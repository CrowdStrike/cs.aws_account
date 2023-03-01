import os
import unittest

from zope import component

from ..account import Account
from ..interfaces import IRegionalAccounts
from ..regional_account import RegionalAccount
from ..regional_accounts import RegionalAccounts
from ..session import Session
from ..testing import AWS_ACCOUNT_INTEGRATION_LAYER


class IntegrationTestAWSAccountRegionalAccounts(unittest.TestCase):

    level = 2

    def setUp(self):
        self.session_kwargs = {
            'aws_access_key_id':     os.environ.get('AWS_ACCESS_KEY_ID'),
            'aws_secret_access_key': os.environ.get('AWS_SECRET_ACCESS_KEY'),
        }
        self.session = Session(**self.session_kwargs)
        self.account = Account(self.session)
        self.ratelimit_kwargs = {'max_count': 1, 'interval': 1, 'block': False}
        self.filter = {'Partitions': {'aws': {'Regions': {'include': ['us-east-1']}}}}

        self.filter1_raccts = RegionalAccounts(
            self.ratelimit_kwargs, {'SessionParameters': self.session_kwargs}, self.filter)

        self.all_raccts = RegionalAccounts(
            self.ratelimit_kwargs, {'SessionParameters': self.session_kwargs})

    def test_account(self):
        self.assertEqual(self.filter1_raccts.account().account_id(), self.account.account_id())

    def test_getitem(self):
        self.assertTrue(isinstance(self.filter1_raccts['us-east-1'], RegionalAccount))
        with self.assertRaises(KeyError):
            self.filter1_raccts['bad']

    def test_get(self):
        self.assertTrue(isinstance(self.filter1_raccts.get('us-east-1'), RegionalAccount))
        self.assertIsNone(self.filter1_raccts.get('bad', None))

    def test_contains(self):
        self.assertTrue('us-east-1' in self.filter1_raccts)
        self.assertFalse('bad' in self.filter1_raccts)

    def test_keys(self):
        self.assertTrue('us-east-1' in self.filter1_raccts.keys())
        self.assertFalse('bad' in self.filter1_raccts.keys())

    def test_iter(self):
        self.assertEqual(list(self.filter1_raccts), ['us-east-1'])

    def test_values(self):
        self.assertEqual(len(self.filter1_raccts.values()), 1)
        self.assertTrue(isinstance(self.filter1_raccts.values()[0], RegionalAccount))

    def test_items(self):
        self.assertEqual(len(self.filter1_raccts.items()), 1)
        self.assertEqual(self.filter1_raccts.items()[0][0], 'us-east-1')
        self.assertTrue(isinstance(self.filter1_raccts.items()[0][1], RegionalAccount))

    def test_len(self):
        self.assertEqual(len(self.filter1_raccts), 1)

    def test_filter_application(self):
        self.assertGreater(len(self.all_raccts), len(self.filter1_raccts))
        self.assertIn('us-east-2', self.all_raccts)
        self.assertNotIn('us-east-2', self.filter1_raccts)

    def test_filter_mutation(self):
        self.assertIn('us-east-1', self.all_raccts)
        self.assertIn('us-east-2', self.all_raccts)
        self.all_raccts.filter['Partitions'] = {'aws': {'Regions': {'exclude': ['us-east-2']}}}
        self.assertNotIn('us-east-2', self.all_raccts)
        self.assertIn('us-east-1', self.all_raccts)


class IntegrationTestAWSAccountRegionalAccountsZCA(unittest.TestCase):

    layer = AWS_ACCOUNT_INTEGRATION_LAYER

    def setUp(self):
        # RateLimit, Account, Filter=None, RateLimitRegionSpec=None, service='ec2'
        self.kwargs = {
            'RateLimit': {'max_count': 1, 'interval': 1, 'block': False},
            'Account':  {
                'SessionParameters': {
                    'aws_access_key_id':     os.environ.get('AWS_ACCESS_KEY_ID'),
                    'aws_secret_access_key': os.environ.get('AWS_SECRET_ACCESS_KEY'),
                },
            },
            'Filter': {
                'Partitions': {'aws': {'Regions': {'include': ['us-east-1']}}},
            },
        }

    def test_factories(self):
        # non-cached
        ra = component.createObject(u"cs.aws_account.regional_accounts", **self.kwargs)
        self.assertTrue(IRegionalAccounts.providedBy(ra))

        # cached
        self.assertIs(
                component.createObject(u"cs.aws_account.cached_regional_accounts",
                                       **self.kwargs),
                component.createObject(u"cs.aws_account.cached_regional_accounts",
                                       **self.kwargs)
            )
