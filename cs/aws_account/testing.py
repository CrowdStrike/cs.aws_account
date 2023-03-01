"""Test helpers for cs.aws_account."""
import warnings

from zope.component.testlayer import ZCMLFileLayer

import cs.aws_account


# see https://github.com/boto/boto3/issues/454
warnings.filterwarnings("ignore", message="unclosed.*<ssl.SSLSocket.*>")


AWS_ACCOUNT_INTEGRATION_LAYER = ZCMLFileLayer(cs.aws_account,
                                              zcml_file='ftesting.zcml',
                                              name='AWSAccountComponents')
