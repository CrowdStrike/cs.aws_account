from zope.component.testlayer import ZCMLFileLayer
import cs.aws_account

AWS_ACCOUNT_INTEGRATION_LAYER = ZCMLFileLayer(cs.aws_account,
                                          zcml_file='ftesting.zcml',
                                          name='AWSAccountComponents')
