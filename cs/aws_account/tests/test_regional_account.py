from datetime import timedelta
import os
import unittest

from cs.ratelimit import RateLimitProperties, RateLimitExceeded
from zope import component

from ..account import Account
from ..interfaces import IRegionalAccount
from ..regional_account import RegionalAccount
from ..session import Session
from ..testing import AWS_ACCOUNT_INTEGRATION_LAYER


class IntegrationTestAWSAccountRegionalAccount(unittest.TestCase):

    level = 2

    def setUp(self):
        self.session_kwargs = {'aws_access_key_id':     os.environ.get('AWS_ACCESS_KEY_ID'),
                               'aws_secret_access_key': os.environ.get('AWS_SECRET_ACCESS_KEY')}
        self.session = Session(**self.session_kwargs)
        self.account = Account(self.session)
        self.ratelimit = RateLimitProperties(max_count=1, interval=timedelta(seconds=10), block=False)
        self.ra = RegionalAccount(self.ratelimit, self.account, region_name='us-east-1')

    def test_region(self):
        self.assertEqual(self.ra.region(), 'us-east-1')

    def test_account(self):
        self.assertIs(self.ra.account(), self.account)

    def test_call_client(self):
        self.ra.call_client('sts', 'get_caller_identity')
        with self.assertRaises(RateLimitExceeded):
            self.ra.call_client('sts', 'get_caller_identity')
        self.ra.ratelimit.max_count = 2
        self.ra.call_client('sts', 'get_caller_identity')

    def test_get_paginator(self):
        paginator = self.ra.get_paginator('ec2', 'describe_instances')
        page_iterator = paginator.paginate(PaginationConfig={'MaxItems': 10})
        next(page_iterator.__iter__())
        with self.assertRaises(RateLimitExceeded):
            next(page_iterator.__iter__())
        self.ra.ratelimit.max_count = 2
        next(page_iterator.__iter__())


class IntegrationTestAWSAccountRegionalAccountZCA(unittest.TestCase):

    layer = AWS_ACCOUNT_INTEGRATION_LAYER

    def setUp(self):
        self.session_kwargs = {'aws_access_key_id':     os.environ.get('AWS_ACCESS_KEY_ID'),
                               'aws_secret_access_key': os.environ.get('AWS_SECRET_ACCESS_KEY')}
        self.session = Session(**self.session_kwargs)
        self.account = Account(self.session)
        self.ratelimit = RateLimitProperties(max_count=1, interval=timedelta(seconds=1), block=False)

    def test_factories(self):
        # non-cached
        ra = component.createObject(
            u"cs.aws_account.regional_account", self.ratelimit, self.account, region_name='us-east-1')
        self.assertTrue(IRegionalAccount.providedBy(ra))

        # cached
        self.assertIs(
                component.createObject(u"cs.aws_account.cached_regional_account",
                                       Account={'SessionParameters': self.session_kwargs}),
                component.createObject(u"cs.aws_account.cached_regional_account",
                                       Account={'SessionParameters': self.session_kwargs})
            )
