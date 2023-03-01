from boto3.session import Session
from zope import interface


class IBoto3Session(interface.Interface):
    """Marker for a Boto3 session object"""


interface.classImplements(Session, IBoto3Session)
