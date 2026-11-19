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
        # getdict() returns {} for an unset setting, which would route every
        # request through curl_cffi; only attach options when configured
        options = (
            cast("CurlCffiOptions", settings.getdict("CURL_CFFI_OPTIONS"))
            if settings.get("CURL_CFFI_OPTIONS") is not None
            else None
        )
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
        options = request.meta.get("curl_cffi_options")
        # curl_cffi only adds browser default headers when impersonating
        return bool(
            options
            and options.get("impersonate")
            and options.get("default_headers", True)
        )


class DefaultHeadersMiddleware(_CurlCffiMixin, _DefaultHeadersMiddleware):
    @classmethod
    def from_crawler(cls, crawler: Crawler) -> Self:
        obj = super().from_crawler(crawler)
        crawler.signals.connect(obj.spider_opened, signal=signals.spider_opened)
        return obj

    def spider_opened(self, spider: Spider) -> None:
        # only a spider that defines default_request_headers replaces the
        # DEFAULT_REQUEST_HEADERS setting loaded in from_crawler
        headers = getattr(spider, "default_request_headers", None)
        if headers is not None:
            self._headers = without_none_values(headers).items()


class UserAgentMiddleware(_CurlCffiMixin, _UserAgentMiddleware):
    pass
