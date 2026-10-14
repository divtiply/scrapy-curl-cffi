from typing import cast

import curl_cffi
import curl_cffi.const
import curl_cffi.requests.exceptions
import curl_cffi.requests.session
import curl_cffi.requests.utils

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

from scrapy import Spider
from scrapy import version_info as scrapy_version_info
from scrapy.core.downloader.handlers.http11 import HTTP11DownloadHandler
from scrapy.crawler import Crawler
from scrapy.exceptions import NotConfigured
from scrapy.http import Request, Response
from scrapy.settings import BaseSettings
from scrapy.utils.defer import deferred_from_coro
from scrapy.utils.reactor import is_asyncio_reactor_installed
from twisted.internet.defer import Deferred

from .converters import (
    to_curl_cffi_request_params,
    to_curl_cffi_ssl_version,
    to_scrapy_download_error,
    to_scrapy_response,
)


class CurlCffiDownloadHandler(HTTP11DownloadHandler):
    if scrapy_version_info < (2, 14):

        def __init__(self, crawler: Crawler) -> None:
            self._check_requirements()
            super().__init__(crawler.settings, crawler)  # pyright: ignore[reportCallIssue]
            self._init_session(crawler)

        def download_request(  # pyright: ignore[reportRedeclaration, reportIncompatibleMethodOverride]
            self, request: Request, spider: Spider
        ) -> Deferred[Response]:
            if "curl_cffi_options" in request.meta:
                return deferred_from_coro(self._download_request(request))
            return super().download_request(request, spider)  # pyright: ignore[reportCallIssue]

        def close(self) -> Deferred[None]:  # pyright: ignore[reportRedeclaration, reportIncompatibleMethodOverride]
            d: Deferred = super().close()  # pyright: ignore[reportAssignmentType]
            if self._session:
                close_session_dfd = deferred_from_coro(self._session.close())
                d.addBoth(lambda _: close_session_dfd)
            return d

    else:

        def __init__(self, crawler: Crawler) -> None:
            self._check_requirements()
            super().__init__(crawler)
            self._init_session(crawler)

        async def download_request(self, request: Request) -> Response:
            if "curl_cffi_options" in request.meta:
                return await self._download_request(request)
            return await super().download_request(request)

        async def close(self) -> None:
            await super().close()
            if self._session:
                await self._session.close()

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> Self:
        return cls(crawler)

    def _init_session(self, crawler: Crawler) -> None:
        self._session: curl_cffi.AsyncSession | None = None
        self._max_clients, self._session_params = self._build_session_config(
            crawler.settings
        )

    def _check_requirements(self) -> None:
        if not is_asyncio_reactor_installed():
            msg = (
                f"{self.__class__.__qualname__} requires the asyncio Twisted "
                f"reactor. Make sure you have it configured in the "
                f"TWISTED_REACTOR setting. See the asyncio documentation "
                f"of Scrapy for more information."
            )
            raise NotConfigured(msg)

    def _build_session_config(
        self, settings: BaseSettings
    ) -> tuple[int, curl_cffi.requests.session.BaseSessionParams]:
        params: curl_cffi.requests.session.BaseSessionParams = {
            "verify": settings.getbool("DOWNLOAD_VERIFY_CERTIFICATES"),
            "trust_env": False,
        }
        if (http_version := settings.get("CURL_CFFI_HTTP_VERSION")) is not None:
            params["http_version"] = cast(
                "curl_cffi.requests.utils.HttpVersionLiteral", http_version
            )
        if bind_address := settings.get("DOWNLOAD_BIND_ADDRESS"):
            params["interface"] = bind_address
        ssl_version = to_curl_cffi_ssl_version(
            tls_min=settings.get("DOWNLOAD_TLS_MIN_VERSION"),
            tls_max=settings.get("DOWNLOAD_TLS_MAX_VERSION"),
        )
        if ssl_version is not None:
            params["curl_options"] = {curl_cffi.const.CurlOpt.SSLVERSION: ssl_version}
        return settings.getint("CURL_CFFI_MAX_CLIENTS", 10), params

    async def _download_request(self, request: Request) -> Response:
        curl_cffi_request_params = to_curl_cffi_request_params(request)
        if self._session is None:
            self._session = self._create_session()
        try:
            curl_cffi_response = await self._session.request(
                **curl_cffi_request_params
            )
        except curl_cffi.requests.exceptions.RequestException as e:
            error = to_scrapy_download_error(e)
            if error is not None:
                raise error from e
            raise
        return to_scrapy_response(curl_cffi_response, request)

    def _create_session(self) -> curl_cffi.AsyncSession:
        return curl_cffi.AsyncSession(
            max_clients=self._max_clients,
            **self._session_params,
        )
