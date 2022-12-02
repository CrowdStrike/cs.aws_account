# from botocore.exceptions import ClientError

class AWSClientException(Exception):
    """Represents an boto3 error raised from making a call to AWS API."""
    def __init__(self, error, *args, **kwargs):
        """
        """
        self._error = error
        self._account = kwargs['AccountAlias']
        self._region = kwargs['Region']
        self._error_message = "Error message: {}. Account: {}. Region: {}".format(str(self._error),str(self._account),str(self._region))
        super().__init__(self._error_message)

    def __str__(self):
        return str(self._error_message)

