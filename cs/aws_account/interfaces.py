from zope import interface


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