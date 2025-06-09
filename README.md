# scrapy-curl-cffi

[Scrapy][1] integration with [curl_cffi][2] ([curl-impersonate][3]).

## Installation

```sh
pip install scrapy-curl-cffi
```

Another option, to enable Scrapy's support for modern HTTP compression
protocols:

```sh
pip install scrapy-curl-cffi[compression]
```

## Configuration

Update your Scrapy project settings as follows:

```python
DOWNLOAD_HANDLERS = {
    "http": "scrapy_curl_cffi.handler.CurlCffiDownloadHandler",
    "https": "scrapy_curl_cffi.handler.CurlCffiDownloadHandler",
}

DOWNLOADER_MIDDLEWARES = {
    "scrapy_curl_cffi.middlewares.CurlCffiMiddleware": 200,
    "scrapy_curl_cffi.middlewares.DefaultHeadersMiddleware": 400,
    "scrapy_curl_cffi.middlewares.UserAgentMiddleware": 500,
    "scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware": None,
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
}

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
```

## Usage

To download a [`scrapy.Request`][4] with `curl_cffi`, add the
`curl_cffi_options` special key to the [`Request.meta`][5] attribute. The value
should be a dict with any of the following options:

- `impersonate` (`str`) - which browser version to impersonate
- `default_headers` (`bool`) - whether to set default browser headers when
  impersonating (default: `True`)
- `ja3` (`str`) - ja3 string to impersonate
- `akamai` (`str`) - akamai string to impersonate
- `extra_fp` (`str`) - extra fingerprints options, in complement to ja3 and
  akamai strings
- `verify` (`bool`) - whether to verify https certs (default: `False`)

See the [curl_cffi documentation][6] for more info on these options.

Alternatively, you can use the `curl_cffi_options` spider attribute or the
`CURL_CFFI_OPTIONS` setting to automatically assign the `curl_cffi_options` meta
for all requests.

### Example spider

```python
class FingerprintsSpider(scrapy.Spider):
    name = "fingerprints"
    start_urls = ["https://tls.browserleaks.com/json"]
    curl_cffi_options = {"impersonate": "chrome"}

    def parse(self, response):
        yield response.json()
```

## Similar projects

- [scrapy-impersonate](https://github.com/jxlil/scrapy-impersonate)
- [scrapy-fingerprint](https://github.com/tieyongjie/scrapy-fingerprint)

[1]: https://github.com/scrapy/scrapy
[2]: https://github.com/lexiforest/curl_cffi
[3]: https://github.com/lexiforest/curl-impersonate
[4]: https://docs.scrapy.org/en/latest/topics/request-response.html#request-objects
[5]: https://docs.scrapy.org/en/latest/topics/request-response.html#scrapy.Request.meta
[6]: https://curl-cffi.readthedocs.io
