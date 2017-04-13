# Splunk Handler

[![Build](https://img.shields.io/travis/zach-taylor/splunk_handler.svg?style=flat-square)](https://travis-ci.org/zach-taylor/splunk_handler)
[![Code Climate](https://img.shields.io/codeclimate/github/zach-taylor/splunk_handler.svg?style=flat-square)](https://codeclimate.com/github/zach-taylor/splunk_handler)
[![PyPI](https://img.shields.io/pypi/v/splunk_handler.svg?style=flat-square)](https://pypi.python.org/pypi/splunk_handler)

**Splunk Handler is a Python Logger for sending logged events to an installation of Splunk Enterprise.**

*This logger requires the destination Splunk Enterprise server to have enabled and configured the [Splunk HTTP Event Collector](http://dev.splunk.com/view/event-collector/SP-CAAAE6M).*

## A Note on Using with AWS Lambda

[AWS Lambda](https://aws.amazon.com/lambda/) has a custom implementation of Python Threading, and does not signal when the main thread exits. Because of this, it is possible to have Lambda halt execution while logs are still being processed. To ensure that execution does not terminate prematurely, Lambda users will be required to invoke splunk_handler.perform_exit directly as the very last call in the Lambda handler, which will block the main thread from exiting until all logs have processed.
~~~python
from splunk_handler import perform_exit

def lambda_handler(event, context):
    do_work()
    perform_exit()  # Flush logs and shut down processing
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
        #flush_interval=15.0, # send batches of log statements every n seconds, defaults to 15.0
        #queue_size=5000, # a throttle to prevent resource overconsumption, defaults to 5000
        #debug=False, # turn on debug mode; prints module activity to stdout, defaults to False
    )

    logging.getLogger('').addHandler(splunk)

    logging.warning('hello!')
~~~

I would recommend using a JSON formatter with this to receive your logs in JSON format.
Here is an open source one: https://github.com/madzak/python-json-logger

### Logging Config

Sometimes it's a good idea to create a logging configuration using a Python dict
and the `logging.config.dictConfig` function. This method is used by default in Django.

Here is an example dictionary config and how it might be used in a settings file:

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

## Contributing

Feel free to contribute an issue or pull request:

1. Check for existing issues and PRs
2. Fork the repo, and clone it locally
3. Create a new branch for your contribution
4. Push to your fork and submit a pull request

## License

This project is licensed under the terms of the [MIT license](http://opensource.org/licenses/MIT).
