from setuptools import setup

setup(
    name='splunk_handler',
    version='3.0.1',
    license='MIT License',
    description='A Python logging handler that sends your logs to Splunk',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Zach Taylor',
    author_email='ztaylor234@gmail.com',
    url='https://github.com/zach-taylor/splunk_handler',
    packages=['splunk_handler'],
    install_requires=['requests >= 2.25.0, < 3.0.0'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: System :: Logging'
    ]
)
