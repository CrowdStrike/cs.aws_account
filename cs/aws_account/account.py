"""Components for interacting with AWS accounts."""
# pylint: disable=invalid-name
from threading import RLock
import operator

from cachetools import cached, cachedmethod, Cache
from zope import interface
from zope.component.factory import Factory
from botocore.config import Config

from .caching_key import aggregated_string_hash
from .interfaces import IAccount
from .session import session_factory
from .retry import aws_throttling_retry


@interface.implementer(IAccount)
class Account:
    """AWS account information.

    Args:
        session: cs.aws_account.Session instance
    """

    aws_client_config = Config(retries={"max_attempts": 10})

    def __init__(self, session):
        """Initialize the Account with a Read Lock."""
        self._session = session
        self._cache_aliases = Cache(maxsize=1)
        self._rlock = RLock()

    def account_id(self):
        """Return account identifier string."""
        return self._session.account_id()

    def alias(self):
        """Return the first available alias or else the account id."""
        aliases = self.aliases()
        return aliases[0] if aliases else self.account_id()

    @cachedmethod(operator.attrgetter('_cache_aliases'), lock=operator.attrgetter('_rlock'))
    @aws_throttling_retry()
    def aliases(self):
        """Return list of all account aliases."""
        client_kwargs = self.session().client_kwargs(service='iam')
        client_kwargs['config'] = Account.aws_client_config
        return self.session().boto3().client('iam', **client_kwargs).list_account_aliases()['AccountAliases']

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
    return Account(session=session)


CachingAccountFactory = Factory(account_factory)
