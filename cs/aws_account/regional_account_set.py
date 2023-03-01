"""Components for interacting with RegionalAccountSets, which are containers for RegionalAccounts instances."""
from threading import RLock

from zope import interface
from zope.component.factory import Factory

from .interfaces import IRegionalAccounts, IRegionalAccountSet
from .regional_accounts import regional_accounts_factory


@interface.implementer(IRegionalAccountSet)
class RegionalAccountSet:
    """A container of cs.aws_account.regional_accounts.RegionalAccounts instances.

    The container iterates over its content values
    (cs.aws_account.regional_account.RegionalAccount objects).

    add(), discard() and values() calls refer to RegionAccounts containers,
    whilst __iter__() returns RegionAccount objects.

    Args:
        arbitrary list of RegionalAccounts objects to instantiate the active set with
    """

    # pylint: disable=no-value-for-parameter
    def __init__(self, *args):
        """Initialize the RegionalAccountSet."""
        self._regional_accounts = set()
        self._lock = RLock()
        for regional_account in args:
            if not IRegionalAccounts.providedBy(regional_account):
                raise ValueError(regional_account)
            self._regional_accounts.add(regional_account)

    def add(self, regional_accounts):
        """Add RegionalAccounts instance to include for iteration if not available."""
        if not IRegionalAccounts.providedBy(regional_accounts):
            raise ValueError(regional_accounts)
        with self._lock:
            self._regional_accounts.add(regional_accounts)

    def discard(self, regional_accounts):
        """Discard RegionalAccounts instance from iteration if available."""
        if not IRegionalAccounts.providedBy(regional_accounts):
            raise ValueError(regional_accounts)
        with self._lock:
            self._regional_accounts.discard(regional_accounts)

    def values(self):
        """Frozenset of available RegionalAccounts providers."""
        with self._lock:
            return frozenset(list(self._regional_accounts))

    def __iter__(self):
        """Iterate over unique RegionalAccount instances from available RegionalAccounts instances."""
        regional_accounts = []
        with self._lock:
            for regional_account in self._regional_accounts:
                regional_accounts.extend(list(regional_account.values()))
            regional_accounts = set(regional_accounts)
        return iter(regional_accounts)


RegionalAccountSetFactory = Factory(RegionalAccountSet)


@interface.implementer(IRegionalAccountSet)
def regional_account_set_factory(*args):
    """cs.aws_account.regional_account_set.RegionalAccountSet factory.

    This accepts an arbitrary number of valid
    cs.aws_account.regional_accounts.regional_accounts_factory kwargs dicts.
    the returned RegionalAccountSet will be instantiated with cached objects
    created with those specifications.

    Args:
        [see cs.aws_account.regional_accounts.regional_accounts_factory]

    Returns:
        cs.aws_account.regional_account_set.RegionalAccountSet object
    """
    ra_set = RegionalAccountSet()
    for regional_accounts in args:
        ra_set.add(regional_accounts_factory(**regional_accounts['RegionalAccounts']))
    return ra_set


RegionalAccountSetFactoryFromConfig = Factory(regional_account_set_factory)
