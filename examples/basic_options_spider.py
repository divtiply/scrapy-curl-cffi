# usage: scrapy runspider examples/basic_options_spider.py


from scrapy import Spider


class BasicOptionsSpider(Spider):
    name = "basic-options"
    start_urls = ["https://browserleaks.com/ip"]
    curl_cffi_options = {"impersonate": "chrome"}

    custom_settings = {
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_curl_cffi.handler.CurlCffiDownloadHandler",
            "https": "scrapy_curl_cffi.handler.CurlCffiDownloadHandler",
        },
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy_curl_cffi.middlewares.CurlCffiMiddleware": 200,
            "scrapy_curl_cffi.middlewares.DefaultHeadersMiddleware": 400,
            "scrapy_curl_cffi.middlewares.UserAgentMiddleware": 500,
            "scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware": None,  # noqa: E501
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
    }

    def parse(self, response):
        yield response.json()
