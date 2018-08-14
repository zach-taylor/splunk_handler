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


def force_flush():
    for instance in instances:
        try:
            instance.force_flush()
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
                 retry_backoff=2.0, protocol='https', proxies = None,
                 record_format = False):

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
        self.protocol = protocol
        self.proxies = proxies
        self.record_format = record_format

        self.write_debug_log("Starting debug mode")

        if hostname is None:
            self.hostname = socket.gethostname()
        else:
            self.hostname = hostname

        self.write_debug_log("Preparing to override loggers")

        # prevent infinite recursion by silencing requests and urllib3 loggers
        logging.getLogger('requests').propagate = False
        logging.getLogger('urllib3').propagate = False

        # and do the same for ourselves
        logging.getLogger(__name__).propagate = False

        # disable all warnings from urllib3 package
        if not self.verify:
            requests.packages.urllib3.disable_warnings()
        
        if self.verify and self.protocol == 'http':
            print("[SplunkHandler DEBUG] " + 'cannot use SSL Verify and unsecure connection')
        
        if self.proxies is not None:
            self.session.proxies = self.proxies
            
        # Set up automatic retry with back-off
        self.write_debug_log("Preparing to create a Requests session")
        retry = Retry(total=self.retry_count,
                      backoff_factor=self.retry_backoff,
                      method_whitelist=False,  # Retry for any HTTP verb
                      status_forcelist=[500, 502, 503, 504])
        self.session.mount(self.protocol+'://', HTTPAdapter(max_retries=retry))

        self.start_worker_thread()

        self.write_debug_log("Class initialize complete")

    def emit(self, record):
        self.write_debug_log("emit() called")

        try:
            record = self.format_record(record)
        except Exception as e:
            self.write_log("Exception in Splunk logging handler: %s" % str(e))
            self.write_log(traceback.format_exc())
            return

        if self.flush_interval > 0:
            try:
                self.write_debug_log("Writing record to log queue")
                # Put log message into queue; worker thread will pick up
                self.queue.put_nowait(record)
            except Full:
                self.write_log("Log queue full; log data will be dropped.")
        else:
            # Flush log immediately; is blocking call
            self._splunk_worker(payload=record)

    def close(self):
        self.shutdown()
        logging.Handler.close(self)

    #
    # helper methods
    #

    def start_worker_thread(self):
        # Start a worker thread responsible for sending logs
        if self.flush_interval > 0:
            self.write_debug_log("Preparing to spin off first worker thread Timer")
            self.timer = Timer(self.flush_interval, self._splunk_worker)
            self.timer.daemon = True  # Auto-kill thread if main process exits
            self.timer.start()

    def write_log(self, log_message):
        print("[SplunkHandler] " + log_message)

    def write_debug_log(self, log_message):
        if self.debug:
            print("[SplunkHandler DEBUG] " + log_message)

    def format_record(self, record):
        self.write_debug_log("format_record() called")

        if self.source is None:
            source = record.pathname
        else:
            source = self.source

        current_time = time.time()
        if self.testing:
            current_time = None

        if self.record_format:
            try:
                record = json.dumps(record)
            except:
                pass
        
        params = {
            'time': current_time,
            'host': self.hostname,
            'index': self.index,
            'source': source,
            'sourcetype': self.sourcetype,
            'event': self.format(record),
        }

        self.write_debug_log("Record dictionary created")

        formatted_record = json.dumps(params, sort_keys=True)
        self.write_debug_log("Record formatting complete")

        return formatted_record

    def _splunk_worker(self, payload=None):
        self.write_debug_log("_splunk_worker() called")

        if self.flush_interval > 0:
            # Stop the timer. Happens automatically if this is called
            # via the timer, does not if invoked by force_flush()
            self.timer.cancel()

            queue_is_empty = self.empty_queue()

        if not payload:
            payload = self.log_payload

        if payload:
            self.write_debug_log("Payload available for sending")
            url = '%s://%s:%s/services/collector' % (self.protocol,self.host, self.port)
            self.write_debug_log("Destination URL is " + url)

            try:
                self.write_debug_log("Sending payload: " + payload)
                r = self.session.post(
                    url,
                    data=payload,
                    headers={'Authorization': "Splunk %s" % self.token},
                    verify=self.verify,
                    timeout=self.timeout
                )
                r.raise_for_status()  # Throws exception for 4xx/5xx status
                self.write_debug_log("Payload sent successfully")

            except Exception as e:
                try:
                    self.write_log("Exception in Splunk logging handler: %s" % str(e))
                    self.write_log(traceback.format_exc())
                except:
                    self.write_debug_log("Exception encountered," +
                                         "but traceback could not be formatted")

            self.log_payload = ""
        else:
            self.write_debug_log("Timer thread executed but no payload was available to send")

        # Restart the timer
        if self.flush_interval > 0:
            timer_interval = self.flush_interval
            if self.SIGTERM:
                self.write_debug_log("Timer reset aborted due to SIGTERM received")
            else:
                if not queue_is_empty:
                    self.write_debug_log("Queue not empty, scheduling timer to run immediately")
                    timer_interval = 1.0  # Start up again right away if queue was not cleared

                self.write_debug_log("Resetting timer thread")
                self.timer = Timer(timer_interval, self._splunk_worker)
                self.timer.daemon = True  # Auto-kill thread if main process exits
                self.timer.start()
                self.write_debug_log("Timer thread scheduled")

    def empty_queue(self):
        while not self.queue.empty():
            self.write_debug_log("Recursing through queue")
            try:
                item = self.queue.get(block=False)
                self.log_payload = self.log_payload + item
                self.queue.task_done()
                self.write_debug_log("Queue task completed")
            except Empty:
                self.write_debug_log("Queue was empty")

            # If the payload is getting very long, stop reading and send immediately.
            if not self.SIGTERM and len(self.log_payload) >= 524288:  # 50MB
                self.write_debug_log("Payload maximum size exceeded, sending immediately")
                return False

        return True

    def force_flush(self):
        self.write_debug_log("Force flush requested")
        self._splunk_worker()

    def shutdown(self):
        self.write_debug_log("Immediate shutdown requested")

        # Only initiate shutdown once
        if self.SIGTERM:
            return

        self.write_debug_log("Setting instance SIGTERM=True")
        self.SIGTERM = True

        if self.flush_interval > 0:
            self.timer.cancel()  # Cancels the scheduled Timer, allows exit immediatley

        self.write_debug_log("Starting up the final run of the worker thread before shutdown")
        # Send the remaining items that might be sitting in queue.
        self._splunk_worker()
