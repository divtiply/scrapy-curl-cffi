from ipaddress import ip_address
from typing import TypedDict, cast

import curl_cffi
import scrapy.http
from scrapy.responsetypes import responsetypes

from .utils import parse_basic_auth_header


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
    response.meta["download_latency"] = curl_cffi_response.elapsed
    return response


def to_scrapy_headers(curl_cffi_headers: curl_cffi.Headers) -> scrapy.http.Headers:
    return scrapy.http.Headers(curl_cffi_headers.multi_items())
