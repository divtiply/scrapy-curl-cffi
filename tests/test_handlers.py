from datetime import timedelta
from types import SimpleNamespace
from typing import cast

import curl_cffi
import pytest
from scrapy import Request
from scrapy.core.downloader.handlers.http11 import HTTP11DownloadHandler
from scrapy.exceptions import DownloadFailedError, DownloadTimeoutError
from scrapy.utils.test import get_crawler

from scrapy_curl_cffi.handlers import CurlCffiDownloadHandler


class FakeSession:

    """Stands in for ``curl_cffi.AsyncSession`` in handler tests."""

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.request_calls: list[dict] = []
        self.closed = False

    async def request(self, **params: object) -> SimpleNamespace:
        self.request_calls.append(params)
        return SimpleNamespace(
            headers=curl_cffi.Headers(),
            url="http://example.com",
            status_code=200,
            content=b"ok",
            primary_ip="93.184.216.34",
            elapsed=timedelta(seconds=0.01),
        )

    async def close(self) -> None:
        self.closed = True


def _make_handler(
    monkeypatch: pytest.MonkeyPatch,
    settings: dict | None = None,
    *,
    patch_session: bool = True,
) -> CurlCffiDownloadHandler:
    if patch_session:
        monkeypatch.setattr(curl_cffi, "AsyncSession", FakeSession)
    crawler = get_crawler(settings_dict=settings)
    return CurlCffiDownloadHandler(crawler)


def _make_request() -> Request:
    return Request("http://example.com", meta={"curl_cffi_options": {}})


async def test_session_created_lazily_and_reused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handler = _make_handler(monkeypatch)
    assert handler._session is None

    await handler._download_request(_make_request())
    await handler._download_request(_make_request())

    session = handler._session
    assert isinstance(session, FakeSession)
    assert len(session.request_calls) == 2


def test_default_session_config(monkeypatch: pytest.MonkeyPatch) -> None:
    handler = _make_handler(monkeypatch)
    assert handler._max_clients == 10
    assert handler._session_params == {
        "verify": False,
        "trust_env": False,
    }


def test_session_config_from_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    handler = _make_handler(
        monkeypatch,
        settings={
            "CURL_CFFI_MAX_CLIENTS": 5,
            "DOWNLOAD_VERIFY_CERTIFICATES": True,
            "CURL_CFFI_HTTP_VERSION": "v1",
            "DOWNLOAD_BIND_ADDRESS": "127.0.0.2",
            "DOWNLOAD_TLS_MIN_VERSION": "TLSv1.2",
        },
    )
    ssl_version = (
        curl_cffi.const.CurlSslVersion.TLSv1_2
        | curl_cffi.const.CurlSslVersion.MAX_DEFAULT
    )
    assert handler._max_clients == 5
    assert handler._session_params == {
        "verify": True,
        "trust_env": False,
        "http_version": "v1",
        "interface": "127.0.0.2",
        "curl_options": {curl_cffi.const.CurlOpt.SSLVERSION: ssl_version},
    }


async def test_create_session_applies_config(monkeypatch: pytest.MonkeyPatch) -> None:
    handler = _make_handler(
        monkeypatch,
        settings={
            "CURL_CFFI_MAX_CLIENTS": 5,
            "DOWNLOAD_VERIFY_CERTIFICATES": True,
            "CURL_CFFI_HTTP_VERSION": "v1",
            "DOWNLOAD_BIND_ADDRESS": "127.0.0.2",
        },
        patch_session=False,
    )
    session = handler._create_session()
    try:
        assert isinstance(session, curl_cffi.AsyncSession)
        assert session.max_clients == 5
        assert session.http_version == "v1"
        assert session.interface == "127.0.0.2"
        # True is resolved to the certificate bundle path by curl_cffi
        assert session.verify
    finally:
        await session.close()


async def test_close_closes_session(monkeypatch: pytest.MonkeyPatch) -> None:
    handler = _make_handler(monkeypatch)
    await handler._download_request(_make_request())
    session = cast("FakeSession | None", handler._session)

    async def _noop_close(*_args: object) -> None:
        return None

    monkeypatch.setattr(HTTP11DownloadHandler, "close", _noop_close)
    await handler.close()
    assert session is not None
    assert session.closed


def _make_failing_session(
    exc: Exception,
) -> FakeSession:
    session = FakeSession()

    async def _raise(**_params: object) -> SimpleNamespace:
        raise exc

    session.request = _raise  # type: ignore[method-assign]
    return session


async def _assert_mapped(
    monkeypatch: pytest.MonkeyPatch,
    exc: Exception,
    expected: type[Exception],
) -> None:
    handler = _make_handler(monkeypatch)
    handler._session = _make_failing_session(exc)  # pyright: ignore[reportAttributeAccessIssue]
    with pytest.raises(expected):
        await handler._download_request(_make_request())


async def test_timeout_mapped_to_download_timeout_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _assert_mapped(
        monkeypatch,
        curl_cffi.requests.exceptions.Timeout("timed out"),
        DownloadTimeoutError,
    )


async def test_connection_error_dataloss_code_mapped_to_download_failed_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _assert_mapped(
        monkeypatch,
        curl_cffi.requests.exceptions.ConnectionError(
            "send failure", curl_cffi.const.CurlECode.SEND_ERROR
        ),
        DownloadFailedError,
    )
