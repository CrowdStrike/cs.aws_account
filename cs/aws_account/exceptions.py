from botocore.exceptions import ClientError

class AWSClientException(Exception):
    """Represents an boto3 error raised from making a call to AWS API."""
    def __init__(self, error: ClientError, *args, **kwargs):
        """
        """
        self._error = error
        self._account = kwargs['AccountAlias']
        self._region = kwargs['Region']
        super().__init__(*args, **kwargs)

    def __str__(self):
        error_statement = "Error message: {}. Account: {}. Region: {}".format(str(self._error),str(self._account),str(self._region))
        return error_statement
