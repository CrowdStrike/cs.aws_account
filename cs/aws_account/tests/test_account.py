import os
import unittest

from zope import component

from ..testing import AWS_ACCOUNT_INTEGRATION_LAYER
from ..interfaces import IAccount
from ..account import Account, account_factory
from ..session import Session


class IntegrationTestAWSAccountAccount(unittest.TestCase):

    level = 2

    def setUp(self):
        self.session_kwargs = {'aws_access_key_id':     os.environ.get('AWS_ACCESS_KEY_ID'),
                               'aws_secret_access_key': os.environ.get('AWS_SECRET_ACCESS_KEY')}
        self.assume_role_kwargs = {'sts_method': 'assume_role',
                                   'RoleArn': os.environ.get('AWS_ASSUME_ROLE'),
                                   'RoleSessionName': 'testing_assume_role_for_cs_aws_account_package'
                                   }
        self.session = Session(**self.session_kwargs)

    def test_account_id(self):
        acct = Account(self.session)
        self.assertGreater(len(acct.account_id()), 0)

    def test_account_alias(self):
        acct = Account(self.session)
        self.assertGreater(len(acct.alias()), 0)

    def test_account_aliases(self):
        acct = Account(self.session)
        self.assertEqual(len(acct._cache_aliases), 0)
        self.assertGreater(len(acct.aliases()), 0)
        self.assertEqual(len(acct._cache_aliases), 1)

    def test_account_session(self):
        acct = Account(self.session)
        self.assertIs(acct.session(), self.session)

    def test_caching_factory(self):
        s1 = account_factory(SessionParameters=self.session_kwargs)
        s2 = account_factory(SessionParameters=self.session_kwargs)
        self.assertIs(s1, s2)


class IntegrationTestAWSAccountAccountZCA(unittest.TestCase):
    layer = AWS_ACCOUNT_INTEGRATION_LAYER

    def setUp(self):
        self.session_kwargs = {'aws_access_key_id':     os.environ.get('AWS_ACCESS_KEY_ID'),
                               'aws_secret_access_key': os.environ.get('AWS_SECRET_ACCESS_KEY')}

    def test_account_factories(self):
        s = component.createObject(u"cs.aws_account.session", SessionParameters=self.session_kwargs)
        a = component.createObject(u"cs.aws_account.account", s)
        self.assertTrue(IAccount.providedBy(a))
        a1 = component.createObject(u"cs.aws_account.cached_account", SessionParameters=self.session_kwargs)
        self.assertTrue(IAccount.providedBy(a1))
        a2 = component.createObject(u"cs.aws_account.cached_account", SessionParameters=self.session_kwargs)
        self.assertIs(a1, a2)
