import asyncio

from twisted.internet import asyncioreactor

# install the asyncio reactor before anything imports
# twisted.internet.reactor, so get_crawler() and the handler's requirement
# check see the same reactor a real crawl would use; a SelectorEventLoop is
# required on Windows where the default loop is a ProactorEventLoop
asyncioreactor.install(asyncio.SelectorEventLoop())
