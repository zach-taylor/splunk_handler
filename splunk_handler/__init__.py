import atexit
import json
import logging
import socket
import sys
import time
import traceback

from threading import Timer

import requests
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

is_py2 = sys.version[0] == '2'
if is_py2:
    from Queue import Queue, Full, Empty
else:
    from queue import Queue, Full, Empty

instances = []  # For keeping track of running class instances

# Called when application exit imminent (main thread ended / got kill signal)
@atexit.register
def perform_exit():
    for instance in instances:
        try:
            instance.shutdown()
        except:
            pass

class SplunkHandler(logging.Handler):
    """
    A logging handler to send events to a Splunk Enterprise instance
    running the Splunk HTTP Event Collector.
    """
    def __init__(self, host, port, token, index,
                 hostname=None, source=None, sourcetype='text',
                 verify=True, timeout=60, flush_interval=15.0,
                 queue_size=5000, debug=False, retry_count=5,
                 retry_backoff=2.0):

        global instances
        instances.append(self)
        logging.Handler.__init__(self)

        self.host = host
        self.port = port
        self.token = token
        self.index = index
        self.source = source
        self.sourcetype = sourcetype
        self.verify = verify
        self.timeout = timeout
        self.flush_interval = flush_interval
        self.log_payload = ""
        self.SIGTERM = False  # 'True' if application requested exit
        self.timer = None
        self.testing = False  # Used for slightly altering logic during unit testing
        # It is possible to get 'behind' and never catch up, so we limit the queue size
        self.queue = Queue(maxsize=queue_size)
        self.debug = debug
        self.session = requests.Session()
        self.retry_count = retry_count
        self.retry_backoff = retry_backoff

        self.write_log("Starting debug mode", is_debug=True)

        if hostname is None:
            self.hostname = socket.gethostname()
        else:
            self.hostname = hostname

        self.write_log("Preparing to override loggers", is_debug=True)

        # prevent infinite recursion by silencing requests and urllib3 loggers
        logging.getLogger('requests').propagate = False

        # and do the same for ourselves
        logging.getLogger(__name__).propagate = False

        # disable all warnings from urllib3 package
        if not self.verify:
            requests.packages.urllib3.disable_warnings()

        # Set up automatic retry with back-off
        self.write_log("Preparing to create a Requests session", is_debug=True)
        retry = Retry(total=self.retry_count,
                      backoff_factor=self.retry_backoff,
                      status_forcelist=[ 500, 502, 503, 504 ])
        self.session.mount('https://', HTTPAdapter(max_retries=retry))


        self.write_log("Preparing to spin off first worker thread Timer", is_debug=True)

        # Start a worker thread responsible for sending logs
        self.timer = Timer(self.flush_interval, self._splunk_worker)
        self.timer.daemon = True  # Auto-kill thread if main process exits
        self.timer.start()

        self.write_log("Class initialize complete", is_debug=True)

    def write_log(self, log_message, is_debug=False):
        if is_debug:
            if self.debug:
                print("[SplunkHandler DEBUG] " + log_message)
        else:
            print("[SplunkHandler] " + log_message)

    def emit(self, record):
        self.write_log("emit() called", is_debug=True)

        try:
            record = self.format_record(record)
        except Exception as e:
            self.write_log("Exception in Splunk logging handler: %s" % str(e))
            self.write_log(traceback.format_exc())
            return

        try:
            self.write_log("Writing record to log queue", is_debug=True)
            # Put log message into queue; worker thread will pick up
            self.queue.put_nowait(record)
        except Full:
            self.write_log("Log queue full; log data will be dropped.")

    def format_record(self, record):
        self.write_log("format_record() called", is_debug=True)

        if self.source is None:
            source = record.pathname
        else:
            source = self.source

        current_time = time.time()
        if self.testing:
            current_time = None

        params = {
            'time': current_time,
            'host': self.hostname,
            'index': self.index,
            'source': source,
            'sourcetype': self.sourcetype,
            'event': self.format(record),
        }

        self.write_log("Record dictionary created", is_debug=True)

        formatted_record = json.dumps(params, sort_keys=True)
        self.write_log("Record formatting complete", is_debug=True)

        return formatted_record

    def _splunk_worker(self):
        self.write_log("_splunk_worker() called", is_debug=True)

        queue_empty = True

        # Pull everything off the queue.
        while not self.queue.empty():
            self.write_log("Recursing through queue", is_debug=True)
            try:
                item = self.queue.get(block=False)
                self.log_payload = self.log_payload + item
                self.queue.task_done()
                self.write_log("Queue task completed", is_debug=True)
            except Empty:
                self.write_log("Queue was empty", is_debug=True)

            # If the payload is getting very long, stop reading and send immediately.
            if not self.SIGTERM and len(self.log_payload) >= 524288:  # 50MB
                queue_empty = False
                self.write_log("Payload maximum size exceeded, sending immediately", is_debug=True)
                break

        if self.log_payload:
            self.write_log("Payload available for sending", is_debug=True)
            url = 'https://%s:%s/services/collector' % (self.host, self.port)
            self.write_log("Destination URL is " + url, is_debug=True)

            try:
                self.write_log("Sending payload: " + self.log_payload, is_debug=True)
                r = self.session.post(
                    url,
                    data=self.log_payload,
                    headers={'Authorization': "Splunk %s" % self.token},
                    verify=self.verify,
                    timeout=self.timeout,
                )
                r.raise_for_status()  # Throws exception for 4xx/5xx status
                self.write_log("Payload sent successfully", is_debug=True)

            except Exception as e:
                try:
                    self.write_log("Exception in Splunk logging handler: %s" % str(e))
                    self.write_log(traceback.format_exc())
                except:
                    self.write_log("Exception encountered, but traceback could not be formatted", is_debug=True)

            self.log_payload = ""
        else:
            self.write_log("Timer thread executed but no payload was available to send", is_debug=True)

        # Restart the timer
        timer_interval = self.flush_interval
        if self.SIGTERM:
            self.write_log("Timer reset aborted due to SIGTERM received", is_debug=True)
        else:
            if not queue_empty:
                self.write_log("Queue not empty, scheduling timer to run immediately", is_debug=True)
                timer_interval = 1.0  # Start up again right away if queue was not cleared

            self.write_log("Resetting timer thread", is_debug=True)

            self.timer = Timer(timer_interval, self._splunk_worker)
            self.timer.daemon = True  # Auto-kill thread if main process exits
            self.timer.start()
            self.write_log("Timer thread scheduled", is_debug=True)

    def close(self):
        self.shutdown()
        logging.Handler.close(self)

    def shutdown(self):
        # Only initiate shutdown once
        if self.SIGTERM:
            return

        self.write_log("Immediate shutdown requested", is_debug=True)
        self.SIGTERM = True
        self.timer.cancel()  # Cancels the scheduled Timer, allows exit immediatley

        self.write_log("Starting up the final run of the worker thread before shutdown", is_debug=True)
        # Send the remaining items that might be sitting in queue.
        self._splunk_worker()
