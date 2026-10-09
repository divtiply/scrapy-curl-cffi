from ipaddress import ip_address
from typing import TypedDict, cast

import curl_cffi
import curl_cffi.const
import curl_cffi.requests.exceptions
import curl_cffi.requests.utils
import scrapy.http
from scrapy.responsetypes import responsetypes

from .utils import parse_basic_auth_header

try:
    from scrapy.exceptions import (
        CannotResolveHostError,
        DownloadConnectionRefusedError,
        DownloadFailedError,
        DownloadTimeoutError,
        UnsupportedURLSchemeError,
    )
except ImportError:  # Scrapy < 2.13
    CannotResolveHostError = None
    DownloadConnectionRefusedError = None
    DownloadFailedError = None
    DownloadTimeoutError = None
    UnsupportedURLSchemeError = None

_DATALOSS_CODES = {
    curl_cffi.const.CurlECode.SEND_ERROR,
    curl_cffi.const.CurlECode.RECV_ERROR,
    curl_cffi.const.CurlECode.WEIRD_SERVER_REPLY,
}


class CurlCffiOptions(TypedDict, total=False):
    impersonate: curl_cffi.requests.impersonate.BrowserTypeLiteral
    ja3: str
    akamai: str
    extra_fp: (
        curl_cffi.requests.impersonate.ExtraFingerprints
        | curl_cffi.requests.impersonate.ExtraFpDict
    )
    default_headers: bool
    verify: bool
    http_version: "curl_cffi.requests.utils.HttpVersionLiteral"


class _CurlCffiRequestParamsBase(TypedDict, total=True):
    method: curl_cffi.requests.session.HttpMethod
    url: str


class _CurlCffiRequestParams(
    _CurlCffiRequestParamsBase, curl_cffi.requests.session.RequestParams
):
    pass


def to_curl_cffi_request_params(
    scrapy_request: scrapy.http.Request,
) -> _CurlCffiRequestParams:
    headers = to_curl_cffi_headers(scrapy_request.headers)
    proxy_auth_header = headers.pop("Proxy-Authorization", None)

    request_params: _CurlCffiRequestParams = {
        "method": cast("curl_cffi.requests.session.HttpMethod", scrapy_request.method),
        "url": scrapy_request.url,
        "data": scrapy_request.body,
        "headers": headers,
        "allow_redirects": False,  # disable curl-side redirection handling
        "accept_encoding": None,  # disable curl-side content decompression
        "discard_cookies": True,  # disable curl-side cookies handling
    }

    if proxy := scrapy_request.meta.get("proxy"):
        request_params["proxy"] = proxy
    if proxy_auth_header:
        request_params["proxy_auth"] = parse_basic_auth_header(proxy_auth_header)

    if bind_address := scrapy_request.meta.get("bindaddress"):
        request_params["interface"] = bind_address

    if timeout := scrapy_request.meta.get("download_timeout"):
        request_params["timeout"] = timeout

    options: CurlCffiOptions = scrapy_request.meta.get("curl_cffi_options", {})
    supported_keys = CurlCffiOptions.__annotations__.keys()
    unsupported_keys = options.keys() - supported_keys
    if unsupported_keys:
        msg = f"Unsupported curl_cffi_options keys: {', '.join(unsupported_keys)}"
        raise ValueError(msg)
    request_params.update(**options)

    return request_params


def to_curl_cffi_headers(scrapy_headers: scrapy.http.Headers) -> curl_cffi.Headers:
    return curl_cffi.Headers([(k, v) for k, vs in scrapy_headers.items() for v in vs])


def to_scrapy_response(
    curl_cffi_response: curl_cffi.Response, scrapy_request: scrapy.http.Request
) -> scrapy.http.Response:
    headers = to_scrapy_headers(curl_cffi_response.headers)
    response_class = responsetypes.from_args(
        headers=headers,
        url=curl_cffi_response.url,
        body=curl_cffi_response.content,
    )
    response = response_class(
        url=curl_cffi_response.url,
        status=curl_cffi_response.status_code,
        headers=headers,
        body=curl_cffi_response.content,
        flags=["curl_cffi"],
        request=scrapy_request,
        # certificate=
        ip_address=ip_address(curl_cffi_response.primary_ip),
        # protocol=
    )
    response.meta["download_latency"] = curl_cffi_response.elapsed.total_seconds()
    return response


def to_scrapy_headers(curl_cffi_headers: curl_cffi.Headers) -> scrapy.http.Headers:
    return scrapy.http.Headers(curl_cffi_headers.multi_items())


def to_scrapy_download_error(  # noqa: PLR0911
    exc: curl_cffi.requests.exceptions.RequestException,
    url: str,
    timeout: object | None,
) -> Exception | None:
    """Map a curl_cffi request exception onto the matching Scrapy download error.

    Returns ``None`` on Scrapy versions without the download error types
    (< 2.13), where no mapping is possible.
    """
    if (
        DownloadFailedError is None
        or DownloadTimeoutError is None
        or UnsupportedURLSchemeError is None
        or CannotResolveHostError is None
        or DownloadConnectionRefusedError is None
    ):
        return None
    if isinstance(exc, curl_cffi.requests.exceptions.Timeout):
        if timeout is not None:
            msg = f"Getting {url} took longer than {timeout} seconds."
        else:
            msg = f"Getting {url} timed out."
        return DownloadTimeoutError(msg)
    if isinstance(exc, curl_cffi.requests.exceptions.InvalidSchema):
        return UnsupportedURLSchemeError(str(exc))
    if isinstance(exc, curl_cffi.requests.exceptions.DNSError):
        return CannotResolveHostError(str(exc))
    if isinstance(
        exc,
        (
            curl_cffi.requests.exceptions.SSLError,
            curl_cffi.requests.exceptions.ProxyError,
        ),
    ):
        return DownloadConnectionRefusedError(str(exc))
    if isinstance(exc, curl_cffi.requests.exceptions.ConnectionError):
        if exc.code in _DATALOSS_CODES:
            return DownloadFailedError(str(exc))
        return DownloadConnectionRefusedError(str(exc))
    return DownloadFailedError(str(exc))
