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

    import logging
    from splunk_handler import SplunkHandler

    splunk = SplunkHandler(
        host='splunk.example.com',
        port='8089',
        username='username',
        password='password',
        index='main'
    )

    logging.getLogger('').addHandler(splunk)

    logging.info('hello!')

I would recommend using a JSON formatter with this to receive your logs in JSON format.
Here is an open source one: https://github.com/madzak/python-json-logger


## Contributing

Feel free to contribute an issue or pull request:
1. Check for existing issues and PRs
2. Fork the repo, and clone it locally
3. Create a new branch for your contribution
4. Push to your fork and submit a pull request

## License

This project is licensed under the terms of the [MIT license](http://opensource.org/licenses/MIT).

