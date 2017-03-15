import atexit
import json
import logging
import socket
import sys
import time
import traceback

from threading import Timer

import requests

is_py2 = sys.version[0] == '2'
if is_py2:
    from Queue import Queue, Full, Empty
else:
    from queue import Queue, Full, Empty


class SplunkHandler(logging.Handler):
    """
    A logging handler to send events to a Splunk Enterprise instance
    running the Splunk HTTP Event Collector.
    """
    instances = []  # For keeping track of running class instances

    def __init__(self, host, port, token, index,
                 hostname=None, source=None, sourcetype='text',
                 verify=True, timeout=60, flush_interval=15.0,
                 queue_size=5000):

        SplunkHandler.instances.append(self)
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

        if hostname is None:
            self.hostname = socket.gethostname()
        else:
            self.hostname = hostname

        # prevent infinite recursion by silencing requests and urllib3 loggers
        logging.getLogger('requests').propagate = False

        # and do the same for ourselves
        logging.getLogger(__name__).propagate = False

        # disable all warnings from urllib3 package
        if not self.verify:
            requests.packages.urllib3.disable_warnings()

        # Start a worker thread responsible for sending logs
        self.timer = Timer(self.flush_interval, self._splunk_worker)
        self.timer.daemon = True  # Auto-kill thread if main process exits
        self.timer.start()

    def emit(self, record):
        record = self.format_record(record)
        try:
            # Put log message into queue; worker thread will pick up
            self.queue.put_nowait(record)
        except Full:
            print("Log queue full; log data will be dropped.")

    def format_record(self, record):
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

        return json.dumps(params)

    def _splunk_worker(self):
        queue_empty = True

        # Pull everything off the queue.
        while not self.queue.empty():
            try:
                item = self.queue.get(block=False)
                self.log_payload = self.log_payload + item
                self.queue.task_done()
            except Empty:
                pass

            # If the payload is getting very long, stop reading and send immediately.
            if not self.SIGTERM and len(self.log_payload) >= 524288:  # 50MB
                queue_empty = False
                break

        if self.log_payload:
            url = 'https://%s:%s/services/collector' % (self.host, self.port)

            try:
                r = requests.post(
                    url,
                    data=self.log_payload,
                    headers={'Authorization': "Splunk %s" % self.token},
                    verify=self.verify,
                    timeout=self.timeout,
                )
                r.raise_for_status()  # Throws exception for 4xx/5xx status

            except Exception as e:
                try:
                    print(traceback.format_exc())
                    print("Exception in Splunk logging handler: %s" % str(e))
                except:
                    pass

            self.log_payload = ""

        # Restart the timer
        timer_interval = self.flush_interval
        if not self.SIGTERM:
            if not queue_empty:
                timer_interval = 1.0  # Start up again right away if queue was not cleared

            self.timer = Timer(timer_interval, self._splunk_worker)
            self.timer.daemon = True  # Auto-kill thread if main process exits
            self.timer.start()

    def shutdown(self):
        self.SIGTERM = True
        self.timer.cancel()  # Cancels the scheduled Timer, allows exit immediatley

        # Send the remaining items that might be sitting in queue.
        self._splunk_worker()

    # Called when application exit imminent (main thread ended / got kill signal)
    @atexit.register
    def catch_exit():
        for instance in SplunkHandler.instances:
            try:
                instance.shutdown()
            except:
                pass
