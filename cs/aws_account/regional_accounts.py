from threading import RLock
from cachetools import cached
from zope.component.factory import Factory
from zope import interface
from zope.schema.fieldproperty import FieldProperty
from .interfaces import IRegionalAccounts
from .caching_key import aggregated_string_hash
from .account import account_factory
from .regional_account import regional_account_factory
            

@interface.implementer(IRegionalAccounts)
class RegionalAccounts(object):
    """Enumerable read-only mapping whose keys are AWS region strings and values are 
    related cs.aws_account.regional_account.RegionalAccount instances
    
    This implementation leverages the caching factory for the RegionalAccount
    value population.  This means that 2 seperate RegionalAccounts objects will
    point to the same value reference for common factory call signatures.
    
    See README.md for usage
    
    Dict Filter Spec:
        Partitions:
         aws: # valid AWS partition name.  If absent, defaults to all available partitions
          IncludeNonRegional: True|False # include non-regional endpoint names
          Regions: #if absent, defaults to all available regions
           include: [list, of, regions] #if absent, defaults to all available regions
           exclude: [list, of, regions] #takes precedence over include
    
    Args:
        RateLimit: [see cs.ratelimit.components.ratelimitproperties_factory]
        Account: [see cs.aws_account.account.account_factory]
    
    Kwargs:
        Filter: Dict filter spec (see above)
        RateLimitRegionSpec: dict where keys are region names and values are
         cs.ratelimit.components.ratelimitproperties_factory factory specs
        service: boto3.session.Session.Client() service used as reference to 
                 build region name lists.
    """
    
    filter = FieldProperty(IRegionalAccounts['filter'])
    
    def __init__(self, RateLimit, Account, Filter=None, RateLimitRegionSpec=None, service='ec2'):
        self.filter = Filter if Filter else {}
        
        self._RateLimit = RateLimit
        self._Account = Account
        self._account = account_factory(**Account)
        self._service = service
        self._RateLimitRegionSpec = RateLimitRegionSpec if RateLimitRegionSpec else {}
        
        self._rlock = RLock()
        self._regional_accounts = {}
        
    def _get_regional_account(self, region_name):
        with self._rlock:
            try:
                return self._regional_accounts[region_name]
            except KeyError:
                self._regional_accounts[region_name] = \
                    regional_account_factory(
                        self._RateLimitRegionSpec[region_name] if region_name \
                            in self._RateLimitRegionSpec else \
                                                    self._RateLimit, self._Account, region_name)
            return self._regional_accounts[region_name]
    
    def account(self):
        return self._account
    
    def __getitem__(self, key):
        if not key in self:
            raise KeyError(key)
        return self._get_regional_account(key)
    
    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key):
        return key in self.__iter__()
    
    def keys(self):
        return (k for k in self)

    def __iter__(self):
        partitions = \
            self.filter.get('Partitions', {k:None for k in \
                    self.account().session().boto3().get_available_partitions()})
        
        regions = set()
        for name in set(partitions):
            p_config = partitions[name]
            if not p_config:
                p_config = {}
            include_non_regional = p_config.get('IncludeNonRegional', True)
            all_regions = self.account().session().boto3().get_available_regions(
                                self._service, 
                                partition_name=name, 
                                allow_non_regional=include_non_regional)
            
            region_include = set(p_config.get('Regions', {}).get('include', {}))
            if not region_include:
                region_include = set(all_regions)
            region_exclude = set(p_config.get('Regions', {}).get('exclude', {}))
            regions.update(region_include - region_exclude)
        
        for region in regions:
            yield region

    def values(self):
        return tuple([self[k] for k in self])

    def items(self):
        return tuple([(k, self[k]) for k in self])

    def __len__(self):
        l = [k for k in self]
        return len(l)
RegionalAccountsFactory = Factory(RegionalAccounts)

@interface.implementer(IRegionalAccounts)
@cached(cache={}, key=aggregated_string_hash, lock=RLock())
def regional_accounts_factory(**kwargs):
    """Caching cs.aws_account.regional_accounts.RegionalAccounts factory
    
    Common call signatures will return cached object.
    
    Create cs.aws_account.regional_accounts.RegionalAccounts with defined
    rate limits for Account and optional region filter.
    
    Kwargs:
        RateLimit: optional [see cs.ratelimit.components.ratelimitproperties_factory]
        Account: required [see cs.aws_account.account.account_factory]
        Filter: optional valid dict filter specification
        RateLimitRegionSpec: optional per-region rate limit specs
        service: optional boto3 client service reference to build region specs from
    
    Returns:
        cs.aws_account.regional_accounts.RegionalAccounts object
    """
    return RegionalAccounts(**kwargs)
CachingRegionalAccountsFactory = Factory(regional_accounts_factory)


