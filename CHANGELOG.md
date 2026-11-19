## v0.4.4 (2026-11-19)

### Fix

- keep Scrapy headers unless curl_cffi impersonates a browser (#7)

## v0.4.3 (2026-11-12)

### Fix

- correct Scrapy version gate in to_scrapy_download_error to < 2.15

## v0.4.2 (2026-10-28)

## v0.4.1 (2026-10-28)

### Feat

- set response protocol from curl_cffi http version

### Fix

- accept DOWNLOAD_BIND_ADDRESS on every supported Scrapy version

### Refactor

- inline _build_session_config into _init_session
- pass TLS version values to converters instead of settings
- read TLS version settings directly instead of via Scrapy private helper
- extract TLS version option composition to converters
- drop unreachable curl_cffi availability check in handlers
- move _TLS_VERSION_MAP to converters and Scrapy helper shims to utils
- default response protocol to None when unknown
- construct download errors from str(exc) only
- use qualified scrapy.exceptions names and version gate in converters

## v0.4.0 (2026-10-09)

### Feat

- reuse a shared AsyncSession across curl_cffi downloads

## v0.3.1 (2026-07-29)

### Fix

- rename handler module to handlers

## v0.3.0 (2026-07-28)

### Feat

- rename adapters module to converters
- rename handler module to handlers

### Fix

- Scrapy >= 2.14 handler compat + download_latency type fix (#1)
- basic-options spider start_urls

### Refactor

- typed return for to_curl_cffi_request_params

## v0.2.0 (2025-06-11)

### Feat

- use discard_cookies instead of dummy cookie jar
- support bindaddress request.meta

### Fix

- **docs**: correct settings snippet

### Refactor

- be pythonic

## v0.1.0 (2025-06-09)
