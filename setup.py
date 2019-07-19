from setuptools import setup, find_packages

with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(
    name='QuerysetDataFrame',
    version="0.0.1",
    author="Oliver Chambers",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/VersBersh/QuerysetDataFrame',
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        'Topic :: Utilities',
    ],

)
