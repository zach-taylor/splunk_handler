from distutils.core import setup

setup(
    name = 'splunk_handler',
    version = '1.1.1',
    license = 'MIT License',
    description = 'A Python logging handler that sends your logs to Splunk',
    long_description = open('README.md').read(),
    author = 'Zach Taylor',
    author_email = 'ztaylor234@gmail.com',
    url = 'https://github.com/zach-taylor/splunk_handler',
    packages = ['splunk_handler'],
    install_requires = ['requests==2.5.1'],
    classifiers = [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: System :: Logging'
    ]
)
