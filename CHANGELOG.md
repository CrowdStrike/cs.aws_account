# Changelog

## 1.0.0

* initial release

## 1.0.1

* remove caching from regional_account_set_factory(). Contained objects are
  still cached, however.

## 1.0.2

* update call signature of session_factory to make SessionParameters optional
* update default regional accounts filter default to more sensible settings.
* fix call signature to regional_account_set_factory() and account_factory()

## 1.0.3

* small fix for logging for assume_role()

## 1.0.4

* add additional logging
* cache region information for performance improvement of RegionalAccounts()
* improve threaded performance of Session boto3 stack management
* add Python 3 compatibility

## 1.0.6

* fix Python syntax bug in regional accounts
* remove RegionalAccountException

## 1.0.7

* fix issue where client calls in Session() don't reference the sessions defaul
  region

## 1.0.8

* fix issue where default_region was used instead of correct region_name

## 1.0.9

* Allow public access to Session._client_kwargs, update broken client calls to
  reference correct region_name

## 1.1.0

* Add monkey patch to botocore.loaders.Loader methods that call os.listdir
  to leverage a global cache to prevent threaded slow calls.
* Update cs.aws_account.session.Session to make more efficient usage of
  botocore.credentials.RefreshableCredentials object, sharing across threads
  to prevent multiple calls to AWS for the same effective creds.

## 1.1.1

* Add unified pipeline build meta

## 1.1.2

* Add ability to defer role assumption processing
