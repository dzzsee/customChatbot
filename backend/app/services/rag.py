from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import Settings
from app.schemas import KnowledgeHit

logger = logging.getLogger(__name__)

COLLECTION_NAME = "nemotron_docs"
WORDS_PER_TOKEN = 0.75


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """Trocea por palabras aproximando tokens (1 token ~ 0.75 palabras)."""
    words = text.split()
    if not words:
        return []
    window = max(1, int(chunk_size * WORDS_PER_TOKEN))
    step = max(1, window - max(0, int(overlap * WORDS_PER_TOKEN)))
    chunks: list[str] = []
    for start in range(0, len(words), step):
        piece = words[start : start + window]
        if not piece:
            break
        chunks.append(" ".join(piece))
        if start + window >= len(words):
            break
    return chunks


class RagStore:
    """Indice vectorial de los analisis, respaldado por Chroma + nemotron-3-embed-1b."""

    def __init__(self, settings: Settings, client) -> None:
        self.settings = settings
        self.client = client
        self._collection: Any | None = None
        self._available = False

    @property
    def available(self) -> bool:
        return self._available

    async def start(self) -> bool:
        if not self.settings.enable_rag:
            logger.info("RAG deshabilitado por configuracion.")
            return False
        try:
            import chromadb  # noqa: PLC0415
        except ImportError:
            logger.warning("chromadb no instalado: el RAG quedara deshabilitado.")
            return False

        try:
            chroma_client = await asyncio.to_thread(
                chromadb.PersistentClient, path=str(self.settings.chroma_dir)
            )
            self._collection = await asyncio.to_thread(
                chroma_client.get_or_create_collection,
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            self._available = True
            logger.info("RAG listo con %s", self.settings.model_embed)
        except Exception as exc:  # noqa: BLE001
            logger.warning("No se pudo inicializar el RAG: %s", exc)
            self._available = False
        return self._available

    async def index_document(
        self, *, file_id: str, name: str, kind: str, text: str
    ) -> int:
        if not self._available or self._collection is None or not text.strip():
            return 0
        chunks = chunk_text(text, self.settings.rag_chunk_size, self.settings.rag_chunk_overlap)
        if not chunks:
            return 0

        try:
            vectors = await self.client.embed(self.settings.model_embed, chunks)
        except Exception as exc:  # noqa: BLE001
            logger.warning("No se pudieron generar embeddings para %s: %s", name, exc)
            return 0

        await self._delete(file_id)
        ids = [f"{file_id}:{index}" for index in range(len(chunks))]
        metadatas = [{"file_id": file_id, "name": name, "kind": kind, "chunk": index} for index in range(len(chunks))]
        await asyncio.to_thread(
            self._collection.add,
            ids=ids,
            documents=chunks,
            embeddings=vectors,
            metadatas=metadatas,
        )
        logger.info("Indexados %d fragmentos de %s", len(chunks), name)
        return len(chunks)

    async def search(self, query: str, top_k: int | None = None) -> list[KnowledgeHit]:
        if not self._available or self._collection is None or not query.strip():
            return []
        limit = top_k or self.settings.rag_top_k
        try:
            vector = (await self.client.embed(self.settings.model_embed, [query]))[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Embedding de consulta fallo: %s", exc)
            return []

        def run() -> dict[str, Any]:
            return self._collection.query(
                query_embeddings=[vector],
                n_results=limit,
                include=["documents", "metadatas", "distances"],
            )

        raw = await asyncio.to_thread(run)
        documents = (raw.get("documents") or [[]])[0]
        metadatas = (raw.get("metadatas") or [[]])[0]
        distances = (raw.get("distances") or [[]])[0]

        hits: list[KnowledgeHit] = []
        for index, document in enumerate(documents):
            metadata = metadatas[index] if index < len(metadatas) else {}
            distance = distances[index] if index < len(distances) else None
            hits.append(
                KnowledgeHit(
                    file_id=metadata.get("file_id"),
                    name=metadata.get("name"),
                    kind=metadata.get("kind"),
                    text=document,
                    score=round(1 - distance, 4) if isinstance(distance, (int, float)) else None,
                )
            )
        return hits

    async def _delete(self, file_id: str) -> None:
        if self._collection is None:
            return
        try:
            existing = await asyncio.to_thread(self._collection.get, where={"file_id": file_id})
            ids = existing.get("ids") or []
            if ids:
                await asyncio.to_thread(self._collection.delete, ids=ids)
        except Exception as exc:  # noqa: BLE001
            logger.debug("No se pudo limpiar el indice de %s: %s", file_id, exc)

    async def delete_document(self, file_id: str) -> None:
        await self._delete(file_id)
