"""Interfaces for wiring together components using Boto3 sessions."""
from boto3.session import Session
from zope import interface
# pylint: disable=inherit-non-class


class IBoto3Session(interface.Interface):
    """Marker for a Boto3 session object."""


interface.classImplements(Session, IBoto3Session)
