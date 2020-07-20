import atexit
import json
import logging
import socket
import time
import traceback
from threading import Timer

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

instances = []  # For keeping track of running class instances
DEFAULT_QUEUE_SIZE = 5000


# Called when application exit imminent (main thread ended / got kill signal)
@atexit.register
def perform_exit():
    for instance in instances:
        try:
            instance.shutdown()
        except Exception:
            pass


def force_flush():
    for instance in instances:
        try:
            instance.force_flush()
        except Exception:
            pass


def wait_until_empty():
    for instance in instances:
        try:
            instance.wait_until_empty()
        except Exception:
            pass


class SplunkHandler(logging.Handler):
    """
    A logging handler to send events to a Splunk Enterprise instance
    running the Splunk HTTP Event Collector.
    """

    def __init__(self, host, port, token, index,
                 allow_overrides=False, debug=False, flush_interval=15.0,
                 force_keep_ahead=False, hostname=None, protocol='https',
                 proxies=None, queue_size=DEFAULT_QUEUE_SIZE, record_format=False,
                 retry_backoff=2.0, retry_count=5, source=None,
                 sourcetype='text', timeout=60, url=None, verify=True):
        """
        Args:
            host (str): The Splunk host param
            port (int): The port the host is listening on
            token (str): Authentication token
            index (str): Splunk index to write to
            allow_overrides (bool): Whether to look for _<param> in log data (ex: _index)
            debug (bool): Whether to print debug console messages
            flush_interval (float): Frequency to push events to splunk host in microseconds
            force_keep_ahead (bool): Sleep instead of dropping logs when queue fills
            hostname (str): The Splunk Enterprise hostname
            protocol (str): The web protocol to use
            proxies (dict): The proxies to use for the request
            queue_size (int): The max number of logs to queue, set to 0 for no max
            record_format (bool): Whether the log record will be json
            retry_backoff (float): The requests lib backoff factor
            retry_count (int): The number of times to retry a failed request
            source (str): The Splunk source param
            sourcetype (str): The Splunk sourcetype param
            timeout (float): The time to wait for a response from Splunk
            url (str): Override of the url to send the event to
            verify (bool): Whether to perform ssl certificate validation
        """

        global instances
        instances.append(self)
        logging.Handler.__init__(self)

        self.allow_overrides = allow_overrides
        self.host = host
        self.port = port
        self.token = token
        self.index = index
        self.source = source
        self.sourcetype = sourcetype
        self.verify = verify
        self.timeout = timeout
        self.flush_interval = flush_interval
        self.force_keep_ahead = force_keep_ahead
        self.log_payload = ""
        self.SIGTERM = False  # 'True' if application requested exit
        self.timer = None
        # It is possible to get 'behind' and never catch up, so we limit the queue size
        self.queue = list()
        self.max_queue_size = max(queue_size, 0)  # 0 is min queue size
        self.debug = debug
        self.session = requests.Session()
        self.retry_count = retry_count
        self.retry_backoff = retry_backoff
        self.protocol = protocol
        self.proxies = proxies
        self.record_format = record_format
        if not url:
            self.url = '%s://%s:%s/services/collector' % (self.protocol, self.host, self.port)
        else:
            self.url = url

        # Keep ahead depends on queue size, so cannot be 0
        if self.force_keep_ahead and not self.max_queue_size:
            self.write_log("Cannot keep ahead of unbound queue, using default queue size")
            self.max_queue_size = DEFAULT_QUEUE_SIZE

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
        self.session.mount(self.protocol + '://', HTTPAdapter(max_retries=retry))

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

        if self.flush_interval <= 0:
            # Flush log immediately; is blocking call
            self._splunk_worker(payload=record)
            return

        self.write_debug_log("Writing record to log queue")

        # If force keep ahead, sleep until space in queue to prevent falling behind
        while self.force_keep_ahead and len(self.queue) >= self.max_queue_size:
            time.sleep(self.alt_flush_interval)

        # Put log message into queue; worker thread will pick up
        if not self.max_queue_size or len(self.queue) < self.max_queue_size:
            self.queue.append(record)
        else:
            self.write_log("Log queue full; log data will be dropped.")

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

        if self.record_format:
            try:
                record = json.dumps(record)
            except Exception:
                pass

        params = {
            'time': self.getsplunkattr(record, '_time', time.time()),
            'host': self.getsplunkattr(record, '_host', self.hostname),
            'index': self.getsplunkattr(record, '_index', self.index),
            'source': record.pathname if self.source is None else self.source,
            'sourcetype': self.getsplunkattr(record, '_sourcetype', self.sourcetype),
            'event': self.format(record)
        }

        self.write_debug_log("Record dictionary created")

        formatted_record = json.dumps(params, sort_keys=True)
        self.write_debug_log("Record formatting complete")

        return formatted_record

    def getsplunkattr(self, obj, attr, default=None):
        val = default
        if self.allow_overrides:
            val = getattr(obj, attr, default)
            try:
                delattr(obj, attr)
            except Exception:
                pass
        return val

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
            self.write_debug_log("Destination URL is " + self.url)

            try:
                self.write_debug_log("Sending payload: " + payload)
                r = self.session.post(
                    self.url,
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
                except Exception:
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
                    # Start up again right away if queue was not cleared
                    timer_interval = self.alt_flush_interval

                self.write_debug_log("Resetting timer thread")
                self.timer = Timer(timer_interval, self._splunk_worker)
                self.timer.daemon = True  # Auto-kill thread if main process exits
                self.timer.start()
                self.write_debug_log("Timer thread scheduled")

    def empty_queue(self):
        if len(self.queue) == 0:
            self.write_debug_log("Queue was empty")
            return True

        self.write_debug_log("Recursing through queue")
        if self.SIGTERM:
            self.log_payload += ''.join(self.queue)
            self.queue.clear()
        else:
            # without looking at each item, estimate how many can fit in 50 MB
            apprx_size_base = len(self.queue[0])
            # dont count more than what is in queue to ensure the same number as pulled are deleted
            count = min(int(524288 / apprx_size_base), len(self.queue))
            self.log_payload += ''.join(self.queue[:count])
            del self.queue[:count]
        self.write_debug_log("Queue task completed")

        return len(self.queue) > 0

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
            self.timer.cancel()  # Cancels the scheduled Timer, allows exit immediately

        self.write_debug_log("Starting up the final run of the worker thread before shutdown")
        # Send the remaining items that might be sitting in queue.
        self._splunk_worker()

    def wait_until_empty(self):
        self.write_debug_log("Waiting until queue empty")
        flush_interval = self.flush_interval
        self.flush_interval = .5

        while len(self.queue) > 0:
            self.write_debug_log("Current queue size: " + str(len(self.queue)))
            time.sleep(.5)

        self.flush_interval = flush_interval

    @property
    def alt_flush_interval(self):
        return min(1.0, self.flush_interval / 2)
