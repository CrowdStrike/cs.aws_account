# AWS ACCOUNT

## Session

The cs.aws_account.Session class provides convienent, threadlocal access to
boto3.session.Session() objects.  Major features includes:
  - a single cs.aws_account.Session() object can be used across threads safely
  - memoized methods for some methods for performant re-calls (i.e. for 
    logging)
  - built-in support for IAM role-assumption, including automated credential
    refreshing

Creating a cs.aws_account.Session is easy...just pass in the same kwargs you 
would for boto3.session.Session (in this example, we get the values from the
current environment).

```python
>>> import os
>>> from cs.aws_account import Session
>>> session_kwargs = {
...     'aws_access_key_id':     os.environ.get('AWS_ACCESS_KEY_ID'),
...     'aws_secret_access_key': os.environ.get('AWS_SECRET_ACCESS_KEY')
... }
>>> session = Session(**session_kwargs)

```

You can now get access to a threadlocal boto3.session.Session() object.

```python
>>> b3 = session.boto3()
>>> type(b3)
<class 'boto3.session.Session'>
>>> b3.get_credentials().access_key == session_kwargs['aws_access_key_id']
True

```

Multiple calls will return the same object (within the same thread)

```python
>>> session.boto3() is session.boto3()
True

```

Different threads will get unique threadlocal boto3.session.Session() objects

```python
>>> import threading
>>> thread_b3 = []
>>> def b3():
...     thread_b3.append(session.boto3())
>>> t1 = threading.Thread(target=b3)
>>> t1.start(); t1.join()
>>> thread_b3[0] is session.boto3()
False

```

It's easy to assume new IAM roles, simply call 
cs.aws_account.Session.assume_role with the same arguments as 
boto3.session.Session().client('sts').assume_role()


```python
>>> b4_key = session.access_key()
>>> assume_role_kwargs = {
...     'RoleArn': os.environ.get('AWS_ASSUME_ROLE'),
...     'RoleSessionName': 'testing_assume_role_for_cs_aws_account_package'
... }
>>> session.assume_role(**assume_role_kwargs)
>>> b4_key == session.access_key()
False

```

Assuming a role is threadsafe and will cascade to other threads.  Keep in mind
that other threads will need to get new references to realize this (e.g.
call cs.aws_account.Session.boto3() again)

```python
>>> thread_key = []
>>> def b3():
...     thread_key.append(session.access_key())
...     new_b3 = session.boto3() # just illustrating that threads will need to get a new reference
>>> t1 = threading.Thread(target=b3)
>>> t1.start(); t1.join()
>>> session.access_key() == thread_key[0]
True

```

We can also revert from an assumed role (same as above from a thread standpoint)

```python
>>> assumed_role_key = session.access_key()
>>> assumed_boto3_session = session.revert() #returns the pop'd session
>>> session.access_key() == assumed_role_key
False
>>> session.access_key() == b4_key
True

```