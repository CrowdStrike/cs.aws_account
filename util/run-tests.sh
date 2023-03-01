#!/bin/bash

TEST_PATTERN=""
if ! [ -z "$1" ]
then
  TEST_PATTERN="-t ${1}"
fi

coverage run --rcfile=util/coverage.config -m zope.testrunner --test-path=build/lib/ ${TEST_PATTERN}
coverage report
bandit -r cs/aws_account
