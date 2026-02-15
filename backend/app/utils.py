import base64
import hashlib
import mimetypes
from pathlib import Path


def to_data_url(image_bytes: bytes, mime: str) -> str:
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def image_file_to_data_url(path: str) -> str:
    """Read an image file and return a data URL:
    data:image/jpeg;base64,....
    """
    p = Path(path)
    mime, _ = mimetypes.guess_type(str(p))
    if mime is None:
        # fallback
        mime = "image/jpeg"

    with open(p, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    return f"data:{mime};base64,{b64}"
