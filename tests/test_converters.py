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
    to_curl_cffi_ssl_version,
    to_scrapy_download_error,
    to_scrapy_response,
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


def test_ssl_version_composed_from_min_only() -> None:
    assert to_curl_cffi_ssl_version("TLSv1.2", None) == (
        curl_cffi.const.CurlSslVersion.TLSv1_2
        | curl_cffi.const.CurlSslVersion.MAX_DEFAULT
    )


def test_ssl_version_composed_from_max_only() -> None:
    assert to_curl_cffi_ssl_version(None, "TLSv1.2") == (
        curl_cffi.const.CurlSslVersion.DEFAULT
        | (curl_cffi.const.CurlSslVersion.TLSv1_2 << 16)
    )


def test_ssl_version_none_without_tls_settings() -> None:
    assert to_curl_cffi_ssl_version(None, None) is None


def test_ssl_version_composed_from_min_and_max() -> None:
    assert to_curl_cffi_ssl_version("TLSv1.1", "TLSv1.3") == (
        curl_cffi.const.CurlSslVersion.TLSv1_1
        | (curl_cffi.const.CurlSslVersion.TLSv1_3 << 16)
    )


def test_ssl_version_unknown_value_is_rejected() -> None:
    with pytest.raises(ValueError, match=r"TLSv9\.9"):
        to_curl_cffi_ssl_version("TLSv9.9", None)


def test_timeout_maps_to_download_timeout_error() -> None:
    error = to_scrapy_download_error(
        curl_cffi.requests.exceptions.Timeout("timed out")
    )
    assert isinstance(error, DownloadTimeoutError)
    assert str(error) == "timed out"


def test_invalid_schema_maps_to_unsupported_url_scheme_error() -> None:
    error = to_scrapy_download_error(
        curl_cffi.requests.exceptions.InvalidSchema("no scheme")
    )
    assert isinstance(error, UnsupportedURLSchemeError)


def test_dns_error_maps_to_cannot_resolve_host_error() -> None:
    error = to_scrapy_download_error(
        curl_cffi.requests.exceptions.DNSError(
            "dns failure", curl_cffi.const.CurlECode.COULDNT_RESOLVE_HOST
        )
    )
    assert isinstance(error, CannotResolveHostError)


def test_ssl_error_maps_to_download_connection_refused_error() -> None:
    error = to_scrapy_download_error(
        curl_cffi.requests.exceptions.SSLError("ssl failure")
    )
    assert isinstance(error, DownloadConnectionRefusedError)


def test_proxy_error_maps_to_download_connection_refused_error() -> None:
    error = to_scrapy_download_error(
        curl_cffi.requests.exceptions.ProxyError("proxy failure")
    )
    assert isinstance(error, DownloadConnectionRefusedError)


def test_connection_error_with_dataloss_code_maps_to_download_failed_error() -> None:
    error = to_scrapy_download_error(
        curl_cffi.requests.exceptions.ConnectionError(
            "send failure", curl_cffi.const.CurlECode.SEND_ERROR
        )
    )
    assert isinstance(error, DownloadFailedError)


def test_connection_error_with_other_code_maps_to_connection_refused_error() -> None:
    error = to_scrapy_download_error(
        curl_cffi.requests.exceptions.ConnectionError(
            "connect failure", curl_cffi.const.CurlECode.COULDNT_CONNECT
        )
    )
    assert isinstance(error, DownloadConnectionRefusedError)


def test_other_request_exception_maps_to_download_failed_error() -> None:
    error = to_scrapy_download_error(
        curl_cffi.requests.exceptions.RequestException("generic")
    )
    assert isinstance(error, DownloadFailedError)


def test_returns_none_when_download_errors_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("scrapy_curl_cffi.converters.scrapy_version_info", (2, 12))
    error = to_scrapy_download_error(curl_cffi.requests.exceptions.Timeout("timed out"))
    assert error is None


def _make_curl_cffi_response() -> curl_cffi.Response:
    response = curl_cffi.Response()
    response.primary_ip = "93.184.216.34"
    return response


@pytest.mark.parametrize(
    ("http_version", "protocol"),
    [
        (curl_cffi.const.CurlHttpVersion.V1_0, "HTTP/1.0"),
        (curl_cffi.const.CurlHttpVersion.V1_1, "HTTP/1.1"),
        (curl_cffi.const.CurlHttpVersion.V2_0, "HTTP/2.0"),
        (curl_cffi.const.CurlHttpVersion.V3, "HTTP/3"),
    ],
)
def test_response_protocol_from_http_version(
    http_version: curl_cffi.const.CurlHttpVersion, protocol: str
) -> None:
    curl_cffi_response = _make_curl_cffi_response()
    curl_cffi_response.http_version = http_version
    response = to_scrapy_response(curl_cffi_response, _make_request())
    assert response.protocol == protocol


def test_response_protocol_none_when_http_version_unknown() -> None:
    curl_cffi_response = _make_curl_cffi_response()
    assert curl_cffi_response.http_version == 0
    response = to_scrapy_response(curl_cffi_response, _make_request())
    assert response.protocol is None
