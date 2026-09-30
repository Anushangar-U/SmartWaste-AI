"""Validate, normalize and privately store citizen-supplied images."""
from __future__ import annotations

import hashlib
import io
import uuid
import warnings
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from backend.config import settings


ALLOWED_DECLARED_MIME = {
    "image/jpeg": {"JPEG"},
    "image/jpg": {"JPEG"},
    "image/png": {"PNG"},
    "image/webp": {"WEBP"},
}
MAX_DECODED_PIXELS = 25_000_000


class ImageValidationError(ValueError):
    pass


def sanitize_image(raw: bytes, declared_mime: str | None) -> dict:
    if not raw:
        raise ImageValidationError("The uploaded photo is empty.")

    max_bytes = int(settings.vision_max_image_mb * 1024 * 1024)
    if len(raw) > max_bytes:
        raise ImageValidationError(
            f"The uploaded photo exceeds the {settings.vision_max_image_mb} MB limit."
        )

    mime = (declared_mime or "").split(";", 1)[0].strip().lower()
    if mime not in ALLOWED_DECLARED_MIME:
        raise ImageValidationError("Only JPG, JPEG, PNG and WEBP photos are accepted.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as opened:
                actual_format = (opened.format or "").upper()
                if actual_format not in ALLOWED_DECLARED_MIME[mime]:
                    raise ImageValidationError(
                        "The uploaded file contents do not match the declared image type."
                    )
                opened.load()
                if opened.width <= 0 or opened.height <= 0:
                    raise ImageValidationError("The uploaded image has invalid dimensions.")
                if opened.width * opened.height > MAX_DECODED_PIXELS:
                    raise ImageValidationError("The uploaded image dimensions are too large.")

                image = ImageOps.exif_transpose(opened).convert("RGB")
                max_dimension = int(settings.vision_max_dimension)
                if max(image.size) > max_dimension:
                    image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

                output = io.BytesIO()
                image.save(output, format="JPEG", quality=90, optimize=True)
                normalized = output.getvalue()
                width, height = image.size
    except ImageValidationError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombWarning) as exc:
        raise ImageValidationError("The uploaded file is not a valid supported image.") from exc

    return {
        "data": normalized,
        "mime_type": "image/jpeg",
        "byte_size": len(normalized),
        "sha256": hashlib.sha256(normalized).hexdigest(),
        "width": width,
        "height": height,
    }


def persist_image(sanitized: dict) -> dict:
    root = Path(settings.upload_dir)
    root.mkdir(parents=True, exist_ok=True)
    filename = uuid.uuid4().hex + ".jpg"
    path = root / filename
    with path.open("xb") as stream:
        stream.write(sanitized["data"])
    return {
        "stored_path": str(path),
        "mime_type": sanitized["mime_type"],
        "byte_size": sanitized["byte_size"],
        "sha256": sanitized["sha256"],
        "width": sanitized["width"],
        "height": sanitized["height"],
    }


def safe_path(stored_path: str) -> Path:
    root = Path(settings.upload_dir).resolve()
    candidate = Path(stored_path).resolve()
    if candidate != root and root not in candidate.parents:
        raise ImageValidationError("Stored image path is outside the upload directory.")
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate


def remove_file(stored_path: str | None):
    if not stored_path:
        return
    try:
        safe_path(stored_path).unlink(missing_ok=True)
    except (OSError, ImageValidationError, FileNotFoundError):
        pass
