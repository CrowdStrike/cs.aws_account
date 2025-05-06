"""Retry module for AWS throttling error."""
import time
import logging

# pylint: disable=global-variable-not-assigned, invalid-name


logger = logging.getLogger(__name__)


def aws_throttling_retry(max_retries=5, base=0.5, growth_factor=0.5):
    """Retry AWS throttling errors with exponential backoff time.

    Calculate time to sleep based on below function.
    The format is::
        base + (retries * growth_factor)

    Kwargs:
    max_retries: Max number of retries when hitting AWS throttling error
    base: base time for exponential backoff calculation
    growth_factor: growth factor used to calculate sleeping time for every retry
    """
    def decorator_retry(func):
        def wrapper(*args, **kwargs):  # pylint: disable=inconsistent-return-statements
            if max_retries < 1:
                raise ValueError("max_retries can't be less than 1")

            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as error:  # pylint: disable=broad-exception-caught
                    err_str = str(error).lower()
                    if 'throttling' in err_str or 'rate exceeded' in err_str or 'limitexceeded' in err_str:
                        retries += 1
                        if retries >= max_retries:
                            logger.warning("Received AWS throttling error. Exhausted all attempts.")
                            raise error
                        backoff_seconds = base + (retries * growth_factor)
                        logger.warning("Received AWS throttling error. Retrying in %s seconds...",
                                       backoff_seconds)
                        time.sleep(backoff_seconds)
                    else:
                        raise error
        return wrapper

    return decorator_retry
