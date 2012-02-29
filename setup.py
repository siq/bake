from distutils.core import setup

setup(
    name='bake',
    version='1.0.a1',
    description='A project scripting utility for Python.',
    long_description=open('README.rst').read(),
    author='Jordan McCoy',
    author_email='mccoy.jordan@gmail.com',
    license='BSD',
    url='http://github.com/jordanm/bake',
    packages=['bake'],
    scripts=['bin/bake'],
)
