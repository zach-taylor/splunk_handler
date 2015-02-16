# Splunk Handler

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
        port='8089',
        username='username',
        password='password',
        index='main'
        #hostname='hostname', # manually set a hostname parameter, defaults to socket.gethostname()
        #source='source', # manually set a source, defaults to the log record.pathname
        #sourcetype='sourcetype', # manually set a sourcetype, defaults to 'text'
        #verify=True # turn SSL verification on or off, defaults to True
    )

    logging.getLogger('').addHandler(splunk)

    logging.warning('hello!')
~~~

I would recommend using a JSON formatter with this to receive your logs in JSON format.
Here is an open source one: https://github.com/madzak/python-json-logger

### Logging Config

Sometimes it's a good idea to create a logging configuration using a Python dict
and the `logging.config.dictConfig` function. This method is used by default in Django.

Here is an example dictionary config:

~~~python
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
                'username': SPLUNK_USERNAME,
                'password': SPLUNK_PASSWORD,
                'index': SPLUNK_INDEX,
                'sourcetype': 'json'
            },
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'json'
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

