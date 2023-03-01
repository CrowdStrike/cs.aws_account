import os
import unittest

from zope import component

from ..account import Account
from ..interfaces import IRegionalAccountSet
from ..regional_account import RegionalAccount
from ..regional_account_set import RegionalAccountSet
from ..regional_accounts import RegionalAccounts, regional_accounts_factory
from ..session import Session
from ..testing import AWS_ACCOUNT_INTEGRATION_LAYER


class IntegrationTestAWSAccountRegionalAccountSet(unittest.TestCase):

    level = 2

    def setUp(self):
        self.session_kwargs = {
            'aws_access_key_id':     os.environ.get('AWS_ACCESS_KEY_ID'),
            'aws_secret_access_key': os.environ.get('AWS_SECRET_ACCESS_KEY'),
        }
        self.session = Session(**self.session_kwargs)
        self.account = Account(self.session)
        self.ratelimit_kwargs = {'max_count': 1, 'interval': 1, 'block': False}
        self.filter1 = {
            'Partitions': {
                'aws': {
                    'Regions': {'include': ['us-east-1']},
                },
            },
        }
        self.filter2 = {
            'Partitions': {
                'aws': {
                    'Regions': {'include': ['us-east-2']},
                },
            },
        }

        self.filter1_raccts = RegionalAccounts(
            self.ratelimit_kwargs, {'SessionParameters': self.session_kwargs}, self.filter1)
        self.filter2_raccts = RegionalAccounts(
            self.ratelimit_kwargs, {'SessionParameters': self.session_kwargs}, self.filter2)
        self.all_raccts = RegionalAccounts(self.ratelimit_kwargs, {'SessionParameters': self.session_kwargs})
        self.racct_set = RegionalAccountSet(self.filter1_raccts, self.filter2_raccts)

    def test_init_add_remove_values(self):
        self.assertEqual(len(self.racct_set.values()), 2)
        self.assertTrue(isinstance(list(self.racct_set.values())[0], RegionalAccounts))
        self.assertIn(self.filter1_raccts, self.racct_set.values())
        self.assertIn(self.filter2_raccts, self.racct_set.values())

        self.racct_set.discard(self.filter2_raccts)
        self.assertIn(self.filter1_raccts, self.racct_set.values())
        self.assertNotIn(self.filter2_raccts, self.racct_set.values())
        self.racct_set.discard(self.filter2_raccts)  # no error

        self.racct_set.add(self.filter2_raccts)
        self.assertIn(self.filter1_raccts, self.racct_set.values())
        self.assertIn(self.filter2_raccts, self.racct_set.values())
        self.racct_set.add(self.filter2_raccts)  # no error

    def test_iter(self):
        self.assertEqual(len(list(self.racct_set)), 2)
        self.assertTrue(isinstance(list(self.racct_set)[0], RegionalAccount))
        self.assertTrue(isinstance(list(self.racct_set)[1], RegionalAccount))
        self.assertIn(self.filter1_raccts['us-east-1'], self.racct_set)
        self.assertIn(self.filter2_raccts['us-east-2'], self.racct_set)
        self.assertNotIn(self.all_raccts['us-west-1'], self.racct_set)

        self.racct_set.discard(self.filter2_raccts)
        self.assertIn(self.filter1_raccts['us-east-1'], self.racct_set)
        self.assertNotIn(self.filter2_raccts['us-east-2'], self.racct_set)
        self.assertEqual(len(list(self.racct_set)), 1)

        self.racct_set.add(self.all_raccts)
        self.assertEqual(len(list(self.racct_set)), len(self.all_raccts))  # tests redundant removals


class IntegrationTestAWSAccountRegionalAccountSetZCA(unittest.TestCase):

    layer = AWS_ACCOUNT_INTEGRATION_LAYER

    def setUp(self):

        self.args = [
            {
                'RegionalAccounts': {
                    'RateLimit': {'max_count': 1, 'interval': 1, 'block': False},
                    'Account':  {
                        'SessionParameters': {
                            'aws_access_key_id': os.environ.get('AWS_ACCESS_KEY_ID'),
                            'aws_secret_access_key': os.environ.get('AWS_SECRET_ACCESS_KEY'),
                        },
                    },
                    'Filter': {
                        'Partitions': {
                            'aws': {'Regions': {'include': ['us-east-1']}},
                        },
                    },
                },
            },
            {
                'RegionalAccounts': {
                    'RateLimit': {'max_count': 1, 'interval': 1, 'block': False},
                    'Account':  {
                        'SessionParameters': {
                            'aws_access_key_id': os.environ.get('AWS_ACCESS_KEY_ID'),
                            'aws_secret_access_key': os.environ.get('AWS_SECRET_ACCESS_KEY'),
                        },
                    },
                    'Filter': {
                        'Partitions': {
                            'aws': {'Regions': {'include': ['us-east-2']}},
                        },
                    },
                },
            },
        ]

    def test_account_factories(self):
        # non-cached
        ra0 = regional_accounts_factory(**self.args[0]['RegionalAccounts'])
        ra1 = regional_accounts_factory(**self.args[1]['RegionalAccounts'])
        ra_set = component.createObject(u"cs.aws_account.regional_account_set", ra0, ra1)
        self.assertTrue(IRegionalAccountSet.providedBy(ra_set))

        self.assertIsNot(
                component.createObject(u"cs.aws_account.regional_account_set_from_config",
                                       *self.args),
                component.createObject(u"cs.aws_account.regional_account_set_from_config",
                                       *self.args)
            )
