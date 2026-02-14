import base64
import hashlib


def to_data_url(image_bytes: bytes, mime: str) -> str:
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
