import os
from distutils.core import setup

packages = []
for root, dirs, files in os.walk('bake'):
    if '__init__.py' in files:
        packages.append(root.replace('/', '.'))

setup(
    name='bake',
    version='1.0.0a1',
    description='A project scripting and build utility.',
    long_description=open('README.rst').read(),
    author='Jordan McCoy',
    author_email='mccoy.jordan@gmail.com',
    license='BSD',
    url='http://github.com/jordanm/bake',
    packages=packages,
    scripts=['bin/bake'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Environment :: Console',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Utilities',
    ]
)
