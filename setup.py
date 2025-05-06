from setuptools import setup, find_packages

version = '1.3.4'

tests_require = [
    'zope.testrunner',
    'zope.configuration',
    'bandit',
    'coverage',
]


doc_tests_require = [
    'pyyaml',
    'Jinja2',
]


lint_require = [
    'flake8',
    'pydocstyle',
    'pylint',
]


with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()


setup(name='cs.aws_account',
      version=version,
      description="AWS account components",
      long_description=long_description,
      long_description_content_type='text/markdown',
      classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Operating System :: Unix",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Framework :: Zope",
        "Framework :: Flake8",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
      ],
      author='David Davis',
      author_email='david.davis@crowdstrike.com',
      maintainer='Forrest Aldridge',
      maintainer_email='forrest.aldridge@crowdstrike.com',
      url='https://github.com/CrowdStrike/cs.aws_account',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['cs'],
      include_package_data=True,
      package_data={
          '': ['*.zcml', '*.yaml', '*.md']
      },
      zip_safe=False,
      install_requires=[
          'setuptools',
          'zope.security',  # for zcml processing dep
          'zope.component',
          'zope.interface',
          'zope.schema',
          'boto3',
          'botocore',
          'cachetools',
          'cs.ratelimit'
      ],
      extras_require={
            'dev': tests_require + doc_tests_require + lint_require,
      },
      entry_points={},
      scripts=['util/run-tests.sh', 'util/lint.sh'],
      python_requires='>=3.8',
      )
