from cachetools import cached, cachedmethod, TTLCache
from threading import local, RLock
import operator
from zope.component.factory import Factory
from zope import interface
from botocore.credentials import RefreshableCredentials
from botocore.session import get_session
from boto3.session import Session as botoSession
from .interfaces import ISession

import logging
logger = logging.getLogger(__name__)

@interface.implementer(ISession)
class Session(object):
    """Thread safe boto3 Session accessor
    
    Provides convienent access to boto3.session.Session() objects even in
    complex threaded environments with IAM role assumption.
    
    Some method calls have memoizing TTL caches to improve performance of
    common action calls (such as logging session information). 
    """
    
    @staticmethod
    def _mapping_hash(mapping):
        """Return a hash based on the key/values of a mapping"""
        _id = ''
        for k, v in mapping.items():
            _id += "{}{}".format(k, v)
        return hash(_id)
    
    def _reset_caches(self):
        """Reset the memoizing decorator caches"""
        with self._rlock:
            self._cache_access_key = TTLCache(maxsize=1, ttl=self._cache_ttl)
            self._cache_account_id = TTLCache(maxsize=1, ttl=self._cache_ttl)
            self._cache_user_id = TTLCache(maxsize=1, ttl=self._cache_ttl)
            self._cache_arn = TTLCache(maxsize=1, ttl=self._cache_ttl)
        
    
    def __init__(self, cache_ttl=3600, **SessionParameters):
        """Setup the thread safety and threadlocal data"""
        class tl_boto3(local):
            boto3 = [] #threadlocal stack
        self._local = tl_boto3() #threadlocal data to protect the non-TS low-level Boto3 session
        self._stack = [(Session._mapping_hash(SessionParameters), SessionParameters)] #master stack
        self._rlock = RLock()
        self._cache_ttl = cache_ttl
        self._reset_caches()
    
    def _assume_role(self, boto3_session, sts_method='assume_role', **kwargs):
        """Stateless assume role call, returns Boto3 session with role assumption"""
        # https://programtalk.com/python-examples/botocore.credentials.RefreshableCredentials.create_from_metadata/
        assume_role = getattr(boto3_session.client('sts'), sts_method)
        def refresh():
            credentials = assume_role(**kwargs)['Credentials']
            #mapping keys common among all assume_role call variations
            return dict(
                access_key=credentials['AccessKeyId'],
                secret_key=credentials['SecretAccessKey'],
                token=credentials['SessionToken'],
                expiry_time=credentials['Expiration'].isoformat())
        
        session_credentials = RefreshableCredentials.create_from_metadata(
                                metadata=refresh(),
                                refresh_using=refresh,
                                method='sts-{}'.format(sts_method.replace('_','-'))) # assume_role -> sts-assume-role
        s = get_session()
        s._credentials = session_credentials
        return botoSession(botocore_session=s)
    
    def boto3(self):
        """Return threadlocal active boto3.session.Session object"""
        with self._rlock:
            #make sure threadlocal boto3 stack entries are valid
            for i, _hash, _b3 in [(i, b3[0], b3[1],) for i, b3 in enumerate(self._local.boto3)]:
                try:
                    if _hash != self._stack[i][0]:
                        self._local.boto3 = self._local.boto3[:i]
                        break
                except IndexError:
                    self._local.boto3 = self._local.boto3[:i]
                    break
            
            #reduce threadlocal boto3 stack, if needed
            self._local.boto3 = self._local.boto3[:len(self._stack)]
            
            #build the needed threadlocal boto3 stack reference
            for hash_, kwargs in self._stack[len(self._local.boto3):]:
                if not self._local.boto3:
                    self._local.boto3.append(
                                (hash_, botoSession(**kwargs), )
                                             )
                else:
                    self._local.boto3.append(
                                (hash_, self._assume_role(
                                                self._local.boto3[-1][1], **kwargs))
                                             )
            
            return self._local.boto3[-1][1] #return lifo entry from threadlocal stack
        
    
    def revert(self):
        """Set active boto3.session.Session object to previous, return pop'd Session"""
        with self._rlock:
            if len(self._stack) > 1:
                s = self.boto3()
                self._stack.pop()
                self._reset_caches()
                return s
    
    def assume_role(self, sts_method='assume_role', **kwargs):
        """Set active boto3.session.Session object to role-assumed object"""
        with self._rlock:
            kwargs['sts_method'] = sts_method
            self._stack.append((Session._mapping_hash(kwargs), kwargs,))
            self._reset_caches()
        self.boto3() #init, raises on error
        logger.info('Assumed AWS Role with ARN {}'.format(self.arn))
    
    @cachedmethod(operator.attrgetter('_cache_access_key'), lock=operator.attrgetter('_rlock'))
    def access_key(self):
        """Return access key related to session"""
        cr = self.boto3().get_credentials() #returns None if not authenticated
        return cr.access_key if cr else None

    @cachedmethod(operator.attrgetter('_cache_account_id'), lock=operator.attrgetter('_rlock'))
    def account_id(self):
        """Return AWS account ID related to session"""
        return self.boto3().client('sts').get_caller_identity()['Account']
    
    @cachedmethod(operator.attrgetter('_cache_user_id'), lock=operator.attrgetter('_rlock'))
    def user_id(self):
        """Return AWS user ID related to session"""
        return self.boto3().client('sts').get_caller_identity()['UserId']
    
    @cachedmethod(operator.attrgetter('_cache_arn'), lock=operator.attrgetter('_rlock'))
    def arn(self):
        """Return the AWS Arn related to session (includes user name)"""
        #this call can be region dependent.  e.g. if calling aws from a govcloud
        #acct, this would fail because aws doesn't understand accounts in govcloud.
        return self.boto3().client('sts', region_name=self.boto3().region_name).get_caller_identity()['Arn']
SessionFactory = Factory(Session)

@interface.implementer(ISession)
@cached(cache={}, lock=RLock())
def session_factory(*args, **kwargs):
    return Session(*args, **kwargs)
CachingSessionFactory = Factory(session_factory)

class Account(object):
    
    _default_region = 'us-west-1'
    
    _service_region_map = {}
    
    def __init__(self, default_region=None,
                        service_region_map=None):
        if default_region:
            self._default_region = default_region
        if service_region_map:
            self._service_region_map = service_region_map
        