import logging
import socket
import traceback

from threading import Thread
from splunklib import client

_client = None


class SplunkFilter(logging.Filter):
    """
    A logging filter for Splunk's debug logs on the root logger to avoid recursion
    """

    def filter(self, record):
        return not (record.module == 'binding' and record.levelno == logging.DEBUG)


class SplunkHandler(logging.Handler):
    """
    A logging handler to send events to a Splunk Enterprise instance
    """

    def __init__(self, host, port, username, password, index):

        logging.Handler.__init__(self)

        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.index = index

    def emit(self, record):

        thread = Thread(target=self._async_emit, args=(record, ))

        thread.start()

    def _init_client(self):

        return client.connect(
                   host=self.host,
                   port=self.port,
                   username=self.username,
                   password=self.password)

    def _async_emit(self, record):

        global _client

        if not _client:
            _client = self._init_client()

        try:
            _client.indexes[self.index].submit(
                 self.format(record),
                 host=socket.gethostname(),
                 source=record.pathname,
                 sourcetype='json')

        except Exception, e:

            print "Traceback:\n" + traceback.format_exc()
            print "Exception in Splunk logging handler: %s" % str(e)

