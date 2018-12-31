import unittest
import os
import threading
import time
from zope import component
from zope.interface.verify import verifyObject
from ..testing import AWS_ACCOUNT_INTEGRATION_LAYER
from cs.aws_account.components import Session
from cs.aws_account.b3 import IBoto3Session
from ..interfaces import ISession

class IntegrationTestAWSAccountSession(unittest.TestCase):
    
    level = 2
    
    def setUp(self):
        self.session_kwargs = {'aws_access_key_id':     os.environ.get('AWS_ACCESS_KEY_ID'),
                               'aws_secret_access_key': os.environ.get('AWS_SECRET_ACCESS_KEY')}
        self.assume_role_kwargs = {'sts_method': 'assume_role',
                                   'RoleArn': os.environ.get('AWS_ASSUME_ROLE'),
                                   'RoleSessionName': 'testing_assume_role_for_cs_aws_account_package'
                                   }
    
    def test_simple_boto3(self):
        s = Session(**self.session_kwargs)
        self.assertTrue(ISession.providedBy(s))
        verifyObject(ISession, s)
        
        b3 = s.boto3()
        self.assertTrue(IBoto3Session.providedBy(b3))
        self.assertIs(b3, s.boto3())
    
    def test_access_key(self):
        s = Session(**self.session_kwargs)
        self.assertEqual(self.session_kwargs['aws_access_key_id'],
                         s.access_key())
    
    def test_caches(self):
        s = Session(**self.session_kwargs)
        def get_cache_lengths():
            return (len(s._cache_access_key), len(s._cache_account_id),
                                    len(s._cache_user_id),len(s._cache_arn),)
        self.assertEqual((0,0,0,0), get_cache_lengths())
        s.access_key(); s.account_id(); s.user_id(), s.arn()
        self.assertEqual((1,1,1,1), get_cache_lengths())
        s.access_key(); s.account_id(); s.user_id(), s.arn()
        self.assertEqual((1,1,1,1), get_cache_lengths())
    
    def test_cache_ttl(self):
        s = Session(cache_ttl=1, **self.session_kwargs)
        def get_cache_lengths():
            return (len(s._cache_access_key), len(s._cache_account_id),
                                    len(s._cache_user_id),len(s._cache_arn),)
        self.assertEqual((0,0,0,0), get_cache_lengths())
        s.access_key(); s.account_id(); s.user_id(), s.arn()
        self.assertEqual((1,1,1,1), get_cache_lengths())
        time.sleep(1)
        self.assertEqual((0,0,0,0), get_cache_lengths())
        s.access_key(); s.account_id(); s.user_id(), s.arn()
        self.assertEqual((1,1,1,1), get_cache_lengths())
        
    
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
        t1.start(); t2.start()
        t1.join(); t2.join()
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
        
    def test_threadlocal_assume_role(self):
        s = Session(**self.session_kwargs)
        ak1 = s.access_key()
        t1 = threading.Thread(target=s.assume_role, kwargs=self.assume_role_kwargs)
        t1.start(); t1.join()
        self.assertNotEqual(ak1, s.access_key())
        
    def test_threadlocal_revert(self):
        s = Session(**self.session_kwargs)
        ak1 = s.access_key()
        s.assume_role(**self.assume_role_kwargs)
        ak2 = s.access_key()
        t1 = threading.Thread(target=s.revert)
        t1.start(); t1.join()
        self.assertEqual(ak1, s.access_key())
        self.assertNotEqual(ak2, s.access_key())
        
    

class IntegrationTestAWSAccountSessionZCA(unittest.TestCase):
    
    layer = AWS_ACCOUNT_INTEGRATION_LAYER
    
    def setUp(self):
        self.session_kwargs = {'aws_access_key_id':     os.environ.get('AWS_ACCESS_KEY_ID'),
                               'aws_secret_access_key': os.environ.get('AWS_SECRET_ACCESS_KEY')}
    
    def test_session_factory(self):
        s = component.createObject(u"cs.aws_account.session", **self.session_kwargs)
        self.assertTrue(ISession.providedBy(s))
        