from typing import cast

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self


from scrapy import Request, Spider, signals
from scrapy import version_info as scrapy_version_info
from scrapy.crawler import Crawler
from scrapy.downloadermiddlewares.defaultheaders import (
    DefaultHeadersMiddleware as _DefaultHeadersMiddleware,
)
from scrapy.downloadermiddlewares.useragent import (
    UserAgentMiddleware as _UserAgentMiddleware,
)
from scrapy.http import Response
from scrapy.utils.python import without_none_values

from .converters import CurlCffiOptions


class CurlCffiMiddleware:
    def __init__(self, options: CurlCffiOptions | None = None) -> None:
        self._options = options

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> Self:
        settings = crawler.settings
        options = cast("CurlCffiOptions", settings.getdict("CURL_CFFI_OPTIONS"))
        obj = cls(options)
        crawler.signals.connect(obj.spider_opened, signal=signals.spider_opened)
        return obj

    def spider_opened(self, spider: Spider) -> None:
        self._options = getattr(spider, "curl_cffi_options", self._options)

    def process_request(
        self,
        request: Request,
        spider: Spider | None = None,  # noqa: ARG002
    ) -> Request | Response | None:
        if self._options is not None:
            request.meta.setdefault("curl_cffi_options", self._options)
        return None


class _CurlCffiMixin:
    if scrapy_version_info < (2, 14):

        def process_request(  # pyright: ignore[reportRedeclaration]
            self, request: Request, spider: Spider
        ) -> Request | Response | None:
            if self._will_use_curl_cffi_default_headers(request):
                return None
            return super().process_request(request, spider)  # pyright: ignore[reportAttributeAccessIssue]

    else:

        def process_request(
            self,
            request: Request,
            spider: Spider | None = None,  # noqa: ARG002
        ) -> Request | Response | None:
            if self._will_use_curl_cffi_default_headers(request):
                return None
            return super().process_request(request)  # pyright: ignore[reportAttributeAccessIssue]

    def _will_use_curl_cffi_default_headers(self, request: Request) -> bool:
        return (  # _
            "curl_cffi_options" in request.meta
            and request.meta["curl_cffi_options"].get("default_headers", True)
        )


class DefaultHeadersMiddleware(_CurlCffiMixin, _DefaultHeadersMiddleware):
    @classmethod
    def from_crawler(cls, crawler: Crawler) -> Self:
        obj = super().from_crawler(crawler)
        crawler.signals.connect(obj.spider_opened, signal=signals.spider_opened)
        return obj

    def spider_opened(self, spider: Spider) -> None:
        headers = without_none_values(getattr(spider, "default_request_headers", {}))
        self._headers = headers.items()


class UserAgentMiddleware(_CurlCffiMixin, _UserAgentMiddleware):
    pass
