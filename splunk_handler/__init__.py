import logging
import socket
import traceback

from threading import Thread

import requests


class SplunkHandler(logging.Handler):
    """
    A logging handler to send events to a Splunk Enterprise instance
    """

    def __init__(self, host, port, username, password, index,
                 hostname=None, source=None, sourcetype='text', verify=True):

        logging.Handler.__init__(self)

        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.index = index
        self.source = source
        self.sourcetype = sourcetype
        self.verify = verify

        if hostname is None:
            self.hostname = socket.gethostname()
        else:
            self.hostname = hostname

        # prevent infinite recursion by silencing requests and urllib3 loggers
        logging.getLogger('requests').propagate = False
        logging.getLogger('urllib3').propagate = False

        # and do the same for ourselves
        logging.getLogger(__name__).propagate = False

    def emit(self, record):

        thread = Thread(target=self._async_emit, args=(record, ))

        thread.start()

    def _async_emit(self, record):

        try:

            if self.source is None:
                source = record.pathname
            else:
                source = self.source

            params = {
                'host': self.hostname,
                'index': self.index,
                'source': source,
                'sourcetype': self.sourcetype
            }
            url = 'https://%s:%s/services/receivers/simple' % (self.host, self.port)
            payload = self.format(record)
            auth = (self.username, self.password)

            r = requests.post(
                url,
                auth=auth,
                data=payload,
                params=params,
                verify=self.verify
            )

            r.close()

        except Exception, e:
            try:
                print traceback.format_exc()
                print "Exception in Splunk logging handler: %s" % str(e)
            except:
                pass

