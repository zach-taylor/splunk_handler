import logging
import unittest

import mock

from splunk_handler import SplunkHandler

SPLUNK_HOST = 'splunk.example.com'
SPLUNK_PORT = '8089'
SPLUNK_USERNAME = 'admin'
SPLUNK_PASSWORD = 'password'
SPLUNK_INDEX = 'main'
SPLUNK_HOSTNAME = 'localhost'
SPLUNK_SOURCE = 'test'
SPLUNK_SOURCETYPE = 'test'
SPLUNK_VERIFY = False

RECEIVER_URL = 'https://%s:%s/services/receivers/simple' % (SPLUNK_HOST, SPLUNK_PORT)

class TestSplunkHandler(unittest.TestCase):
    def setUp(self):
        self.splunk = SplunkHandler(
            host=SPLUNK_HOST,
            port=SPLUNK_PORT,
            username=SPLUNK_USERNAME,
            password=SPLUNK_PASSWORD,
            index=SPLUNK_INDEX,
            hostname=SPLUNK_HOSTNAME,
            source=SPLUNK_SOURCE,
            sourcetype=SPLUNK_SOURCETYPE,
            verify=SPLUNK_VERIFY
        )

    def tearDown(self):
        self.splunk = None

    def test_init(self):
        self.assertIsNotNone(self.splunk)
        self.assertIsInstance(self.splunk, SplunkHandler)
        self.assertIsInstance(self.splunk, logging.Handler)
        self.assertEqual(self.splunk.host, SPLUNK_HOST)
        self.assertEqual(self.splunk.port, SPLUNK_PORT)
        self.assertEqual(self.splunk.username, SPLUNK_USERNAME)
        self.assertEqual(self.splunk.password, SPLUNK_PASSWORD)
        self.assertEqual(self.splunk.index, SPLUNK_INDEX)
        self.assertEqual(self.splunk.hostname, SPLUNK_HOSTNAME)
        self.assertEqual(self.splunk.source, SPLUNK_SOURCE)
        self.assertEqual(self.splunk.sourcetype, SPLUNK_SOURCETYPE)
        self.assertEqual(self.splunk.verify, SPLUNK_VERIFY)

        self.assertFalse(logging.getLogger('requests').propagate)
        self.assertFalse(logging.getLogger('splunk_handler').propagate)


    @mock.patch('splunk_handler.Thread')
    def test_emit(self, thread):
        self.splunk.emit('hello')

        self.assertEqual(
            mock.call(target=self.splunk._async_emit, args=('hello',)),
            thread.mock_calls[0]
        )
        thread.return_value.start.assert_called_once_with()

    @mock.patch('splunk_handler.requests.post')
    def test_async_emit(self, post):
        log = logging.getLogger('test')
        log.addHandler(self.splunk)
        log.warning('hello!')

        post.assert_called_once_with(
            RECEIVER_URL,
            auth=(SPLUNK_USERNAME, SPLUNK_PASSWORD),
            data='hello!',
            params={
                'host': SPLUNK_HOSTNAME,
                'index': SPLUNK_INDEX,
                'source': SPLUNK_SOURCE,
                'sourcetype': SPLUNK_SOURCETYPE
            },
            verify=SPLUNK_VERIFY
        )


