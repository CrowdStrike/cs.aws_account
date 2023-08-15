"""A set of tools for working with AWS accounts.

The methods list_available_services() and list_api_versions() leverage
os.listdir() which is very slow when called from within
concurrent.futures.ThreadPoolExecutor instances.  Sadly, these are called when
a boto3.Session.create_client() is called.  This process becomes prohibitive
when the use-case creates new boto3 session objects in threads (like we do).

We'll monkey patch these two services to leverage a global call cache (vs the
default instance call cache), which insures a caches across instances.
"""

# pylint: disable=wrong-import-position

import botocore.loaders

from .monkies import global_cache


botocore.loaders.Loader.list_available_services = global_cache(
    botocore.loaders.Loader.list_available_services)
botocore.loaders.Loader.list_api_versions = global_cache(
    botocore.loaders.Loader.list_api_versions)


from .interfaces import IAccount
from .interfaces import IRegionalAccount
from .interfaces import IRegionalAccountSet
from .interfaces import IRegionalAccounts
from .interfaces import ISession
from .session import Session
from .session import session_factory  # caching
from .account import Account
from .account import account_factory  # caching
from .regional_account import RegionalAccount
from .regional_account import regional_account_factory  # caching
from .regional_accounts import RegionalAccounts
from .regional_accounts import regional_accounts_factory  # caching
from .regional_account_set import RegionalAccountSet
from .regional_account_set import regional_account_set_factory  # non-caching (but contained objects are cached)


__all__ = [
    'IAccount', 'IRegionalAccount', 'IRegionalAccountSet', 'IRegionalAccounts', 'ISession',
    'Session', 'session_factory', 'Account', 'account_factory', 'RegionalAccount', 'regional_account_factory',
    'RegionalAccounts', 'regional_accounts_factory', 'RegionalAccountSet', 'regional_account_set_factory',
]
