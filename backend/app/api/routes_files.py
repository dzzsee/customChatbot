from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile

from app.context import get_context
from app.schemas import AnalyzeResponse, AttachmentOut, FileListResponse, FileKind
from app.services import media
from app.services.nvidia_client import NvidiaError, guess_mime
from app.services.vision import analyze_document, analyze_image, analyze_video, transcribe_audio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/files", tags=["files"])

CHUNK = 1024 * 1024


async def _save_upload(upload: UploadFile, destination: Path) -> tuple[int, str]:
    size = 0
    mime = upload.content_type or guess_mime(upload.filename or "", "application/octet-stream")
    with destination.open("wb") as handle:
        while chunk := await upload.read(CHUNK):
            size += len(chunk)
            handle.write(chunk)
    return size, mime


def _header(filename: str, mime: str) -> str:
    safe = filename.replace('"', "")
    return f'inline; filename="{safe}"; filename*=UTF-8\'\'{mime}'


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    request: Request,
    file: UploadFile = File(...),
    prompt: str | None = Form(default=None),
) -> AnalyzeResponse:
    ctx = get_context(request)
    settings = ctx.settings

    if not settings.has_api_key:
        raise HTTPException(
            status_code=503,
            detail="Falta NVIDIA_API_KEY. Copia backend/.env.example a backend/.env y anade tu clave.",
        )
    if not file.filename:
        raise HTTPException(status_code=400, detail="El archivo no tiene nombre.")

    try:
        kind = media.sniff_kind(file.filename, file.content_type)
    except media.MediaError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    file_id = uuid.uuid4().hex
    stored_path = settings.uploads_dir / f"{file_id}{Path(file.filename).suffix.lower()}"
    try:
        size, mime = await _save_upload(file, stored_path)
    finally:
        await file.close()

    warnings: list[str] = []
    try:
        media.validate_size(kind, size, settings)
    except media.MediaError as exc:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    workdir = settings.uploads_dir / file_id
    workdir.mkdir(parents=True, exist_ok=True)
    thumb_path: Path | None = None
    info = media.MediaInfo()
    page_count: int | None = None

    try:
        if kind is FileKind.image:
            if media.ffmpeg_available():
                info = await media.probe(stored_path)
                thumb_path = await media.make_thumbnail(stored_path, workdir / "thumb.jpg", at_second=0)
            analysis = await analyze_image(
                ctx.client, ctx.router, settings, stored_path.read_bytes(), mime, prompt=prompt
            )

        elif kind is FileKind.video:
            info = await media.validate_media_limits(kind, stored_path, settings)
            thumb_path = await media.make_thumbnail(
                stored_path, workdir / "thumb.jpg", at_second=min(1.0, (info.duration_s or 1) / 2)
            )
            analysis, normalized = await analyze_video(
                ctx.client, ctx.router, settings, stored_path, workdir, prompt=prompt
            )
            if normalized != stored_path:
                stored_path.unlink(missing_ok=True)
                stored_path = normalized
            if len(analysis) < 40:
                warnings.append("El analisis del video ha sido muy escueto; revisa la duracion del clip.")

        elif kind is FileKind.audio:
            info = await media.validate_media_limits(kind, stored_path, settings)
            transcript, used_fallback = await transcribe_audio(ctx.client, ctx.router, settings, stored_path)
            if used_fallback:
                warnings.append("Parakeet no respondio; se uso Nemotron Omni para transcribir.")
            header = f"## Transcripcion de `{stored_path.name}`\n\n"
            analysis = header + (transcript or "_No se detecto voz en el audio._")

        else:
            analysis, page_count, _ = await analyze_document(ctx.client, ctx.router, settings, stored_path)

    except media.MediaError as exc:
        shutil_cleanup(stored_path, workdir)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NvidiaError as exc:
        shutil_cleanup(stored_path, workdir)
        raise HTTPException(status_code=502, detail=f"NVIDIA rechazo la peticion: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo analizando %s", file.filename)
        shutil_cleanup(stored_path, workdir)
        raise HTTPException(status_code=500, detail=f"No se pudo analizar el archivo: {exc}") from exc

    saved_id = await ctx.db.save_file(
        name=Path(file.filename).name,
        mime=mime,
        kind=kind,
        size_bytes=size,
        stored_path=stored_path,
        analysis=analysis,
        thumb_path=thumb_path,
        duration_s=info.duration_s,
        width=info.width,
        height=info.height,
        page_count=page_count,
    )
    attachment = await ctx.db.get_attachment(saved_id)
    if attachment is None:  # pragma: no cover
        raise HTTPException(status_code=500, detail="No se pudo registrar el archivo.")

    if ctx.rag.available and analysis.strip():
        await ctx.rag.index_document(
            file_id=saved_id, name=attachment.name, kind=kind.value, text=analysis
        )

    return AnalyzeResponse(attachment=attachment, analysis=analysis, warnings=warnings)


def shutil_cleanup(stored_path: Path, workdir: Path) -> None:
    stored_path.unlink(missing_ok=True)
    for child in workdir.glob("*"):
        child.unlink(missing_ok=True)
    workdir.rmdir()


@router.get("", response_model=FileListResponse)
async def list_files(request: Request) -> FileListResponse:
    ctx = get_context(request)
    return FileListResponse(files=await ctx.db.list_attachments())


@router.get("/{file_id}/raw")
async def raw_file(request: Request, file_id: str) -> Response:
    ctx = get_context(request)
    row = await ctx.db.get_row(file_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    path = Path(row["stored_path"])
    if not path.exists():
        raise HTTPException(status_code=410, detail="El archivo original ya fue eliminado.")
    return Response(
        content=path.read_bytes(),
        media_type=row["mime"],
        headers={"Content-Disposition": _header(row["name"], row["mime"])},
    )


@router.get("/{file_id}/thumb")
async def thumbnail(request: Request, file_id: str) -> Response:
    ctx = get_context(request)
    row = await ctx.db.get_row(file_id)
    if row is None or not row.get("thumb_path"):
        raise HTTPException(status_code=404, detail="Sin miniatura para este archivo.")
    path = Path(row["thumb_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Miniatura no encontrada.")
    return Response(content=path.read_bytes(), media_type="image/jpeg")


@router.delete("/{file_id}")
async def delete_file(request: Request, file_id: str) -> dict[str, bool]:
    ctx = get_context(request)
    removed = await ctx.db.delete_file(file_id)
    if removed and ctx.rag.available:
        await ctx.rag.delete_document(file_id)
    return {"deleted": removed}


__all__ = ["router", "AttachmentOut"]
