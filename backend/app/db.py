from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite

from app.config import Settings
from app.schemas import AttachmentOut, FileKind

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    file_id        TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    mime           TEXT NOT NULL,
    kind           TEXT NOT NULL,
    size_bytes     INTEGER NOT NULL,
    duration_s     REAL,
    width          INTEGER,
    height         INTEGER,
    page_count     INTEGER,
    stored_path    TEXT NOT NULL,
    thumb_path     TEXT,
    analysis       TEXT NOT NULL,
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_files_created_at ON files(created_at);
"""


def new_file_id() -> str:
    return uuid.uuid4().hex


class Database:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._path = settings.db_path
        self._started = False

    async def start(self) -> None:
        async with aiosqlite.connect(self._path) as conn:
            await conn.executescript(SCHEMA)
            await conn.commit()
        self._started = True
        logger.info("Base de datos lista en %s", self._path)

    async def stop(self) -> None:
        self._started = False

    async def save_file(
        self,
        *,
        name: str,
        mime: str,
        kind: FileKind,
        size_bytes: int,
        stored_path: Path,
        analysis: str,
        thumb_path: Path | None = None,
        duration_s: float | None = None,
        width: int | None = None,
        height: int | None = None,
        page_count: int | None = None,
    ) -> str:
        file_id = new_file_id()
        created_at = datetime.now(UTC).isoformat()
        async with aiosqlite.connect(self._path) as conn:
            await conn.execute(
                """
                INSERT INTO files (
                    file_id, name, mime, kind, size_bytes, duration_s, width, height,
                    page_count, stored_path, thumb_path, analysis, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    file_id,
                    name,
                    mime,
                    kind.value,
                    size_bytes,
                    duration_s,
                    width,
                    height,
                    page_count,
                    str(stored_path),
                    str(thumb_path) if thumb_path else None,
                    analysis,
                    created_at,
                ),
            )
            await conn.commit()
        return file_id

    async def _fetch(self, file_id: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self._path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM files WHERE file_id = ?", (file_id,)
            ) as cursor:
                row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_row(self, file_id: str) -> dict[str, Any] | None:
        return await self._fetch(file_id)

    async def get_attachment(self, file_id: str) -> AttachmentOut | None:
        row = await self._fetch(file_id)
        return row_to_attachment(row) if row else None

    async def list_attachments(self, limit: int = 100) -> list[AttachmentOut]:
        async with aiosqlite.connect(self._path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM files ORDER BY created_at DESC LIMIT ?", (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
        return [row_to_attachment(dict(row)) for row in rows]

    async def delete_file(self, file_id: str) -> bool:
        row = await self._fetch(file_id)
        async with aiosqlite.connect(self._path) as conn:
            await conn.execute("DELETE FROM files WHERE file_id = ?", (file_id,))
            await conn.commit()
        if not row:
            return False
        for key in ("stored_path", "thumb_path"):
            value = row.get(key)
            if value:
                Path(value).unlink(missing_ok=True)
        return True

    async def cleanup_expired(self) -> int:
        cutoff = (datetime.now(UTC) - timedelta(hours=self.settings.file_ttl_hours)).isoformat()
        rows = await self._list_all()
        removed = 0
        for row in rows:
            if row["created_at"] < cutoff:
                await self.delete_file(row["file_id"])
                removed += 1
        if removed:
            logger.info("Se eliminaron %d archivo(s) expirados", removed)
        return removed

    async def _list_all(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self._path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT * FROM files") as cursor:
                rows = await cursor.fetchall()
        return [dict(row) for row in rows]


def row_to_attachment(row: dict[str, Any]) -> AttachmentOut:
    return AttachmentOut(
        file_id=row["file_id"],
        name=row["name"],
        mime=row["mime"],
        kind=FileKind(row["kind"]),
        size_bytes=row["size_bytes"],
        duration_s=row["duration_s"],
        width=row["width"],
        height=row["height"],
        page_count=row["page_count"],
        url=f"/api/files/{row['file_id']}/raw",
        analysis=row["analysis"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )
