from base64 import b64decode
from urllib.parse import unquote

from scrapy.utils.python import to_bytes


def parse_basic_auth_header(header_value: str | bytes) -> tuple[str, str]:
    parts = to_bytes(header_value).split(b" ")
    if parts[0] != b"Basic" or len(parts) != 2:  # noqa: PLR2004
        msg = "Invalid Basic Auth header"
        raise ValueError(msg)
    tokens = b64decode(parts[1]).split(b":", 1)
    return unquote(tokens[0]), unquote(tokens[1])
