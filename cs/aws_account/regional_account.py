import operator
from threading import RLock
import types
from cachetools import cached
from zope.component.factory import Factory
from zope import interface
from zope.schema.fieldproperty import FieldProperty
from cs.ratelimit import ratelimitedmethod, ratelimitproperties_factory
from .account import account_factory
from .interfaces import IRegionalAccount
from cs.aws_account.caching_key import aggregated_string_hash
from botocore.config import Config
from .exceptions import AWSClientException

import logging
logger = logging.getLogger(__name__)

@interface.implementer(IRegionalAccount)
class RegionalAccount(object):
    """A boto3 session client caller with rate limiting capabilities

    Args:
        ratelimit: cs.ratelimit.RateLimitProperties instance that is referenced
                   at call time to determine rate limiting actions to call_client()
                   and the paginator returned by get_paginator()
        account: cs.aws_account.Account leveraged for all boto3 calls
        region_name: Valid string region_name for all boto3 calls
    """

    """cs.ratelimit.RateLimitProperties instance"""
    ratelimit = FieldProperty(IRegionalAccount['ratelimit'])

    def __init__(self, ratelimit, account, region_name=None):
        self.ratelimit = ratelimit
        self._account = account
        self._region_name = region_name

    def region(self):
        """Return referenced boto3 region_name string"""
        return self._region_name

    def account(self):
        """Return referenced cs.aws_account.Account instance"""
        return self._account

    def _get_client(self, service, **kwargs):
        kwargs['service_name'] = service
        kwargs['region_name'] = self.region()
        kwargs.update(self.account().session().client_kwargs(service=service))
        kwargs['config'] = Config(retries=dict(max_attempts=10))
        return self.account().session().boto3().client(**kwargs)

    @ratelimitedmethod(operator.attrgetter('ratelimit'))
    def _limited(self, callback, **kwargs):
        debug_msg = "calling AWS method {} for account {} ({}) region {} with user arn {}".\
                        format(
                            callback,
                            self._account.account_id(),
                            self._account.alias(),
                            self._region_name,
                            self._account.session().arn()
                            )
        logger.debug(debug_msg)
        try:
            return callback(**kwargs)
        except Exception as e:
            raise AWSClientException(e,AccountAlias=self._account.alias(),Region=self._region_name,AccountId=self._account.account_id())

    def call_client(self, service, method, client_kwargs=None, **kwargs):
        """Return call to boto3 service client method limited by properties in ratelimit

        This can raise cs.ratelimit.RateLimitExceeded based on ratelimit settings

        Raises:
            [dependent on named boto3 service method]

        Args:
            service: valid boto3 service name string
            method: valid boto3 named service method name string
            client_kwargs: mapping of kwargs that will be used to create the
                boto3.client object.

        Kwargs:
            [dependent on named boto3 service method]

        Returns:
            [dependent on named boto3 service method]
        """
        client_kwargs = {} if not client_kwargs else client_kwargs
        client = self._get_client(service, **client_kwargs)
        return self._limited(getattr(client, method), **kwargs)

    def get_paginator(self, service, method, client_kwargs=None):
        """Return paginator for boto3 service client method limited by properties in ratelimit

        same call features as call_client() except calls are accessed via
        a returned paginator
        """
        client_kwargs = {} if not client_kwargs else client_kwargs
        _limited = self._limited
        def paginate(self, **kwargs):
            page_iterator = self.__wrapped__(**kwargs) #get the default paginator from boto3
            _orig_method = page_iterator._method
            def _method(self, **kwargs):
                return _limited(_orig_method, **kwargs)
            page_iterator._method = types.MethodType(_method, page_iterator) #over-ride with rate-limited method.
            return page_iterator

        client = self._get_client(service, **client_kwargs)
        paginator = client.get_paginator(method)
        paginator.__wrapped__ = paginator.paginate #we're gonna replace this
        paginator.paginate = types.MethodType(paginate, paginator)
        return paginator
RegionalAccountFactory = Factory(RegionalAccount)

@interface.implementer(IRegionalAccount)
@cached(cache={}, key=aggregated_string_hash, lock=RLock())
def regional_account_factory(RateLimit=None, Account=None, region_name=None):
    """Caching cs.aws_account.regional_account.RegionalAccount factory

    Common call signatures will return cached object.

    Create cs.aws_account.regional_account.RegionalAccount with defined
    rate limits for Account/region_name combination.

    Kwargs:
        RateLimit: [see cs.ratelimit.components.ratelimitproperties_factory]
        Account: [see cs.aws_account.account.account_factory]
        region_name: valid AWS region name string (i.e. us-east-1, us-east-2, etc)

    Returns:
        cs.aws_account.regional_account.RegionalAccount object
    """
    RateLimit = RateLimit if RateLimit else {}
    rl = ratelimitproperties_factory(**RateLimit)
    acct = account_factory(**Account)
    return RegionalAccount(rl, acct, region_name=region_name)
CachingRegionalAccountFactory = Factory(regional_account_factory)

