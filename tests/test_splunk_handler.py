import logging
import unittest

from splunk_handler import SplunkHandler

SPLUNK_HOST = 'splunk.example.com'
SPLUNK_PORT = '8089'
SPLUNK_USERNAME = 'admin'
SPLUNK_PASSWORD = 'password'
SPLUNK_INDEX = 'main'

RECEIVER_URL = 'https://%s:%s/services/receivers/simple' % (SPLUNK_HOST, SPLUNK_PORT)

class TestSplunkHandler(unittest.TestCase):
    def setUp(self):
        self.splunk = SplunkHandler(
            host=SPLUNK_HOST,
            port=SPLUNK_PORT,
            username=SPLUNK_USERNAME,
            password=SPLUNK_PASSWORD,
            index=SPLUNK_INDEX
        )

    def test_init(self):
        self.assertIsNotNone(self.splunk)
        self.assertIsInstance(self.splunk, SplunkHandler)
        self.assertIsInstance(self.splunk, logging.Handler)
        self.assertEqual(self.splunk.host, SPLUNK_HOST)
        self.assertEqual(self.splunk.port, SPLUNK_PORT)
        self.assertEqual(self.splunk.username, SPLUNK_USERNAME)
        self.assertEqual(self.splunk.password, SPLUNK_PASSWORD)
        self.assertEqual(self.splunk.index, SPLUNK_INDEX)

