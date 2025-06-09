# usage: scrapy runspider examples/custom_headers_spider.py


from scrapy import Spider


class CustomHeadersSpider(Spider):
    name = "custom-headers"
    start_urls = ["https://browserleaks.com/ip"]
    curl_cffi_options = {
        "impersonate": "chrome136",
        "default_headers": False,  # disable curl-side default headers
    }
    default_request_headers = {  # enable scrapy-side default headers
        "Sec-Ch-Ua": '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',  # noqa: E501
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",  # noqa: E501
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",  # noqa: E501
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Priority": "u=0, i",
    }

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
        def extract_table(selector):
            return [sel.css("td::text").getall() for sel in selector.css("tr")]

        yield {"headers": extract_table(response.css("#headers"))}
