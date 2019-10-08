import logging
import unittest

import mock

from splunk_handler import SplunkHandler

# These are intentionally different than the kwarg defaults
SPLUNK_HOST = 'splunk-server.example.com'
SPLUNK_PORT = 1234
SPLUNK_TOKEN = '851A5E58-4EF1-7291-F947-F614A76ACB21'
SPLUNK_INDEX = 'test_index'
SPLUNK_HOSTNAME = 'test_host'
SPLUNK_SOURCE = 'test_source'
SPLUNK_SOURCETYPE = 'test_sourcetype'
SPLUNK_VERIFY = False
SPLUNK_TIMEOUT = 27
SPLUNK_FLUSH_INTERVAL = 5.0
SPLUNK_QUEUE_SIZE = 1111
SPLUNK_DEBUG = False
SPLUNK_RETRY_COUNT = 1
SPLUNK_RETRY_BACKOFF = 0.1

RECEIVER_URL = 'https://%s:%s/services/collector' % (SPLUNK_HOST, SPLUNK_PORT)


class TestSplunkHandler(unittest.TestCase):
    def setUp(self):
        self.splunk = SplunkHandler(
            host=SPLUNK_HOST,
            port=SPLUNK_PORT,
            token=SPLUNK_TOKEN,
            index=SPLUNK_INDEX,
            hostname=SPLUNK_HOSTNAME,
            source=SPLUNK_SOURCE,
            sourcetype=SPLUNK_SOURCETYPE,
            verify=SPLUNK_VERIFY,
            timeout=SPLUNK_TIMEOUT,
            flush_interval=SPLUNK_FLUSH_INTERVAL,
            queue_size=SPLUNK_QUEUE_SIZE,
            debug=SPLUNK_DEBUG,
            retry_count=SPLUNK_RETRY_COUNT,
            retry_backoff=SPLUNK_RETRY_BACKOFF,
        )
        self.splunk.testing = True

    def tearDown(self):
        self.splunk = None

    def test_init(self):
        self.assertIsNotNone(self.splunk)
        self.assertIsInstance(self.splunk, SplunkHandler)
        self.assertIsInstance(self.splunk, logging.Handler)
        self.assertEqual(self.splunk.host, SPLUNK_HOST)
        self.assertEqual(self.splunk.port, SPLUNK_PORT)
        self.assertEqual(self.splunk.token, SPLUNK_TOKEN)
        self.assertEqual(self.splunk.index, SPLUNK_INDEX)
        self.assertEqual(self.splunk.hostname, SPLUNK_HOSTNAME)
        self.assertEqual(self.splunk.source, SPLUNK_SOURCE)
        self.assertEqual(self.splunk.sourcetype, SPLUNK_SOURCETYPE)
        self.assertEqual(self.splunk.verify, SPLUNK_VERIFY)
        self.assertEqual(self.splunk.timeout, SPLUNK_TIMEOUT)
        self.assertEqual(self.splunk.flush_interval, SPLUNK_FLUSH_INTERVAL)
        self.assertEqual(self.splunk.max_queue_size, SPLUNK_QUEUE_SIZE)
        self.assertEqual(self.splunk.debug, SPLUNK_DEBUG)
        self.assertEqual(self.splunk.retry_count, SPLUNK_RETRY_COUNT)
        self.assertEqual(self.splunk.retry_backoff, SPLUNK_RETRY_BACKOFF)

        self.assertFalse(logging.getLogger('requests').propagate)
        self.assertFalse(logging.getLogger('splunk_handler').propagate)

    @mock.patch('requests.Session.post')
    def test_splunk_worker(self, mock_request):
        # Silence root logger
        log = logging.getLogger('')
        for h in log.handlers:
            log.removeHandler(h)

        log = logging.getLogger('test')
        log.addHandler(self.splunk)
        log.warning('hello!')

        self.splunk.timer.join()  # Have to wait for the timer to exec

        expected_output = '{"event": "hello!", "host": "%s", "index": "%s", "source": "%s", ' \
                          '"sourcetype": "%s", "time": null}' % \
                          (SPLUNK_HOSTNAME, SPLUNK_INDEX, SPLUNK_SOURCE, SPLUNK_SOURCETYPE)

        mock_request.assert_called_once_with(
            RECEIVER_URL,
            verify=SPLUNK_VERIFY,
            data=expected_output,
            timeout=SPLUNK_TIMEOUT,
            headers={'Authorization': "Splunk %s" % SPLUNK_TOKEN},
        )
