"""Provides an optimized thread-safe boto3 session wrapper."""
# pylint: disable=invalid-name
from collections.abc import Mapping
from threading import local, RLock
from typing import Optional
import logging
import operator

from boto3.session import Session as botoSession
from botocore.credentials import RefreshableCredentials
from botocore.session import get_session
from cachetools import cached, cachedmethod, Cache
from zope import interface
from zope.component.factory import Factory
from zope.interface.common.collections import IMutableMapping

from .caching_key import aggregated_string_hash
from .interfaces import ISession
from .retry import aws_throttling_retry

logger = logging.getLogger(__name__)


# Region list as of 2022-10-27. Note: A more future proof solution would be
# to leverage boto3.get_available_regions, but we do this instead to prevent
# additional API calls.
AWS_REGIONS = set([
    'af-south-1', 'ap-east-1', 'ap-northeast-1', 'ap-northeast-2', 'ap-northeast-3',
    'ap-south-1', 'ap-southeast-1', 'ap-southeast-2', 'ap-southeast-3', 'ca-central-1',
    'eu-central-1', 'eu-north-1', 'eu-south-1', 'eu-west-1', 'eu-west-2', 'eu-west-3',
    'me-south-1', 'sa-east-1', 'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
    'us-gov-east-1', 'us-gov-west-1'
])


