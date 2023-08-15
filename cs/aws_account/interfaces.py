"""Declares interfaces for wiring components together."""
# pylint: disable=inherit-non-class, no-method-argument, no-self-argument, too-many-ancestors
from typing import Optional

from zope import interface
from zope import schema
from zope.interface.common.collections import IMutableMapping
from zope.interface.common.mapping import IEnumerableMapping

from cs import ratelimit


class ISession(interface.Interface):
    """Boto3 Session accessor."""

    def boto3():
        """Return active boto3 session."""

    def assume_role(sts_method='assume_role', deferred=False, **kwargs):
        """Replace active boto3 session with assumed role boto3 session.

        Kwargs:
            sts_method: name of sts Client method used to execute the role assumption
            deferred: Defers the actual role assumption operation until boto3() is called
            [others]:  Other kwargs are passed unalltered into the named sts role assumption method
        """

    def client_kwargs(service: Optional[str] = None) -> IMutableMapping:
        """Return shallow copy of self._client_kwargs.

        Args:
            service (Optional[str]): If given, and a service endpoint override
                is configured for the specified AWS service (e.g., 'sqs', 'sts'),
                it will be added to the returned client_kwargs mapping.

        Returns:
            mutable mapping of kwargs to pass to a `boto3.session.Session.client` call.
        """

    def revert():
        """Revert active session to previous boto3 session in used before last call to assume_role().

        Attempting to revert the originating boto3 session object does nothing.

        Returns
            active session previous to the revert operation
        """

    def access_key():
        """Return access key string in use for the referenced boto3 object."""

    def account_id():
        """Return AWS account identity string in use for the referenced boto3 object."""

    def user_id():
        """Return AWS account identity string in use for the referenced boto3 object."""

    def arn():
        """Return AWS account identity string in use for the referenced boto3 object."""


class IAccount(interface.Interface):
    """AWS account."""

    def account_id():
        """Return AWS account identity string."""

    def alias():
        """Return first AWS account alias string else account identity."""

    def aliases():
        """Return iterable of all AWS account alias strings."""

    def session():
        """Return ISession provider."""


class IRegionalAccount(interface.Interface):
    """A boto3 session client caller with rate limiting capabilities."""

    ratelimit = schema.Object(
            title="Rate limit properties",
            description="Rate limiting properties",
            required=True,
            schema=ratelimit.IRateLimitProperties
        )

    def account():
        """Return IAccount provider."""

    def region():
        """Return AWS region string."""

    def call_client(self, service, method, client_kwargs=None, **kwargs):
        """Return call to boto3 service client method limited by properties in ratelimit.

        This can raise cs.ratelimit.RateLimitExceeded based on ratelimit settings.

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
        """Return paginator for boto3 service client method limited by properties in ratelimit.

        Same call features as call_client() except calls are accessed via
        a returned paginator.
        """


class IRegionalAccounts(IEnumerableMapping):
    """Mapping whose keys are AWS region strings and values are related IRegionalAccount providers."""

    filter = schema.Dict(
            title="Filter",
            description="The container filter specification",
            readonly=True,  # but still mutable
            required=True
        )

    def account():
        """Return IAccount provider."""


class IRegionalAccountSet(interface.Interface):
    """A container of IRegionalAccounts providers that iterates over their IRegionalAccount providers."""

    def add(regional_accounts):
        """Add IRegionalAccounts provider to include for iteration if not available."""

    def discard(regional_accounts):
        """Discard IRegionalAccounts provider from iteration if available."""

    def values():
        """Frozenset of available IRegionalAccounts providers."""

    def __iter__():
        """Iterate unique IRegionalAccount providers from available IRegionalAccounts providers."""
