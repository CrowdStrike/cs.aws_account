from cachetools import cached, cachedmethod, TTLCache
from threading import local, RLock
from typing import Optional
import operator
from zope import interface
from zope.component.factory import Factory
from zope.interface.common.collections import IMutableMapping
from botocore.credentials import RefreshableCredentials
from botocore.session import get_session
from boto3.session import Session as botoSession
from .interfaces import ISession
from cs.aws_account.caching_key import aggregated_string_hash

import logging
logger = logging.getLogger(__name__)


# Region list as of 2022-06-01. Note: A more future proof solution would be
# to leverage boto3.get_available_regions, but we do this instead to prevent
# additional API calls.
AWS_REGIONS = set([
    'af-south-1', 'ap-east-1', 'ap-northeast-1', 'ap-northeast-2', 'ap-northeast-3',
    'ap-south-1', 'ap-southeast-1', 'ap-southeast-2', 'ap-southeast-3', 'ca-central-1',
    'eu-central-1', 'eu-north-1', 'eu-south-1', 'eu-west-1', 'eu-west-2', 'eu-west-3',
    'me-south-1', 'sa-east-1', 'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
    'us-gov-east-1', 'us-gov-west-1'
])
DEFAULT_AWS_REGION = 'us-west-2'


@interface.implementer(ISession)
class Session(object):
    """Thread safe boto3 Session accessor

    Provides convienent access to boto3.session.Session() objects even in
    complex threaded environments with IAM role assumption.

    Some method calls have memoizing TTL caches to improve performance of
    common action calls (such as logging session information).

    Kwargs:
        cache_ttl: Integer seconds time to live for cached method calls
        [boto3.session.Session]: See boto3.session.Session for other available kwargs
    """

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
            boto3 = []  # threadlocal stack

        # We can't use the ServiceEndpoints directly in boto3 session creation,
        # so we apply them to each client, depending on which service the
        # client is for, instead of adding them to the `_stack`.
        self._service_endpoints = SessionParameters.pop('ServiceEndpoints', {})

        # When setting `endpoint_url`, `region_name` is required, and can usually be
        # determined by the url itself, but for non-region-scoped endpoints, we must
        # supply the appropriate CS cloud-based region as a default or the AWS
        # API call will fail.
        self._default_aws_region = SessionParameters.get(
            'region_name', SessionParameters.pop('DefaultAWSRegion', DEFAULT_AWS_REGION))

        self._local = tl_boto3()  # threadlocal data to protect the non-TS low-level Boto3 session
        self._stack = [(aggregated_string_hash(SessionParameters), SessionParameters)]  # master stack
        self._rlock = RLock()
        self._cache_ttl = cache_ttl
        self._client_kwargs = {}
        self._credentials = {}
        if 'region_name' in SessionParameters:
            self._client_kwargs['region_name'] = SessionParameters['region_name']
        self._reset_caches()

    def _get_credentials(self, boto3_session, sts_method='assume_role', **kwargs):
        """Efficient Boto3 credentials getter

        Only one botocore.credentials.RefreshableCredentials object should
        be needed per assume-role based boto3 session objects.  To prevent
        un-needed api calls for threaded usage, we'll syncronize access to a
        object-level storage.

        Same args as _assume_role()
        """
        #botocore.credentials.RefreshableCredentials is seemingly thread-safe
        hash_ = boto3_session._aws_account_hash
        role_id = "".join([str(v) for v in kwargs.values()])
        with self._rlock:
            if hash_ not in self._credentials:
                self._credentials[hash_] = {}
            if sts_method not in self._credentials[hash_]:
                self._credentials[hash_][sts_method] = {}
            if role_id not in self._credentials[hash_][sts_method]:
                self._credentials[hash_][sts_method][role_id] = None

            if not self._credentials[hash_][sts_method][role_id]:

                def refresh():
                    logger.debug("Refreshing assumed role credentials for ARN {} with session name {}".format(kwargs.get('RoleArn', ''),
                                                                                                              kwargs.get('RoleSessionName', '')))
                    assume_role = getattr(boto3_session.client('sts', **self.client_kwargs(service='sts')), sts_method)
                    logger.debug('Attempting to assumed AWS Role with data {}'.format(kwargs))
                    credentials = assume_role(**kwargs)['Credentials']
                    logger.info('Assumed AWS Role with data {}'.format(kwargs))
                    #mapping keys common among all assume_role call variations
                    return dict(
                        access_key=credentials['AccessKeyId'],
                        secret_key=credentials['SecretAccessKey'],
                        token=credentials['SessionToken'],
                        expiry_time=credentials['Expiration'].isoformat())

                session_credentials = RefreshableCredentials.create_from_metadata(
                                        metadata=refresh(),
                                        refresh_using=refresh,
                                        method='sts-{}'.format(sts_method.replace('_', '-')))  # assume_role -> sts-assume-role
                self._credentials[hash_][sts_method][role_id] = session_credentials

            return self._credentials[hash_][sts_method][role_id]

    def _assume_role(self, boto3_session, sts_method='assume_role', **kwargs):
        """Stateless assume role call, returns Boto3 session with role assumption"""
        # https://programtalk.com/python-examples/botocore.credentials.RefreshableCredentials.create_from_metadata/
        s = get_session()
        s._credentials = self._get_credentials(boto3_session, sts_method, **kwargs)
        return botoSession(botocore_session=s)

    def boto3(self):
        """Return threadlocal active boto3.session.Session object"""
        #logger.debug("Preparing stack definition")
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
            #rebuild the stack so we can safely reference info in unlocked state.
            stack = [t for t in self._stack[len(self._local.boto3):]]

        #Do these tasks outside the lock to allow concurrent calls
        #to independently build the threadlocal boto3 object
        #logger.debug("Preparing threadlocal stack")
        for hash_, kwargs in stack:
            if not self._local.boto3:
                b3 = botoSession(**kwargs)
                b3._aws_account_hash = hash_  #mark the object with its hash
                self._local.boto3.append((hash_, b3,))
            else:
                b3 = self._assume_role(self._local.boto3[-1][1], **kwargs)
                b3._aws_account_hash = hash_  #mark the object with its hash
                self._local.boto3.append((hash_, b3,))
        b3 = self._local.boto3[-1][1]  #return lifo entry from threadlocal stack
        logger.debug("Returning Boto3.Session object with access key {}".format(b3.get_credentials().access_key))
        return b3

    def revert(self):
        """Set active boto3.session.Session object to previous, return pop'd threadlocal boto3.session.Session"""
        with self._rlock:
            if len(self._stack) > 1:
                s = self.boto3()
                self._stack.pop()
                self._reset_caches()
                logger.debug("Reverting role to {}".format(self._stack[-1]))
                return s

    def assume_role(self, sts_method='assume_role', deferred=False, **kwargs):
        """Set active boto3.session.Session object to role-assumed object"""
        with self._rlock:
            kwargs['sts_method'] = sts_method
            self._stack.append((aggregated_string_hash(kwargs), kwargs,))
            self._reset_caches()
        if not deferred:
            self.boto3()  #init, raises on error
        else:
            logger.info('Deffering assumtion of AWS Role with args {}'.format(kwargs))

    def client_kwargs(self, service: Optional[str] = None) -> IMutableMapping:
        """Return shallow copy of self._client_kwargs.

        Args:
            service (Optional[str]): If given, and a service endpoint override
                is configured for the specified AWS service (e.g., 'sqs', 'sts'),
                it will be added to the return client_kwargs dict.
        """
        client_kwargs = self._client_kwargs.copy()
        if service:
            endpoint_url = self._service_endpoints.get(service)
            if endpoint_url:
                client_kwargs['endpoint_url'] = endpoint_url
                # When specifying endpoint_url, boto3 requires a region to be given,
                # even for regionless services like iam, and we have to match the
                # region to the endpoint, so we determine that here, or for non-region-scoped
                # endpoints, provide a default.
                #
                # Yes, now that you mention it, this is unfortunate. :-P
                if not client_kwargs.get('region_name'):
                    parts = endpoint_url.split('.')
                    for part in parts:
                        if part in AWS_REGIONS:
                            client_kwargs['region_name'] = part
                    if not client_kwargs.get('region_name'):
                        client_kwargs['region_name'] = self._default_aws_region
        return client_kwargs

    @cachedmethod(operator.attrgetter('_cache_access_key'), lock=operator.attrgetter('_rlock'))
    def access_key(self):
        """Return access key related to session"""
        logger.debug("Refreshing access key cache")
        cr = self.boto3().get_credentials()  #returns None if not authenticated
        return cr.access_key if cr else None

    @cachedmethod(operator.attrgetter('_cache_account_id'), lock=operator.attrgetter('_rlock'))
    def account_id(self):
        """Return AWS account ID related to session"""
        logger.debug("Refreshing account id cache")
        return self.boto3().client('sts', **self.client_kwargs(service='sts')).get_caller_identity()['Account']

    @cachedmethod(operator.attrgetter('_cache_user_id'), lock=operator.attrgetter('_rlock'))
    def user_id(self):
        """Return AWS user ID related to session"""
        logger.debug("Refreshing user id cache")
        return self.boto3().client('sts', **self.client_kwargs(service='sts')).get_caller_identity()['UserId']

    @cachedmethod(operator.attrgetter('_cache_arn'), lock=operator.attrgetter('_rlock'))
    def arn(self):
        """Return the AWS Arn related to session (includes user name)"""
        #this call can be region dependent.  e.g. if calling aws from a govcloud
        #acct, this would fail because aws doesn't understand accounts in govcloud.
        logger.debug("Refreshing arn cache")
        return self.boto3().client('sts', **self.client_kwargs(service='sts')).get_caller_identity()['Arn']


SessionFactory = Factory(Session)


@interface.implementer(ISession)
@cached(cache={}, key=aggregated_string_hash, lock=RLock())
def session_factory(SessionParameters=None, AssumeRole=None, AssumeRoles=None):
    """Caching cs.aws_account.session.Session factory

    Common call signatures will return cached object.

    Create cs.aws_account.session.Session object.  If AssumeRole parameter is
    available, then process the role assumption.  if AssumeRoles parameter
    is available, then process the series of role assumptions

    Kwargs:
        SessionParameters: optional [see cs.aws_account.session.Session]
        AssumeRole: optional [see cs.aws_account.session.Session.assume_role]
        AssumeRoles: optional iterable of AssumeRole mappings

    Returns:
        cs.aws_account.session.Session object
    """
    SessionParameters = SessionParameters if SessionParameters else {}
    session = Session(**SessionParameters)
    if AssumeRole:
        session.assume_role(**AssumeRole)
    if AssumeRoles:
        for AssumeRole in AssumeRoles:
            session.assume_role(**AssumeRole)
    return session


CachingSessionFactory = Factory(session_factory)

