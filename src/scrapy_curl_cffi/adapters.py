from ipaddress import ip_address
from typing import Any

import curl_cffi
import scrapy.http
from scrapy.responsetypes import responsetypes

from .utils import parse_basic_auth_header


def to_curl_cffi_request_kwargs(scrapy_request: scrapy.http.Request) -> dict[str, Any]:
    curl_cffi_headers = to_curl_cffi_headers(scrapy_request.headers)
    proxy_auth_header = curl_cffi_headers.pop("Proxy-Authorization", None)

    request_kwargs = {
        "method": scrapy_request.method,
        "url": scrapy_request.url,
        "data": scrapy_request.body,
        "headers": curl_cffi_headers,
        "allow_redirects": False,  # disable curl-side redirection
        "accept_encoding": None,  # disable curl-side decompression
    }

    proxy = scrapy_request.meta.get("proxy")
    if proxy is not None:
        request_kwargs["proxy"] = proxy
    if proxy_auth_header is not None:
        request_kwargs["proxy_auth"] = parse_basic_auth_header(proxy_auth_header)

    timeout = scrapy_request.meta.get("download_timeout")
    if timeout is not None:
        request_kwargs["timeout"] = timeout

    options = scrapy_request.meta.get("curl_cffi_options", {})
    supported_keys = {
        "impersonate",
        "default_headers",
        "ja3",
        "akamai",
        "extra_fp",
        "verify",
    }
    unsupported_keys = options.keys() - supported_keys
    if unsupported_keys:
        msg = f"Unsupported curl_cffi_options keys: {', '.join(unsupported_keys)}"
        raise ValueError(msg)
    request_kwargs.update(
        {key: options[key] for key in supported_keys & options.keys()}
    )

    return request_kwargs


def to_curl_cffi_headers(scrapy_headers: scrapy.http.Headers) -> curl_cffi.Headers:
    return curl_cffi.Headers([(k, v) for k, vs in scrapy_headers.items() for v in vs])


def to_scrapy_response(
    curl_cffi_response: curl_cffi.Response, scrapy_request: scrapy.http.Request
) -> scrapy.http.Response:
    scrapy_headers = to_scrapy_headers(curl_cffi_response.headers)
    response_class = responsetypes.from_args(
        headers=scrapy_headers,
        url=curl_cffi_response.url,
        body=curl_cffi_response.content,
    )
    response = response_class(
        url=curl_cffi_response.url,
        status=curl_cffi_response.status_code,
        headers=scrapy_headers,
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
