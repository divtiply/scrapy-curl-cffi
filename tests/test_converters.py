import curl_cffi
import pytest
from scrapy import Request
from scrapy.exceptions import (
    CannotResolveHostError,
    DownloadConnectionRefusedError,
    DownloadFailedError,
    DownloadTimeoutError,
    UnsupportedURLSchemeError,
)

from scrapy_curl_cffi.converters import (
    to_curl_cffi_request_params,
    to_scrapy_download_error,
)


def _make_request(meta: dict | None = None) -> Request:
    return Request("http://example.com", meta=meta or {})


def test_http_version_option_is_passed_through() -> None:
    request = _make_request({"curl_cffi_options": {"http_version": "v2"}})
    params = to_curl_cffi_request_params(request)
    assert params.get("http_version") == "v2"


def test_unsupported_option_key_is_rejected() -> None:
    request = _make_request({"curl_cffi_options": {"bogus": True}})
    with pytest.raises(ValueError, match="bogus"):
        to_curl_cffi_request_params(request)


def test_timeout_maps_to_download_timeout_error_with_timeout() -> None:
    error = to_scrapy_download_error(
        curl_cffi.requests.exceptions.Timeout("timed out"), "http://example.com", 5
    )
    assert isinstance(error, DownloadTimeoutError)
    assert str(error) == "Getting http://example.com took longer than 5 seconds."


def test_timeout_maps_to_download_timeout_error_without_timeout() -> None:
    error = to_scrapy_download_error(
        curl_cffi.requests.exceptions.Timeout("timed out"), "http://example.com", None
    )
    assert isinstance(error, DownloadTimeoutError)
    assert str(error) == "Getting http://example.com timed out."


def test_invalid_schema_maps_to_unsupported_url_scheme_error() -> None:
    error = to_scrapy_download_error(
        curl_cffi.requests.exceptions.InvalidSchema("no scheme"),
        "http://example.com",
        None,
    )
    assert isinstance(error, UnsupportedURLSchemeError)


def test_dns_error_maps_to_cannot_resolve_host_error() -> None:
    error = to_scrapy_download_error(
        curl_cffi.requests.exceptions.DNSError(
            "dns failure", curl_cffi.const.CurlECode.COULDNT_RESOLVE_HOST
        ),
        "http://example.com",
        None,
    )
    assert isinstance(error, CannotResolveHostError)


def test_ssl_error_maps_to_download_connection_refused_error() -> None:
    error = to_scrapy_download_error(
        curl_cffi.requests.exceptions.SSLError("ssl failure"),
        "http://example.com",
        None,
    )
    assert isinstance(error, DownloadConnectionRefusedError)


def test_proxy_error_maps_to_download_connection_refused_error() -> None:
    error = to_scrapy_download_error(
        curl_cffi.requests.exceptions.ProxyError("proxy failure"),
        "http://example.com",
        None,
    )
    assert isinstance(error, DownloadConnectionRefusedError)


def test_connection_error_with_dataloss_code_maps_to_download_failed_error() -> None:
    error = to_scrapy_download_error(
        curl_cffi.requests.exceptions.ConnectionError(
            "send failure", curl_cffi.const.CurlECode.SEND_ERROR
        ),
        "http://example.com",
        None,
    )
    assert isinstance(error, DownloadFailedError)


def test_connection_error_with_other_code_maps_to_connection_refused_error() -> None:
    error = to_scrapy_download_error(
        curl_cffi.requests.exceptions.ConnectionError(
            "connect failure", curl_cffi.const.CurlECode.COULDNT_CONNECT
        ),
        "http://example.com",
        None,
    )
    assert isinstance(error, DownloadConnectionRefusedError)


def test_other_request_exception_maps_to_download_failed_error() -> None:
    error = to_scrapy_download_error(
        curl_cffi.requests.exceptions.RequestException("generic"),
        "http://example.com",
        None,
    )
    assert isinstance(error, DownloadFailedError)


def test_returns_none_when_download_errors_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("scrapy_curl_cffi.converters.DownloadFailedError", None)
    error = to_scrapy_download_error(
        curl_cffi.requests.exceptions.Timeout("timed out"), "http://example.com", 5
    )
    assert error is None
