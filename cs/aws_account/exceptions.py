from botocore.exceptions import ClientError

class AWSClientException(ClientError):
    """Represents an boto3 error raised from making a call to AWS API."""
    def __init__(self, error, *args, **kwargs):
        """
        """
        self._error = error
        self._account = kwargs['AccountAlias']
        self._account_id = kwargs['AccountId']
        self._region = kwargs['Region']
        self._warning = "None"
        if "NoSuch" in str(error):
            self._warning = "Queried item does not exist. Check in the AWS Web Console."
        elif "AccessDenied" in str(error):
            self._warning = "Improper AWS IAM permissions. Please contact IAM team to ensure Contour has permission to access resource."
        elif "AuthFailure" in str(error) or \
            "InvalidClientTokenId" in str(error) or \
            "UnrecognizedClientException" in str(error):
            self._warning = "Contour attempted to access a non-existent resource. Ensure the action, account, and region are removed from the RAS filter"
        self._error_message = "Error message: {}. Account Alias: {}. Account ID: {}. Region: {}. Warning: {}".format(str(self._error), str(self._account), str(self._account_id), str(self._region), str(self._warning))
        super().__init__(self._error_message)

    def __str__(self):
        return str(self._error_message)

