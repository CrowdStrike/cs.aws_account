from threading import RLock
from cachetools import cached
from zope.component.factory import Factory
from zope import interface
from .interfaces import IRegionalAccounts, IRegionalAccountSet
from .regional_accounts import regional_accounts_factory
from .caching_key import aggregated_string_hash


@interface.implementer(IRegionalAccountSet)
class RegionalAccountSet(object):
    """A container of cs.aws_account.regional_accounts.RegionalAccounts 
    instances that iterates over their content values 
    (cs.aws_account.regional_account.RegionalAccount objects)
    
    add(), disacard() and values() calls refer to RegionAccounts containers, 
    whilst __iter__() returns RegionAccount objects
    
    Args:
        arbtrary list of RegionalAccounts objects to instantiate the active set with
    """
    
    def __init__(self, *args):
        self._regional_accounts = set()
        self._lock = RLock()
        for ra in args:
            if not IRegionalAccounts.providedBy(ra):
                raise ValueError(ra)
            self._regional_accounts.add(ra)
    
    def add(self, regional_accounts):
        """Adds RegionalAccounts instance to include for iteration if not available"""
        if not IRegionalAccounts.providedBy(regional_accounts):
            raise ValueError(regional_accounts)
        with self._lock:
            self._regional_accounts.add(regional_accounts)
    def discard(self, regional_accounts):
        """Discards RegionalAccounts instance from iteration if available"""
        if not IRegionalAccounts.providedBy(regional_accounts):
            raise ValueError(regional_accounts)
        with self._lock:
            self._regional_accounts.discard(regional_accounts)
    def values(self):
        """frozenset of available RegionalAccounts providers"""
        with self._lock:
            return frozenset([ra for ra in self._regional_accounts])
    def __iter__(self):
        """Iterator of unique RegionalAccount instances from available RegionalAccounts instances"""
        l = []
        with self._lock:
            for ra in self._regional_accounts:
                l.extend([v for v in ra.values()])
            l = set(l)
        return iter(l)
RegionalAccountSetFactory = Factory(RegionalAccountSet)

@interface.implementer(IRegionalAccountSet)
def regional_account_set_factory(*args):
    """cs.aws_account.regional_account_set.RegionalAccountSet factory
    
    This accepts an arbritrary number of valid 
    cs.aws_account.regional_accounts.regional_accounts_factory kwargs dicts.
    the returned RegionalAccountSet will be instantiated with cached objects
    created with those specifications.
    
    Args:
        [see cs.aws_account.regional_accounts.regional_accounts_factory]
    
    Returns:
        cs.aws_account.regional_account_set.RegionalAccountSet object
    """
    ra_set = RegionalAccountSet()
    for RegionalAccounts in args:
        ra_set.add(regional_accounts_factory(**RegionalAccounts))
    return ra_set
RegionalAccountSetFactoryFromConfig = Factory(regional_account_set_factory)
