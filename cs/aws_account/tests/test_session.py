import os
import threading
import time
import unittest

from zope import component
from zope.interface.verify import verifyObject

from ..interfaces import ISession
from ..testing import AWS_ACCOUNT_INTEGRATION_LAYER
from cs.aws_account.b3 import IBoto3Session
from cs.aws_account.session import Session, session_factory


class IntegrationTestAWSAccountSession(unittest.TestCase):

    level = 2

    def setUp(self):
        self.session_kwargs = {
            'aws_access_key_id':     os.environ.get('AWS_ACCESS_KEY_ID'),
            'aws_secret_access_key': os.environ.get('AWS_SECRET_ACCESS_KEY'),
        }
        self.assume_role_kwargs = {
            'sts_method': 'assume_role',
            'RoleArn': os.environ.get('AWS_ASSUME_ROLE'),
            'RoleSessionName': 'testing_assume_role_for_cs_aws_account_package',
        }

    def test_simple_boto3(self):
        s = Session(**self.session_kwargs)
        self.assertTrue(ISession.providedBy(s))
        verifyObject(ISession, s)

        b3 = s.boto3()
        self.assertTrue(IBoto3Session.providedBy(b3))
        self.assertIs(b3, s.boto3())

    def test_get_credentials(self):
        lock = threading.Lock()
        b3_sessions = []
        s = Session(**self.session_kwargs)
        s.assume_role(**self.assume_role_kwargs)

        def add_session(s, b3_sessions):
            with lock:
                b3_sessions.append(s.boto3())

        t1 = threading.Thread(target=add_session, args=[s, b3_sessions])
        t2 = threading.Thread(target=add_session, args=[s, b3_sessions])
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        b3_sessions.append(s.boto3())
        self.assertIs(b3_sessions[0]._session._credentials,
                      b3_sessions[1]._session._credentials)
        self.assertIs(b3_sessions[1]._session._credentials,
                      b3_sessions[2]._session._credentials)

    def test_access_key(self):
        s = Session(**self.session_kwargs)
        self.assertEqual(self.session_kwargs['aws_access_key_id'],
                         s.access_key())

    def test_caches(self):
        s = Session(**self.session_kwargs)

        def get_cache_lengths():
            return (
                len(s._cache_access_key),
                len(s._cache_account_id),
                len(s._cache_user_id),
                len(s._cache_arn),
            )

        self.assertEqual((0, 0, 0, 0), get_cache_lengths())
        s.access_key()
        s.account_id()
        s.user_id()
        s.arn()
        self.assertEqual((1, 1, 1, 1), get_cache_lengths())

        s.access_key()
        s.account_id()
        s.user_id()
        s.arn()
        self.assertEqual((1, 1, 1, 1), get_cache_lengths())

    def test_cache_ttl(self):
        s = Session(cache_ttl=1, **self.session_kwargs)

        def get_cache_lengths():
            return (
                len(s._cache_access_key),
                len(s._cache_account_id),
                len(s._cache_user_id),
                len(s._cache_arn),
            )

        self.assertEqual((0, 0, 0, 0), get_cache_lengths())

        s.access_key()
        s.account_id()
        s.user_id()
        s.arn()
        self.assertEqual((1, 1, 1, 1), get_cache_lengths())

        time.sleep(1)
        self.assertEqual((0, 0, 0, 0), get_cache_lengths())

        s.access_key()
        s.account_id()
        s.user_id()
        s.arn()
        self.assertEqual((1, 1, 1, 1), get_cache_lengths())

    def test_threadlocal_boto3(self):
        s = Session(**self.session_kwargs)
        lock = threading.Lock()
        d = []
        errors = []

        def tl_session():
            try:
                with lock:
                    d.append(s.boto3())
            except Exception as e:
                errors.append(e)
                return

        t1 = threading.Thread(target=tl_session)
        t2 = threading.Thread(target=tl_session)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        self.assertEqual(errors, [])
        self.assertIsNot(d[0], d[1])
        self.assertEqual(d[0].get_credentials().access_key,
                         d[1].get_credentials().access_key)

    def test_assume_role_and_revert(self):
        s = Session(**self.session_kwargs)
        ak1 = s.access_key()
        s.assume_role(**self.assume_role_kwargs)
        self.assertNotEqual(ak1, s.access_key())
        s.revert()
        self.assertEqual(ak1, s.access_key())
        s.revert()
        self.assertEqual(ak1, s.access_key())

        s.assume_role(**self.assume_role_kwargs)
        s1 = s.boto3()
        s.revert()
        s.assume_role(**self.assume_role_kwargs)
        s2 = s.boto3()
        s.revert()
        s1.client('sts').get_caller_identity()['UserId']
        s2.client('sts').get_caller_identity()['UserId']

    def test_assume_role_deferrence(self):
        s = Session(**self.session_kwargs)
        ak1 = s.access_key()
        s.assume_role(deferred=True, **self.assume_role_kwargs)
        self.assertNotEqual(ak1, s.access_key())
        s.revert()
        self.assertEqual(ak1, s.access_key())
        s.revert()
        self.assertEqual(ak1, s.access_key())

        s.assume_role(deferred=True, **self.assume_role_kwargs)
        s1 = s.boto3()
        s.revert()
        s.assume_role(deferred=True, **self.assume_role_kwargs)
        s2 = s.boto3()
        s.revert()
        s1.client('sts').get_caller_identity()['UserId']
        s2.client('sts').get_caller_identity()['UserId']

    def test_threadlocal_assume_role(self):
        s = Session(**self.session_kwargs)
        ak1 = s.access_key()
        t1 = threading.Thread(target=s.assume_role, kwargs=self.assume_role_kwargs)
        t1.start()
        t1.join()
        self.assertNotEqual(ak1, s.access_key())

    def test_threadlocal_revert(self):
        s = Session(**self.session_kwargs)
        ak1 = s.access_key()
        s.assume_role(**self.assume_role_kwargs)
        ak2 = s.access_key()
        t1 = threading.Thread(target=s.revert)
        t1.start()
        t1.join()
        self.assertEqual(ak1, s.access_key())
        self.assertNotEqual(ak2, s.access_key())

    def test_caching_session_factory(self):
        s1 = session_factory(SessionParameters=self.session_kwargs)
        s2 = session_factory(SessionParameters=self.session_kwargs)
        self.assertIs(s1, s2)

        s1 = session_factory(SessionParameters=self.session_kwargs,
                             AssumeRole=self.assume_role_kwargs)
        s2 = session_factory(SessionParameters=self.session_kwargs,
                             AssumeRole=self.assume_role_kwargs)
        self.assertIs(s1, s2)

        assume_role_kwargs = self.assume_role_kwargs.copy()
        assume_role_kwargs['RoleSessionName'] = 'testing_assume_role_for_cs_aws_account_package_caching_test'
        s2 = session_factory(SessionParameters=self.session_kwargs,
                             AssumeRole=assume_role_kwargs)
        self.assertIsNot(s1, s2)


