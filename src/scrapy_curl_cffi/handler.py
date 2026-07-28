import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import curl_cffi
else:
    try:
        import curl_cffi
    except ImportError:
        curl_cffi = None

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
from scrapy.utils.defer import deferred_from_coro
from scrapy.utils.reactor import is_asyncio_reactor_installed
from twisted.internet.defer import Deferred

from .adapters import to_curl_cffi_request_params, to_scrapy_response

logger = logging.getLogger(__name__)


class CurlCffiDownloadHandler(HTTP11DownloadHandler):
    if scrapy_version_info < (2, 14):

        def __init__(self, crawler: Crawler) -> None:
            self._check_requirements()
            super().__init__(crawler.settings, crawler)  # pyright: ignore[reportCallIssue]
            self._session: curl_cffi.AsyncSession | None = None

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
            self._session: curl_cffi.AsyncSession | None = None

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

    def _check_requirements(self) -> None:
        if curl_cffi is None:
            msg = f"{self.__class__.__qualname__} requires curl_cffi to be installed."
            raise NotConfigured(msg)
        if not is_asyncio_reactor_installed():
            msg = (
                f"{self.__class__.__qualname__} requires the asyncio Twisted "
                f"reactor. Make sure you have it configured in the "
                f"TWISTED_REACTOR setting. See the asyncio documentation "
                f"of Scrapy for more information."
            )
            raise NotConfigured(msg)

    async def _download_request(self, request: Request) -> Response:
        curl_cffi_request_params = to_curl_cffi_request_params(request)
        if self._session:
            curl_cffi_response = await self._session.request(**curl_cffi_request_params)
        else:
            async with self._create_session() as session:
                curl_cffi_response = await session.request(**curl_cffi_request_params)
        return to_scrapy_response(curl_cffi_response, request)

    def _create_session(
        self, *, max_clients: int = 1, verify: bool = False
    ) -> curl_cffi.AsyncSession:
        return curl_cffi.AsyncSession(
            max_clients=max_clients,
            verify=verify,
            trust_env=False,
        )
