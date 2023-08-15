#!/bin/bash

flake8 "cs/aws_account" --count --exit-zero --max-complexity=15 --max-line-length=127 --statistics
pylint "cs/aws_account" --exit-zero --max-line-length=127 --disable=R0801 --ignore=tests
pydocstyle "cs/aws_account" --count