"""Components for interacting with Regional Accounts, which are containers for RegionalAccount instances."""
from threading import RLock

from cachetools import cached, TTLCache
from zope import interface
from zope.component.factory import Factory
from zope.schema.fieldproperty import FieldProperty

from .account import account_factory
from .caching_key import aggregated_string_hash
from .interfaces import IRegionalAccounts
from .regional_account import regional_account_factory


@interface.implementer(IRegionalAccounts)
class RegionalAccounts:
    """Enumerable read-only mapping of RegionalAccount instances.

    Keys are AWS region strings and values are related
    cs.aws_account.regional_account.RegionalAccount instances.

    This implementation leverages the caching factory for the RegionalAccount
    value population.  This means that 2 separate RegionalAccounts objects will
    point to the same value reference for common factory call signatures.

    See README.md for usage.

    Dict Filter Spec:
        Partitions:
         aws: # valid AWS partition name.  If absent, defaults 'aws'
           IncludeNonRegional: True|False # include non-regional endpoint names, defaults to False
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

    # pylint: disable=too-many-instance-attributes, too-many-arguments, consider-using-generator, invalid-name

    filter = FieldProperty(IRegionalAccounts['filter'])

    def __init__(self, RateLimit, Account, Filter=None, RateLimitRegionSpec=None, service='ec2'):
        """Initialize the RegionalAccounts container."""
        self.filter = Filter if Filter else {}

        self._rate_limit = RateLimit
        self._account_properties = Account
        self._account = account_factory(**Account)
        self._service = service
        self._rate_limit_region_spec = RateLimitRegionSpec if RateLimitRegionSpec else {}

        self._rlock = RLock()
        self._regional_accounts = {}

    def _get_regional_account(self, region_name):
        with self._rlock:
            try:
                return self._regional_accounts[region_name]
            except KeyError:
                self._regional_accounts[region_name] = regional_account_factory(
                    self._rate_limit_region_spec[region_name] if region_name in
                    self._rate_limit_region_spec else self._rate_limit, self._account_properties, region_name)
            return self._regional_accounts[region_name]

    def account(self):
        """Return the accounts wrapped by this RegionalAccounts instance."""
        return self._account

    def __getitem__(self, key):
        """Get the requested regional account or raise as part of IEnumerableMapping."""
        if key not in self:
            raise KeyError(key)
        return self._get_regional_account(key)

    def get(self, key, default=None):
        """Get an attribute or return the default as part of IEnumerableMapping."""
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key):
        """Return whether the requested regional account is held by this wrapper as part of IEnumerableMapping."""
        return key in self.__iter__()

    def keys(self):
        """Return the requested regional account key held by this wrapper as part of IEnumerableMapping."""
        return (k for k in self)

    @cached(cache=TTLCache(maxsize=1000, ttl=86400))
    def _all_regions(self, partition_name, allow_non_regional):
        return self.account().session().boto3().get_available_regions(
                                self._service,
                                partition_name=partition_name,
                                allow_non_regional=allow_non_regional)

    def __iter__(self):
        """Iterate over all regions in this wrapper as part of IEnumerableMapping."""
        partitions = self.filter.get('Partitions', {'aws': None})

        regions = set()
        for name in set(partitions):
            p_config = partitions[name]
            if not p_config:
                p_config = {}
            include_non_regional = p_config.get('IncludeNonRegional', False)
            all_regions = self._all_regions(name, include_non_regional)

            region_include = set(p_config.get('Regions', {}).get('include', {}))
            if not region_include:
                region_include = set(all_regions)
            region_exclude = set(p_config.get('Regions', {}).get('exclude', {}))
            regions.update(region_include - region_exclude)

        for region in regions:
            yield region

    def values(self):
        """Return all regional accounts in this wrapper as part of IEnumerableMapping."""
        return tuple([self[k] for k in self])

    def items(self):
        """Return key and account for all regional accounts in this wrapper as part of IEnumerableMapping."""
        return tuple([(k, self[k]) for k in self])

    def __len__(self):
        """Return the number of regional accounts held in this wrapper as part of IEnumerableMapping."""
        return len(list(iter(self)))


RegionalAccountsFactory = Factory(RegionalAccounts)


@interface.implementer(IRegionalAccounts)
@cached(cache={}, key=aggregated_string_hash, lock=RLock())
def regional_accounts_factory(**kwargs):
    """Create and cache a cs.aws_account.regional_accounts.RegionalAccounts instance.

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