class IntegrationTestAWSAccountSessionZCA(unittest.TestCase):

    layer = AWS_ACCOUNT_INTEGRATION_LAYER

    def setUp(self):
        self.session_kwargs = {'aws_access_key_id':     os.environ.get('AWS_ACCESS_KEY_ID'),
                               'aws_secret_access_key': os.environ.get('AWS_SECRET_ACCESS_KEY')}

    def test_session_factories(self):
        s = component.createObject(u"cs.aws_account.session", SessionParameters=self.session_kwargs)
        self.assertTrue(ISession.providedBy(s))
        s = component.createObject(u"cs.aws_account.cached_session", SessionParameters=self.session_kwargs)
        self.assertTrue(ISession.providedBy(s))

        s = component.createObject(u"cs.aws_account.cached_session")
        self.assertTrue(ISession.providedBy(s))


class TestSessionClientKwargs(unittest.TestCase):
    def setUp(self):
        self.session_kwargs = {
            'region_name': 'us-west-1',
            'ServiceEndpoints': {
                'sts': 'https://test.sts.us-west-1.com/test',
                'sqs': {
                    'us-west-1': 'https://test.sqs.us-west-1.com/test',
                    'eu-central-1': 'https://test.sqs.eu-central-1.com/test',
                }
            }
        }

    def test_with_service_and_session_region_matches_endpoint_region(self):
        s = Session(**self.session_kwargs)
        self.assertDictEqual(
            s.client_kwargs(service='sts'),
            {'region_name': 'us-west-1', 'endpoint_url': 'https://test.sts.us-west-1.com/test'}
        )

    def test_cross_region_service_endpoint(self):
        s = Session(**self.session_kwargs)
        self.assertDictEqual(
            s.client_kwargs(service='sqs'),
            {'region_name': 'us-west-1', 'endpoint_url': 'https://test.sqs.us-west-1.com/test'}
        )

    def test_no_endpoint_url_added_without_service(self):
        s = Session(**self.session_kwargs)
        self.assertDictEqual(s.client_kwargs(), {'region_name': 'us-west-1'})

    def test_no_endpoint_url_added_with_service_not_in_endpoints_map(self):
        s = Session(**self.session_kwargs)
        self.assertDictEqual(s.client_kwargs(service='invalid'), {'region_name': 'us-west-1'})

    def test_no_endpoint_url_added_with_service_not_in_cross_region_endpoints_map(self):
        self.session_kwargs['region_name'] = 'us-west-2'
        s = Session(**self.session_kwargs)
        self.assertDictEqual(s.client_kwargs(service='sqs'), {'region_name': 'us-west-2'})

    def test_no_endpoint_url_added_for_session_region_mismatch(self):
        self.session_kwargs['ServiceEndpoints']['sts'] = 'https://sts.ap-east-1.com'
        s = Session(**self.session_kwargs)
        self.assertDictEqual(s.client_kwargs(service='sts'), {'region_name': 'us-west-1'})

    def test_no_endpoint_added_without_session_region(self):
        self.session_kwargs.pop('region_name')
        s = Session(**self.session_kwargs)
        self.assertDictEqual(s.client_kwargs(service='sts'), {})
