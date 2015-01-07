import logging
import socket
import traceback

from threading import Thread

import requests


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

    def _async_emit(self, record):

        try:

            params = {
                'host': socket.gethostname(),
                'index': self.index,
                'source': record.pathname,
                'sourcetype': 'json'
            }
            url = 'https://%s:%s/services/receivers/simple' % (self.host, self.port)
            payload = self.format(record)
            auth = (self.username, self.password)

            r = requests.post(
                url,
                auth=auth,
                data=payload,
                params=params
            )

            r.close()

        except Exception, e:

            print "Traceback:\n" + traceback.format_exc()
            print "Exception in Splunk logging handler: %s" % str(e)

