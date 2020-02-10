from setuptools import setup, find_packages

with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(
    name='querysetdataframe',
    version="0.0.2",
    author="Oliver Chambers",
    long_description=long_description,
    url='https://github.com/VersBersh/QuerysetDataFrame',
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        'Topic :: Utilities',
    ],

)