@interface.implementer(ISession)
class Session:
    """Thread-safe boto3 Session accessor.

    Provides convenient access to boto3.session.Session() objects even in
    complex threaded environments with IAM role assumption.

    Some method calls have memoizing caches to improve performance of
    common action calls (such as logging session information).

    Kwargs:
        [boto3.session.Session]: See boto3.session.Session for available kwargs
    """

    # pylint: disable=too-many-instance-attributes, protected-access

    def _reset_caches(self):
        """Reset the memoizing decorator caches."""
        with self._rlock:
            self._cache_access_key = Cache(maxsize=1)
            self._cache_account_id = Cache(maxsize=1)
            self._cache_user_id = Cache(maxsize=1)
            self._cache_arn = Cache(maxsize=1)

    def __init__(self, **SessionParameters):
        """Set up the thread safety and threadlocal data."""

        class TLBoto3(local):  # pylint: disable=too-few-public-methods
            """Threadlocal boto3 client stack."""

            boto3 = []  # threadlocal stack

        # We can't use the ServiceEndpoints directly in boto3 session creation,
        # so we apply them to each client, depending on which service the
        # client is for, instead of adding them to the `_stack`.
        self._service_endpoints = SessionParameters.pop('ServiceEndpoints', {})

        self._local = TLBoto3()  # threadlocal data to protect the non-TS low-level Boto3 session
        self._stack = [(aggregated_string_hash(SessionParameters), SessionParameters)]  # master stack
        self._rlock = RLock()
        self._client_kwargs = {}
        self._credentials = {}
        if 'region_name' in SessionParameters:
            self._client_kwargs['region_name'] = SessionParameters['region_name']
        self._reset_caches()

    def _get_credentials(self, boto3_session, sts_method='assume_role', **kwargs):
        """Efficient Boto3 credentials getter.

        Only one botocore.credentials.RefreshableCredentials object should
        be needed per assume-role based boto3 session objects.  To prevent
        un-needed api calls for threaded usage, we'll syncronize access to an
        object-level storage.

        Same args as _assume_role().
        """
        # botocore.credentials.RefreshableCredentials is seemingly thread-safe
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
                    logger.debug(
                        "Refreshing assumed role credentials for ARN %s with session name %s",
                        kwargs.get('RoleArn', ''), kwargs.get('RoleSessionName', ''))
                    assume_role = getattr(boto3_session.client('sts', **self.client_kwargs(service='sts')), sts_method)
                    logger.debug("Attempting to assumed AWS Role with data %s", kwargs)
                    credentials = assume_role(**kwargs)['Credentials']
                    logger.info("Assumed AWS Role with data %s", kwargs)
                    # mapping keys common among all assume_role call variations
                    return {
                        'access_key': credentials['AccessKeyId'],
                        'secret_key': credentials['SecretAccessKey'],
                        'token': credentials['SessionToken'],
                        'expiry_time': credentials['Expiration'].isoformat(),
                    }

                session_credentials = RefreshableCredentials.create_from_metadata(
                    metadata=refresh(),
                    refresh_using=refresh,
                    method=f"sts-{sts_method.replace('_', '-')}")  # assume_role -> sts-assume-role
                self._credentials[hash_][sts_method][role_id] = session_credentials

            return self._credentials[hash_][sts_method][role_id]

    def _assume_role(self, boto3_session, sts_method='assume_role', **kwargs):
        """Stateless assume role call; returns Boto3 session with role assumption."""
        # https://programtalk.com/python-examples/botocore.credentials.RefreshableCredentials.create_from_metadata/
        session = get_session()
        session._credentials = self._get_credentials(boto3_session, sts_method, **kwargs)
        return botoSession(botocore_session=session)

    def boto3(self):
        """Return threadlocal active boto3.session.Session object."""
        with self._rlock:
            # make sure threadlocal boto3 stack entries are valid
            for i, _hash, _ in [(i, b3[0], b3[1],) for i, b3 in enumerate(self._local.boto3)]:
                try:
                    if _hash != self._stack[i][0]:
                        self._local.boto3 = self._local.boto3[:i]
                        break
                except IndexError:
                    self._local.boto3 = self._local.boto3[:i]
                    break

            # reduce threadlocal boto3 stack, if needed
            self._local.boto3 = self._local.boto3[:len(self._stack)]
            # rebuild the stack so we can safely reference info in unlocked state.
            stack = [t for t in self._stack[len(self._local.boto3):]]  # pylint: disable=unnecessary-comprehension

        # Do these tasks outside the lock to allow concurrent calls
        # to independently build the threadlocal boto3 object
        # logger.debug("Preparing threadlocal stack")
        for hash_, kwargs in stack:
            if not self._local.boto3:
                boto_session = botoSession(**kwargs)
                boto_session._aws_account_hash = hash_  # mark the object with its hash
                self._local.boto3.append((hash_, boto_session,))
            else:
                boto_session = self._assume_role(self._local.boto3[-1][1], **kwargs)
                boto_session._aws_account_hash = hash_  # mark the object with its hash
                self._local.boto3.append((hash_, boto_session,))
        boto_session = self._local.boto3[-1][1]  # return lifo entry from threadlocal stack
        logger.debug("Returning Boto3.Session object with access key %s", boto_session.get_credentials().access_key)
        return boto_session

    def revert(self):
        """Set active boto3.session.Session object to previous; return pop'd threadlocal boto3.session.Session."""
        with self._rlock:
            if len(self._stack) > 1:
                boto_session = self.boto3()
                self._stack.pop()
                self._reset_caches()
                logger.debug("Reverting role to %s", self._stack[-1])
                return boto_session
        return None

    def assume_role(self, sts_method='assume_role', deferred=False, **kwargs):
        """Set active boto3.session.Session object to role-assumed object."""
        with self._rlock:
            kwargs['sts_method'] = sts_method
            self._stack.append((aggregated_string_hash(kwargs), kwargs,))
            self._reset_caches()
        if not deferred:
            self.boto3()  # init, raises on error
        else:
            logger.info("Differing assumption of AWS Role with args %s", kwargs)

    def client_kwargs(self, service: Optional[str] = None) -> IMutableMapping:
        """Return shallow copy of self._client_kwargs.

        Args:
            service (Optional[str]): If given, and a service endpoint override
                is configured for the specified AWS service (e.g., 'sqs', 'sts'),
                it will be added to the return client_kwargs dict.
        """
        client_kwargs = self._client_kwargs.copy()
        kwarg_region = client_kwargs.get('region_name')
        if service and kwarg_region:
            endpoint_url = self._service_endpoints.get(service)

            # handle cross-region custom endpoints
            if isinstance(endpoint_url, Mapping):
                endpoint_url = endpoint_url.get(kwarg_region, None)

            # if we have a custom endpoint for this region
            if endpoint_url:
                endpoint_region = None
                endpoint_url_parts = endpoint_url.split('.')
                for part in endpoint_url_parts:
                    if part in AWS_REGIONS:
                        endpoint_region = part
                # Iff the custom endpoint region and operation match, use the endpoint for that region.
                # Otherwise, we have no choice but to fallback to the default endpoint, since boto3
                # requires a region if endpoint_url is also given.
                if endpoint_region and endpoint_region == kwarg_region:
                    client_kwargs['endpoint_url'] = endpoint_url
        return client_kwargs

    @cachedmethod(operator.attrgetter('_cache_access_key'), lock=operator.attrgetter('_rlock'))
    @aws_throttling_retry()
    def access_key(self):
        """Return access key related to session."""
        logger.debug("Refreshing access key cache")
        creds = self.boto3().get_credentials()  # returns None if not authenticated
        return creds.access_key if creds else None

    @cachedmethod(operator.attrgetter('_cache_account_id'), lock=operator.attrgetter('_rlock'))
    @aws_throttling_retry()
    def account_id(self):
        """Return AWS account ID related to session."""
        logger.debug("Refreshing account id cache")
        return self.boto3().client('sts', **self.client_kwargs(service='sts')).get_caller_identity()['Account']

    @cachedmethod(operator.attrgetter('_cache_user_id'), lock=operator.attrgetter('_rlock'))
    @aws_throttling_retry()
    def user_id(self):
        """Return AWS user ID related to session."""
        logger.debug("Refreshing user id cache")
        return self.boto3().client('sts', **self.client_kwargs(service='sts')).get_caller_identity()['UserId']

    @cachedmethod(operator.attrgetter('_cache_arn'), lock=operator.attrgetter('_rlock'))
    def arn(self):
        """Return the AWS Arn related to session (includes user name)."""
        # this call can be region dependent.  e.g. if calling aws from a govcloud
        # acct, this would fail because aws doesn't understand accounts in govcloud.
        logger.debug("Refreshing arn cache")
        return self.boto3().client('sts', **self.client_kwargs(service='sts')).get_caller_identity()['Arn']


SessionFactory = Factory(Session)


@interface.implementer(ISession)
@cached(cache={}, key=aggregated_string_hash, lock=RLock())
def session_factory(SessionParameters=None, AssumeRole=None, AssumeRoles=None):
    """Create and cache a cs.aws_account.session.Session.

    Common call signatures will return cached object.

    Create cs.aws_account.session.Session object. If AssumeRole parameter is
    available, then process the role assumption. If AssumeRoles parameter
    is available, then process the series of role assumptions.

    Kwargs:
        SessionParameters: optional [see cs.aws_account.session.Session]
        AssumeRole: optional [see cs.aws_account.session.Session.assume_role]
        AssumeRoles: optional iterable of assume_role mappings

    Returns:
        cs.aws_account.session.Session object
    """
    SessionParameters = SessionParameters if SessionParameters else {}
    session = Session(**SessionParameters)
    if AssumeRole:
        session.assume_role(**AssumeRole)
    if AssumeRoles:
        for Role in AssumeRoles:
            session.assume_role(**Role)
    return session


CachingSessionFactory = Factory(session_factory)
