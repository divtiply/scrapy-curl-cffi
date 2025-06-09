from collections.abc import Mapping

from scrapy import Request, Spider, signals
from scrapy.crawler import Crawler
from scrapy.downloadermiddlewares.defaultheaders import (
    DefaultHeadersMiddleware as _DefaultHeadersMiddleware,
)
from scrapy.downloadermiddlewares.useragent import (
    UserAgentMiddleware as _UserAgentMiddleware,
)
from scrapy.http import Response
from typing_extensions import Self


class CurlCffiMiddleware:
    def __init__(self, options: Mapping | None) -> None:
        self._options = options

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> Self:
        settings = crawler.settings
        if "CURL_CFFI_OPTIONS" in settings:
            options = settings.getdict("CURL_CFFI_OPTIONS")
        else:
            options = None
        mw = cls(options)
        crawler.signals.connect(mw.spider_opened, signal=signals.spider_opened)
        return mw

    def spider_opened(self, spider: Spider) -> None:
        self._options = getattr(spider, "curl_cffi_options", self._options)

    def process_request(
        self,
        request: Request,
        spider: Spider,  # noqa: ARG002
    ) -> Request | Response | None:
        if self._options is not None:
            request.meta.setdefault("curl_cffi_options", self._options)
        return None


class _CurlCffiMixin:
    def process_request(
        self, request: Request, spider: Spider
    ) -> Request | Response | None:
        if (
            "curl_cffi_options" in request.meta  # _
            and request.meta["curl_cffi_options"].get("default_headers", True)
        ):
            return None
        return super().process_request(request, spider)  # type: ignore


class DefaultHeadersMiddleware(_CurlCffiMixin, _DefaultHeadersMiddleware):
    @classmethod
    def from_crawler(cls, crawler: Crawler) -> Self:
        mw = super().from_crawler(crawler)
        crawler.signals.connect(mw.spider_opened, signal=signals.spider_opened)
        return mw

    def spider_opened(self, spider: Spider) -> None:
        headers = getattr(spider, "default_request_headers", None) or {}
        self._headers = headers.items() if isinstance(headers, Mapping) else headers


class UserAgentMiddleware(_CurlCffiMixin, _UserAgentMiddleware):
    pass
