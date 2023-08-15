"""Provides custom exceptions for cs.aws_account."""


class AWSClientException(Exception):
    """Represents a boto3 error raised from making a call to AWS API."""

    def __init__(self, error, *_, **kwargs):
        """Prepare the error message from the given error."""
        self._error = error
        self._account = kwargs['AccountAlias']
        self._account_id = kwargs['AccountId']
        self._region = kwargs['Region']
        self._warning = "None"
        error_string = str(self._error)
        if "NoSuch" in error_string:
            self._warning = "Queried item does not exist. Check in the AWS Web Console."
        elif "AccessDenied" in error_string:
            self._warning = "Improper AWS IAM permissions. Verify application role has permission to access resource."
        elif ("AuthFailure" in error_string or
              "InvalidClientTokenId" in error_string or
              "UnrecognizedClientException" in error_string):
            self._warning = ("Attempted to access a non-existent resource. "
                             "Ensure the action, account, and region are removed from the RAS filter")
        self._error_message = (f"Error message: {error_string}. Account Alias: {str(self._account)}. "
                               f"Account ID: {str(self._account_id)}. "
                               f"Region: {str(self._region)}. Warning: {str(self._warning)}")
        super().__init__(self._error_message)

    def __str__(self):
        """Emit the prepared error message."""
        return str(self._error_message)
