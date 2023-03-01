"""Components for interacting with AWS accounts."""
# pylint: disable=invalid-name
from threading import RLock
import operator

from cachetools import cached, cachedmethod, TTLCache
from zope import interface
from zope.component.factory import Factory

from .caching_key import aggregated_string_hash
from .interfaces import IAccount
from .session import session_factory


@interface.implementer(IAccount)
class Account:
    """AWS account information.

    Args:
        session: cs.aws_account.Session instance

    Kwargs:
        cache_ttl: integer seconds time to live setting for cached method calls.
                   defaults to 3600
    """

    def __init__(self, session, cache_ttl=3600):
        """Initialize the Account with a Read Lock."""
        self._session = session
        self._cache_aliases = TTLCache(maxsize=1, ttl=cache_ttl)
        self._rlock = RLock()

    def account_id(self):
        """Return account identifier string."""
        return self._session.account_id()

    def alias(self):
        """Return the first available alias or else the account id."""
        aliases = self.aliases()
        return aliases[0] if aliases else self.account_id()

    @cachedmethod(operator.attrgetter('_cache_aliases'), lock=operator.attrgetter('_rlock'))
    def aliases(self):
        """Return list of all account aliases."""
        return self.session().boto3().client('iam', **self.session().client_kwargs(
            service='iam')).list_account_aliases()['AccountAliases']

    def session(self):
        """Return referenced cs.aws_account.Session object."""
        return self._session


AccountFactory = Factory(Account)


@interface.implementer(IAccount)
@cached(cache={}, key=aggregated_string_hash, lock=RLock())
def account_factory(SessionParameters=None, AssumeRole=None, AssumeRoles=None):
    """Create and cache a cs.aws_account.account.Account.

    Common call signatures will return cached object.

    Create cs.aws_account.account.Account object. If AssumeRole parameter is
    available, then process the role assumption. If AssumeRoles parameter
    is available, then process the series of role assumptions.

    Kwargs:
        SessionParameters: [see cs.aws_account.session.Session]
        AssumeRole: [see cs.aws_account.session.Session.assume_role]
        AssumeRoles: iterable of assume_role mappings

    Returns:
        cs.aws_account.account.Account object
    """
    session = session_factory(SessionParameters=SessionParameters,
                              AssumeRole=AssumeRole,
                              AssumeRoles=AssumeRoles)
    kwargs = {}
    if SessionParameters and 'cache_ttl' in SessionParameters:
        kwargs['cache_ttl'] = SessionParameters['cache_ttl']
    return Account(session=session, **kwargs)


CachingAccountFactory = Factory(account_factory)
