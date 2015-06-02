
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

with open('requirements.txt') as f:
    requirements = f.read()

with open('extra_test_requirements.txt') as f:
    extra_test_requirements = f.read()

with open('extra_requirements.txt') as f:
    requirements += f.read()

setup(
    name='phabula',
    version='0.1.0',
    description='Update/News (blog) extension to the psyion web framework',
    long_description=readme + '\n\n' + history,
    author='Julian Paul Glass',
    author_email='julian@psyrium.com.au',
    url='https://github.com/joulez/phabula',
    packages=[
        'phabula',
    ],
    package_dir={'phabula':
                 'phabula'},
    include_package_data=True,
    install_requires=requirements,
    license="BSD",
    zip_safe=False,
    keywords='phabula',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    extras_require={'testing': extra_test_requirements},
    test_suite='phabula.tests'
)

# vim:set sw=4 sts=4 st=4 et tw=79:
