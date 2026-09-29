from __future__ import annotations

import asyncio
import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings
from app.schemas import FileKind

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".m4v", ".webm", ".mov", ".mkv", ".avi"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".webm"}
DOCUMENT_EXTENSIONS = {".pdf", ".txt", ".md", ".csv", ".json", ".docx", ".log", ".tsv"}

MB = 1024 * 1024


class MediaError(ValueError):
    """Error de validación o procesamiento de archivos, con mensaje en español."""


@dataclass(slots=True)
class MediaInfo:
    duration_s: float | None = None
    width: int | None = None
    height: int | None = None
    has_audio: bool = False
    video_codec: str | None = None


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def require_ffmpeg() -> None:
    if not ffmpeg_available():
        raise MediaError(
            "FFmpeg no esta instalado o no esta en el PATH. "
            "Descargalo de https://ffmpeg.org/download.html y reinicia la terminal."
        )


async def _run(cmd: list[str], timeout: float = 300.0) -> tuple[int, bytes, bytes]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        proc.kill()
        raise MediaError(f"FFmpeg supero el tiempo limite ({timeout:.0f}s): {cmd[0]}")
    return proc.returncode or 0, stdout, stderr


def sniff_kind(filename: str, mime: str | None = None) -> FileKind:
    suffix = Path(filename).suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return FileKind.image
    if suffix in VIDEO_EXTENSIONS:
        return FileKind.video
    if suffix in AUDIO_EXTENSIONS:
        return FileKind.audio
    if suffix in DOCUMENT_EXTENSIONS:
        return FileKind.document
    raise MediaError(
        f"Tipo de archivo no soportado: {suffix or filename}. "
        "Formatos admitidos: imagenes (png, jpg, webp), video (mp4, mov, webm), "
        "audio (mp3, wav, m4a) y documentos (pdf, txt, md, csv, docx)."
    )


def validate_size(kind: FileKind, size_bytes: int, settings: Settings) -> None:
    if kind is FileKind.image:
        limit_mb, label = settings.max_image_mb, "imagen"
    elif kind is FileKind.video:
        limit_mb, label = settings.max_video_mb, "video"
    elif kind is FileKind.audio:
        limit_mb, label = settings.max_audio_mb, "audio"
    else:
        limit_mb, label = settings.max_doc_mb, "documento"

    if size_bytes > limit_mb * MB:
        raise MediaError(
            f"El {label} pesa {size_bytes / MB:.1f} MB y el limite es {limit_mb} MB."
        )


async def probe(path: Path) -> MediaInfo:
    require_ffmpeg()
    code, stdout, stderr = await _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        timeout=60.0,
    )
    if code != 0:
        raise MediaError(f"No se pudo leer el archivo: {stderr.decode('utf-8', 'ignore')[:300]}")

    try:
        data = json.loads(stdout.decode("utf-8", "ignore"))
    except json.JSONDecodeError as exc:
        raise MediaError("ffprobe devolvio una respuesta invalida.") from exc

    info = MediaInfo()
    raw_duration = data.get("format", {}).get("duration")
    if raw_duration:
        try:
            info.duration_s = round(float(raw_duration), 2)
        except (TypeError, ValueError):
            info.duration_s = None

    for stream in data.get("streams", []):
        codec_type = stream.get("codec_type")
        if codec_type == "video" and info.width is None:
            info.width = stream.get("width")
            info.height = stream.get("height")
            info.video_codec = stream.get("codec_name")
        elif codec_type == "audio":
            info.has_audio = True
    return info


async def validate_media_limits(
    kind: FileKind, path: Path, settings: Settings
) -> MediaInfo:
    """Aplica los limites de duracion. Devuelve la informacion del medio."""
    if kind not in (FileKind.video, FileKind.audio):
        return MediaInfo()

    info = await probe(path)

    if kind is FileKind.video:
        if info.duration_s is None:
            raise MediaError(
                "No se pudo determinar la duracion del video. "
                "El modelo Nemotron Omni solo admite MP4 de hasta "
                f"{settings.max_video_seconds // 60} minutos."
            )
        if info.duration_s > settings.max_video_seconds:
            minutes = info.duration_s / 60
            limit = settings.max_video_seconds // 60
            raise MediaError(
                f"El video dura {minutes:.1f} minutos y el limite de Nemotron Omni es "
                f"{limit} minutos (2 min / 128 frames). "
                "Recorta el clip o extrae solo el audio para transcribirlo."
            )
    elif info.duration_s and info.duration_s > settings.max_audio_seconds:
        raise MediaError(
            f"El audio dura {info.duration_s / 60:.1f} minutos y el limite es "
            f"{settings.max_audio_seconds // 60} minutos."
        )
    return info


async def normalize_video_to_mp4(source: Path, target: Path) -> Path:
    """Remux/transcode a MP4 H.264 + AAC, que es lo que espera Nemotron Omni."""
    code, _, stderr = await _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(target),
        ],
        timeout=900.0,
    )
    if code != 0 or not target.exists() or target.stat().st_size == 0:
        logger.warning("No se pudo normalizar el video a MP4: %s", stderr.decode("utf-8", "ignore")[:300])
        return source
    return target


async def extract_audio(source: Path, target: Path) -> Path | None:
    """Extrae el audio a WAV 16 kHz mono para ASR."""
    code, _, stderr = await _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(target),
        ],
        timeout=600.0,
    )
    if code != 0 or not target.exists():
        logger.warning("No se pudo extraer el audio: %s", stderr.decode("utf-8", "ignore")[:300])
        return None
    return target


async def make_thumbnail(source: Path, target: Path, *, at_second: float = 1.0) -> Path | None:
    require_ffmpeg()
    code, _, _ = await _run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{at_second:.2f}",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-vf",
            "scale=640:-2",
            str(target),
        ],
        timeout=60.0,
    )
    if code != 0 or not target.exists():
        return None
    return target


def _fitz():
    try:
        import fitz  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover
        raise MediaError(
            "Falta PyMuPDF. Instala las dependencias con: pip install -r requirements.txt"
        ) from exc
    return fitz


def extract_pdf(path: Path, max_pages: int) -> tuple[str, int, list[bytes]]:
    """Extrae texto por pagina y rasteriza las paginas sin texto (escaneos)."""
    fitz = _fitz()
    doc = fitz.open(path)
    try:
        total = doc.page_count
        parts: list[str] = []
        images: list[bytes] = []
        for index in range(min(total, max_pages)):
            page = doc.load_page(index)
            text = page.get_text().strip()
            images.append(page.get_pixmap(dpi=150).tobytes("png"))
            if text:
                parts.append(f"--- Pagina {index + 1} ---\n{text}")
        if not parts:
            parts.append(
                f"Documento de {total} paginas sin capa de texto (escaneado). "
                "Las paginas se enviaron como imagenes para analisis visual."
            )
        body = "\n\n".join(parts)
        if total > max_pages:
            body += f"\n\n[Documento truncado: {total} paginas, se leyeron {max_pages}.]"
        return body, total, images
    finally:
        doc.close()


def extract_docx(path: Path) -> str:
    try:
        import docx  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover
        raise MediaError(
            "Falta python-docx. Instala las dependencias con: pip install -r requirements.txt"
        ) from exc
    document = docx.Document(path)
    blocks = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            if any(cells):
                blocks.append(" | ".join(cells))
    return "\n".join(blocks)


def extract_plain_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_bytes().decode("utf-8", "ignore")
