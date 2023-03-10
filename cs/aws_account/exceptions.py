class AWSClientException(Exception):
    """Represents an boto3 error raised from making a call to AWS API."""
    def __init__(self, error, *args, **kwargs):
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
        self._error_message = "Error message: {}. Account Alias: {}. Account ID: {}. Region: {}. Warning: {}".format(
            error_string, str(self._account), str(self._account_id), str(self._region), str(self._warning))
        super().__init__(self._error_message)

    def __str__(self):
        return str(self._error_message)
