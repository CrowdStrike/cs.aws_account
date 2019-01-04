from zope import interface
from zope.interface.common.mapping import IEnumerableMapping
from zope import schema
from cs import ratelimit

class ISession(interface.Interface):
    """Boto3 Session accessor"""
    
    def boto3():
        """Return active boto3 session"""
    
    def assume_role(sts_method='assume_role', **kwargs):
        """Replace active boto3 session with assumed role boto3 session
        
        Kwargs:
            sts_method: name of sts Client method used to execute the role assumption
            [others]:  Other kwargs are passed unalltered into the named sts role assumption method
        """
    
    def revert():
        """Revert active session to previous boto3 session in used before last call to assume_role().
        
        Attempting to revert the originating boto3 session object does nothing.
        
        Returns
            active session previous to the revert operation
        """
    
    def access_key():
        """Return access key string in use for the referenced boto3 object"""
    
    def account_id():
        """Return AWS account identity string in use for the referenced boto3 object"""
    
    def user_id():
        """Return AWS account identity string in use for the referenced boto3 object"""
    
    def arn():
        """Return AWS account identity string in use for the referenced boto3 object"""

class IAccount(interface.Interface):
    """AWS account"""
    
    def account_id():
        """Return AWS account identity string"""
    
    def alias():
        """Return first AWS account alias string else account identity"""
    
    def aliases():
        """Return iterable of all AWS account alias strings"""
    
    def session():
        """Return ISession provider"""

class IRegionalAccount(interface.Interface):
    """A boto3 session client caller with rate limiting capabilities"""
    
    ratelimit = schema.Object(
            title=u"Rate limit properties",
            description=u"Rate limiting properties",
            required=True,
            schema=ratelimit.IRateLimitProperties
        )
    
    def account():
        """Return IAccount provider"""
    
    def region():
        """Return AWS region string"""
    
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
    
    def get_paginator(service, method, client_kwargs=None, **kwargs):
        """Return paginator for boto3 service client method limited by properties in ratelimit
        
        same call features as call_client() except calls are accessed via
        a returned paginator
        """

class IRegionalAccounts(IEnumerableMapping):
    """Mapping whose keys are AWS region strings and values are 
    related IRegionalAccount providers
    """
    
    filter = schema.Dict(
            title=u"Filter",
            description=u"The container filter specification",
            readonly=True, #but still mutable
            required=True
        )
    
    def account():
        """Return IAccount provider"""
    
class IRegionalAccountSet(interface.Interface):
    """A container of IRegionalAccounts providers that iterates over their content values (IRegionalAccount providers)"""
    
    def add(regional_accounts):
        """Adds IRegionalAccounts provider to include for iteration if not available"""
    def discard(regional_accounts):
        """Discards IRegionalAccounts provider from iteration if available"""
    def values():
        """frozenset of available IRegionalAccounts providers"""
    def __iter__():
        """Iterator of unique IRegionalAccount providers from available IRegionalAccounts providers"""
    
    