from setuptools import setup

setup(
    name='splunk_handler',
    version='2.0.8',
    license='MIT License',
    description='A Python logging handler that sends your logs to Splunk',
    long_description=open('README.md').read(),
    author='Zach Taylor',
    author_email='ztaylor234@gmail.com',
    url='https://github.com/zach-taylor/splunk_handler',
    packages=['splunk_handler'],
    install_requires=[
        'requests >= 2.6.0, < 3.0.0',
        'urllib3'
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: System :: Logging'
    ]
)
