from setuptools import setup, find_packages

version = '1.0.9'

tests_require = [
    'zope.testrunner',
    'zope.configuration'
]

doc_tests_require = [
    'pyyaml',
    'Jinja2'
]

setup(name='cs.aws_account',
      version=version,
      description="AWS account components",
      long_description=open("README.md").read() + "\n" +
                       open("HISTORY.txt").read(),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: Other/Proprietary License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
      ],
      author='David Davis',
      author_email='david.davis@crowdstrike.com',
      url='http://stash.cs.sys/projects/PSO/repos/cs.aws_account/browse',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['cs'],
      include_package_data=True,
      package_data = {
          '': ['*.zcml', '*.yaml']
        },
      zip_safe=False,
      install_requires=[
          'setuptools',
          'zope.security', # for zcml processing dep
          'zope.component',
          'zope.interface',
          'zope.schema',
          'boto3',
          'botocore',
          'cachetools',
          'cs.ratelimit'
      ],
      extras_require={
            'testing': tests_require,
            'doc_testing': doc_tests_require
      },
      entry_points={
          },
      )
