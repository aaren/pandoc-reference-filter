from setuptools import setup

try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except (IOError, ImportError):
    long_description = ''

setup(
    name="pandoc-internal-references",
    version='0.1',
    description="Image attributes and internal referencing in markdown",
    long_description=long_description,
    py_modules=['internalreferences'],
    author="Aaron O'Leary",
    author_email='dev@aaren.me',
    license='BSD 2-Clause',
    url='http://github.com/aaren/pandoc-internal-references',
    install_requires=['pandocfilters', ],
    entry_points={
        'console_scripts': [
            'internal-references = internalreferences:main',
        ],
    }
)
