from setuptools import setup

setup(
    name='pyli',
    version='1.4.1',
    author='thenoviceoof',
    author_email='thenoviceoof@gmail.com',
    packages=['pyli'],
    scripts=['bin/pyli'],
    url='https://github.com/thenoviceoof/pyli',
    license='LICENSE',
    description='Better python CLI integration',
    long_description=open('README.rst').read(),
    install_requires=[
    ],
    test_requires=[
        'nose'
    ],
    test_suite='tests',
)
