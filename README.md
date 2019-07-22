# Splunk Handler

[![Build](https://img.shields.io/travis/zach-taylor/splunk_handler.svg?style=flat-square)](https://travis-ci.org/zach-taylor/splunk_handler)
[![Code Climate](https://img.shields.io/codeclimate/maintainability/zach-taylor/splunk_handler.svg?style=flat-square)](https://codeclimate.com/github/zach-taylor/splunk_handler/maintainability)
[![PyPI](https://img.shields.io/pypi/v/splunk_handler.svg?style=flat-square)](https://pypi.python.org/pypi/splunk_handler)

**Splunk Handler is a Python Logger for sending logged events to an installation of Splunk Enterprise. or an instance of Splunk Cloud**

*This logger requires the splunk server to have the [Splunk HTTP Event Collector](http://dev.splunk.com/view/event-collector/SP-CAAAE6M). enabled and configured*

## A Note on Using with AWS Lambda

[AWS Lambda](https://aws.amazon.com/lambda/) has a custom implementation of Python Threading, and does not signal when the main thread exits. Because of this, it is possible to have Lambda halt execution while logs are still being processed. To ensure that execution does not terminate prematurely, Lambda users will be required to invoke splunk_handler.force_flush directly as the very last call in the Lambda handler, which will block the main thread from exiting until all logs have processed.
~~~python
from splunk_handler import force_flush

def lambda_handler(event, context):
    do_work()
    force_flush()  # Flush logs in a blocking manner
~~~


## Installation

Pip:

    pip install splunk_handler

Manual:

    python setup.py install

## Usage

    from splunk_handler import SplunkHandler

Then use it like any other regular Python [logging handler](https://docs.python.org/2/howto/logging.html#handlers).

Example:

~~~python
    import logging
    from splunk_handler import SplunkHandler

    splunk = SplunkHandler(
        host='splunk.example.com',
        port='8088',
        token='851A5E58-4EF1-7291-F947-F614A76ACB21',
        index='main'
        #hostname='hostname', # manually set a hostname parameter, defaults to socket.gethostname()
        #source='source', # manually set a source, defaults to the log record.pathname
        #sourcetype='sourcetype', # manually set a sourcetype, defaults to 'text'
        #verify=True, # turn SSL verification on or off, defaults to True
        #timeout=60, # timeout for waiting on a 200 OK from Splunk server, defaults to 60s
        #flush_interval=15.0, # send batch of logs every n sec, defaults to 15.0, set '0' to block thread & send immediately
        #queue_size=5000, # a throttle to prevent resource overconsumption, defaults to 5000
        #debug=False, # turn on debug mode; prints module activity to stdout, defaults to False
        #retry_count=5, # Number of retry attempts on a failed/erroring connection, defaults to 5
        #retry_backoff=2.0,  # Backoff factor, default options will retry for 1 min, defaults to 2.0
        #cloud=False # turn on Splunk Cloud support node. this changes the URL used to upload events
    )

    logging.getLogger('').addHandler(splunk)

    logging.warning('hello!')
~~~

I would recommend using a JSON formatter with this to receive your logs in JSON format.
Here is an open source one: https://github.com/madzak/python-json-logger

### Logging Config

Sometimes it's a good idea to create a logging configuration using a Python dict
and the `logging.config.dictConfig` function. This method is used by default in Django.

Below is an example dictionary config and how it might be used in a settings file.

(This example assumes that the python-json-logger package is installed)


~~~python
import os

# Splunk settings
SPLUNK_HOST = os.getenv('SPLUNK_HOST', 'splunk.example.com')
SPLUNK_PORT = int(os.getenv('SPLUNK_PORT', '8088'))
SPLUNK_TOKEN = os.getenv('SPLUNK_TOKEN', '851A5E58-4EF1-7291-F947-F614A76ACB21')
SPLUNK_INDEX = os.getenv('SPLUNK_INDEX', 'main')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(created)f %(exc_info)s %(filename)s %(funcName)s %(levelname)s %(levelno)s %(lineno)d %(module)s %(message)s %(pathname)s %(process)s %(processName)s %(relativeCreated)d %(thread)s %(threadName)s'
        }
    },
    'handlers': {
        'splunk': {
            'level': 'DEBUG',
            'class': 'splunk_handler.SplunkHandler',
            'formatter': 'json',
            'host': SPLUNK_HOST,
            'port': SPLUNK_PORT,
            'token': SPLUNK_TOKEN,
            'index': SPLUNK_INDEX,
            'sourcetype': 'json',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        }
    },
    'loggers': {
        '': {
            'handlers': ['console', 'splunk'],
            'level': 'DEBUG'
        }
    }
}
~~~

Then, do `logging.config.dictConfig(LOGGING)` to configure your logging.

Note: I included a configuration for the JSON formatter mentioned above.

## Retry Logic

This library uses the built-in retry logic from urllib3 (a retry
counter and a backoff factor). Should the defaults not be desireable,
you can find more information about how to best configure these
settings in the [urllib3 documentation](https://github.com/kennethreitz/requests/blob/b2289cd2d5d21bd31cf4a818a4e0ff6951b2317a/requests/packages/urllib3/util/retry.py#L104).

## Contributing

Feel free to contribute an issue or pull request:

1. Check for existing issues and PRs
2. Fork the repo, and clone it locally
3. Create a new branch for your contribution
4. Push to your fork and submit a pull request

## License

This project is licensed under the terms of the [MIT license](http://opensource.org/licenses/MIT).
