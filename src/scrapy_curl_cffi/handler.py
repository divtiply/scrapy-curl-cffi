import logging
from http.cookiejar import Cookie, CookieJar

import curl_cffi
from scrapy import Spider
from scrapy.core.downloader.handlers.http import HTTPDownloadHandler
from scrapy.crawler import Crawler
from scrapy.http import Request, Response
from scrapy.settings import BaseSettings
from scrapy.utils.defer import deferred_from_coro
from scrapy.utils.reactor import is_asyncio_reactor_installed
from twisted.internet.defer import Deferred

from .adapters import to_curl_cffi_request_kwargs, to_scrapy_response

logger = logging.getLogger(__name__)


class CurlCffiDownloadHandler(HTTPDownloadHandler):
    def __init__(self, settings: BaseSettings, crawler: Crawler) -> None:
        super().__init__(settings, crawler)
        if not is_asyncio_reactor_installed():
            msg = (
                f"{self.__class__.__qualname__} requires the asyncio Twisted "
                f"reactor. Make sure you have it configured in the "
                f"TWISTED_REACTOR setting. See the asyncio documentation "
                f"of Scrapy for more information."
            )
            raise ValueError(msg)
        self._session: curl_cffi.AsyncSession | None = None

    def download_request(self, request: Request, spider: Spider) -> Deferred[Response]:
        if "curl_cffi_options" in request.meta:
            return deferred_from_coro(self._download_request(request, spider))
        return super().download_request(request, spider)

    async def _download_request(self, request: Request, spider: Spider) -> Response:  # noqa: ARG002
        curl_cffi_request_kwargs = to_curl_cffi_request_kwargs(request)
        if self._session:
            curl_cffi_response = await self._session.request(**curl_cffi_request_kwargs)
        else:
            async with self._create_session() as session:
                curl_cffi_response = await session.request(**curl_cffi_request_kwargs)
        return to_scrapy_response(curl_cffi_response, request)

    def _create_session(
        self,
        max_clients: int = 1,
        verify: bool = False,  # noqa: FBT001, FBT002
    ) -> curl_cffi.AsyncSession:
        return curl_cffi.AsyncSession(
            max_clients=max_clients,
            cookies=_DummyCookieJar(),
            trust_env=False,
            allow_redirects=False,
            verify=verify,
        )

    def close(self) -> Deferred[None]:
        d = super().close()
        if self._session:
            close_session_dfd = deferred_from_coro(self._session.close())
            d.addBoth(lambda _: close_session_dfd)
        return d


class _DummyCookieJar(CookieJar):
    def set_cookie(self, cookie: Cookie) -> None:
        pass
