from typing import Any

import pytest
from scrapy import Request, Spider
from scrapy.utils.test import get_crawler

from scrapy_curl_cffi.middlewares import (
    CurlCffiMiddleware,
    DefaultHeadersMiddleware,
    UserAgentMiddleware,
)

USER_AGENT = "test-agent"
DEFAULT_REQUEST_HEADERS = {"Accept-Language": "en"}


class PlainSpider(Spider):
    name = "plain"


def _process(
    settings: dict[str, Any] | None = None,
    spider_options: dict[str, Any] | None = None,
) -> Request:
    spidercls: type[Spider] = PlainSpider
    if spider_options is not None:
        spidercls = type(
            "OptionsSpider",
            (Spider,),
            {"name": "opts", "curl_cffi_options": spider_options},
        )
    crawler = get_crawler(
        spidercls,
        {
            "USER_AGENT": USER_AGENT,
            "DEFAULT_REQUEST_HEADERS": DEFAULT_REQUEST_HEADERS,
            **(settings or {}),
        },
    )
    spider = spidercls.from_crawler(crawler)
    curl_mw = CurlCffiMiddleware.from_crawler(crawler)
    headers_mw = DefaultHeadersMiddleware.from_crawler(crawler)
    ua_mw = UserAgentMiddleware.from_crawler(crawler)
    curl_mw.spider_opened(spider)
    headers_mw.spider_opened(spider)
    ua_mw.spider_opened(spider)

    request = Request("https://example.com/")
    for mw in (curl_mw, headers_mw, ua_mw):
        mw.process_request(request, spider)
    return request


def test_unset_setting_attaches_no_options() -> None:
    request = _process()
    assert "curl_cffi_options" not in request.meta
    assert request.headers.get("User-Agent") == USER_AGENT.encode()
    assert request.headers.get("Accept-Language") == b"en"


def test_explicit_none_setting_attaches_no_options() -> None:
    request = _process({"CURL_CFFI_OPTIONS": None})
    assert "curl_cffi_options" not in request.meta


def test_empty_setting_attaches_empty_options_and_keeps_scrapy_headers() -> None:
    request = _process({"CURL_CFFI_OPTIONS": {}})
    assert request.meta["curl_cffi_options"] == {}
    assert request.headers.get("User-Agent") == USER_AGENT.encode()


@pytest.mark.parametrize(
    "options",
    [
        {"ja3": "771,4865,0,0,0"},
        {"http_version": "v2"},
        {"impersonate": "chrome", "default_headers": False},
    ],
)
def test_scrapy_headers_sent_when_curl_adds_none(options: dict[str, Any]) -> None:
    request = _process({"CURL_CFFI_OPTIONS": options})
    assert request.meta["curl_cffi_options"] == options
    assert request.headers.get("User-Agent") == USER_AGENT.encode()
    assert request.headers.get("Accept-Language") == b"en"


def test_impersonation_leaves_headers_to_curl() -> None:
    request = _process({"CURL_CFFI_OPTIONS": {"impersonate": "chrome"}})
    assert request.headers.get("User-Agent") is None
    assert request.headers.get("Accept-Language") is None


def test_spider_attribute_overrides_unset_setting() -> None:
    request = _process(spider_options={"impersonate": "chrome"})
    assert request.meta["curl_cffi_options"] == {"impersonate": "chrome"}
    assert request.headers.get("User-Agent") is None


def test_spider_default_request_headers_replace_setting() -> None:
    spidercls = type(
        "HeadersSpider",
        (Spider,),
        {"name": "headers", "default_request_headers": {"X-Spider": "1"}},
    )
    crawler = get_crawler(
        spidercls, {"DEFAULT_REQUEST_HEADERS": DEFAULT_REQUEST_HEADERS}
    )
    spider = spidercls.from_crawler(crawler)
    mw = DefaultHeadersMiddleware.from_crawler(crawler)
    mw.spider_opened(spider)
    request = Request("https://example.com/")
    mw.process_request(request, spider)
    assert request.headers.get("X-Spider") == b"1"
    assert request.headers.get("Accept-Language") is None


def test_request_meta_takes_precedence() -> None:
    crawler = get_crawler(PlainSpider, {"CURL_CFFI_OPTIONS": {"impersonate": "chrome"}})
    mw = CurlCffiMiddleware.from_crawler(crawler)
    request = Request("https://example.com/", meta={"curl_cffi_options": {"ja3": "x"}})
    mw.process_request(request)
    assert request.meta["curl_cffi_options"] == {"ja3": "x"}
