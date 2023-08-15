![CrowdStrike cs.aws_account](https://raw.githubusercontent.com/CrowdStrike/cs.aws_account/main/docs/img/cs-logo.png)

# cs.aws_account

Boto3 provides nice bindings into the AWS API.  However, when dealing with
a complex environment with many regions and accounts, the default calls can
become cumbersome.  This package provides some convenience layers to
application builders that wish to remove some of the complexities for
common tasks such as account coordination, call limiting, and threaded
access.

Why might you want to use this package?

  - You're worried about call rates to the AWS API
  - You're developing a multi-threaded application and you'd like to provide
    thread-safe global access to boto3.session.Session objects.
  - You'd like to allow runtime configuration to determine which AWS
    accounts and regions are acted on by your application.

## Narrative Application Usage

Although individual package components are easy enough to understand, as a
whole, things get complex.  To help your introduction, this section provides
quick narratives to component usage.

### Configuration

It all starts with configuration.  In these examples, we'll leverage Yaml and
Jinga (to allow for anchors/references and config macros) to help
iilustrate how a real-world deployment might work.

Given the following YAML file, named `config.yaml`:

```yaml
SessionParameters: &aws_api_creds
 aws_access_key_id: {{AWS_ACCESS_KEY_ID}}
 aws_secret_access_key: {{AWS_SECRET_ACCESS_KEY}}

Account: &default_account
 SessionParameters: *aws_api_creds
  AssumeRole:
   RoleArn: {{AWS_ASSUME_ROLE}}
   RoleSessionName: test_assumed_role_session #arbitrary name

RateLimit: &default_ratelimit
 max_count: 10
 interval: 1
 block: True

RegionalAccounts: &us-east-1
 Account: *default_account
 RateLimit: *default_ratelimit
 Filter:
  Partitions:
   aws:
    IncludeNonRegional: True
    Regions:
     include: [us-east-1]

RegionalAccounts: &all-execpt-us-east-1
 Account: *default_account
 RateLimit: *default_ratelimit
 Filter:
  Partitions:
   aws:
    Regions:
     exclude: [us-east-1]

YourApp:
 RegionalAccountSet:
  - RegionalAccounts: *us-east-1
  - RegionalAccounts: *all-execpt-us-east-1
```

The following code will parse the YAML into Python data structures and
interpolate the named environment variables into the configuration.

```python
>>> from jinja2 import Template
>>> import os
>>> import yaml
>>> with open('config.yaml') as config_file:
...     rendered_config = Template(config_file.read()).render(os.environ)
>>> config = yaml.load(rendered_config)
```

Most of the entries in the config have parameters defined by `cs.aws_account`.
The exception is the *YourApp* entry, which determines how your application
will consume the rest of the configuration parameters.  In this example,
the application is choosing to produce a
`cs.aws_account.regional_account_set.RegionalAccountSet` instance for consumption.

Here's how the app should initialize this object

```python
>>> from cs.aws_account.regional_account_set import regional_account_set_factory
>>> accounts = None
>>> def my_app_initialization(config):
...     global accounts
...     accounts = regional_account_set_factory(*config['YourApp']['RegionalAccountSet'])
>>> my_app_initialization(config)
```

There is now a global `accounts` variable that can be leveraged across your
application whose contents was determined via configuration.  Some important
notes about this object:

 - It is iterable, producing instances of `cs.aws_account.regional_account.RegionalAccount`
   objects.
 - `cs.aws_account.regional_account.RegionalAccount` objects have methods to
   interface with boto3 `Session.Client()` and `Session.Client().get_paginator()`
   that have built-in ratelimiting...this is one of the reasons you're
   leveraging this package.
 - the usage of `cs.aws_account.regional_account_set.regional_account_set_factory`
   insured that the objects referenced are cached object singletons.  This
   means that other config-driven factory based objects with common call
   signatures will also reference these singletons.


### Custom endpoints

With AWS and boto3, customizing the endpoints used for the various AWS services
is possible, though doing so can be a bit finicky. To simplify this process with
`cs.aws_account`, add a nested object to the `SessionParameters`
configuration block in your YAML config, like the example below:

```yaml
ServiceEndpoints: &vpc_service_endpoints
 ec2: {{EC2_VPC_ENDPOINT}}
 sqs:
  us-east-1: {{SQS_VPC_ENDPOINT_US_EAST_1}}
  us-west-2: {{SQS_VPC_ENDPOINT_US_WEST_2}}

SessionParameters: &aws_api_creds
 aws_access_key_id: {{AWS_ACCESS_KEY_ID}}
 aws_secret_access_key: {{AWS_SECRET_ACCESS_KEY}}
 ServiceEndpoints: *vpc_service_endpoints

Account: &default_account
 SessionParameters: *aws_api_creds
 AssumeRole:
  RoleArn: {{AWS_ASSUME_ROLE}}
  RoleSessionName: test_assumed_role_session #arbitrary name

RateLimit: &default_ratelimit
 max_count: 10
 interval: 1
 block: True

RegionalAccounts: &us-east-1
 Account: *default_account
 RateLimit: *default_ratelimit
 Filter:
  Partitions:
   aws:
    IncludeNonRegional: True
    Regions:
     include: [us-east-1]

YourApp:
 RegionalAccountSet:
  - RegionalAccounts: *us-east-1
```

There are two important points to note here:

1. Cross-region custom endpoints are supported by specifying the endpoint as a map of region
   aliases to endpoints instead of strings for each service.
2. When using custom endpoints, because of limitations in the underlying boto3 library, the
   region specified for a given AWS API call must match the region of the custom endpoint, or
   `cs.aws_account` will fallback to the default endpoint for that service.

## Components

### The Session
The `cs.aws_account.Session` class provides convienent, threadlocal access to
`boto3.session.Session` objects.  Major features includes:
  - a single `cs.aws_account.Session` object can be used across threads safely
  - memoized methods for some methods for performant re-calls (i.e. for
    logging)
  - built-in support for IAM role-assumption, including automated credential
    refreshing

Creating a `cs.aws_account.Session` is easy...just pass in the same kwargs you
would for `boto3.session.Session` (in this example, we get the values from the
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

You can now get access to a threadlocal `boto3.session.Session` object.

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

Different threads will get unique threadlocal `boto3.session.Session` objects

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
`cs.aws_account.Session.assume_role()` with the same arguments as
`boto3.session.Session().client('sts').assume_role()`


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
call `cs.aws_account.Session.boto3()` again)

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

For environments that desire to leverage singletons for common
`cs.aws_account.Session()` initialization parameters, there is a convienence
factory

```python
>>> from cs.aws_account import session_factory
>>> session_factory(SessionParameters=session_kwargs) is \
...             session_factory(SessionParameters=session_kwargs)
True
```

> The caching singleton factories are only semi intelligent when it comes to
> understanding common non-hashable argument values.  The internal algorithm
> simply iterates args, sorts kwargs, and aggregates the `str()` values to
> determine the results hash...e.g. hash is impacted by things like value
> ordering.


### The Account
The `cs.aws_account.Account` class is mostly a small wrapper on top of
`cs.aws_account.Session` that provides accessors to cachable account information.

```python
>>> from cs.aws_account import Account
>>> account = Account(session=session)
>>> assert(account.account_id())

>>> account.session() is session
True
>>> account.alias() in account.aliases()
True
>>> account.account_id() == account.session().account_id()
True
```

As with `cs.aws_account.Session`, there is a caching singleton factory
available for common initialization parameters.  unlike Account, parameters
are the same as those for `cs.aws_account.Session`.

```python
>>> from cs.aws_account import account_factory
>>> account_factory(SessionParameters=session_kwargs) is \
...             account_factory(SessionParameters=session_kwargs)
True
```

### The Regional Account
The `cs.aws_account.RegionalAccount` class provides a thread-safe, runtime
adjustable, region-specific, rate limited boto3 Client caller and
paginator.

> See `cs.ratelimit` for detailed information on how rate limiting operates
> and the various configuration choices.

```python
>>> from cs.aws_account import RegionalAccount
>>> from cs.ratelimit import RateLimitProperties, RateLimitExceeded
>>> from datetime import timedelta
>>> rl = RateLimitProperties(max_count=1, interval=timedelta(seconds=1), block=False)
>>> raccount = RegionalAccount(rl, account, region_name='us-east-1')
>>> raccount.region() == 'us-east-1'
True
>>> raccount.account() is account
True
```

Simple boto3 Client call rate limits are now available (these calls are always
routed to named region).

```python
>>> _ = raccount.call_client('sts', 'get_caller_identity')
>>> try:
...     _ = raccount.call_client('sts', 'get_caller_identity')
... except RateLimitExceeded:
...     print('Too fast!')
Too fast!
```

We can change the rate limit behavior at runtime for the instance

```python
>>> raccount.ratelimit.max_count = 2
>>> _ = raccount.call_client('sts', 'get_caller_identity')
```

We can also get access to a rate limited paginator.  All calls to boto3 are
contolled by the same instance rate limiter.

```python
>>> paginator = raccount.get_paginator('ec2', 'describe_instances')
>>> page_iterator = paginator.paginate(PaginationConfig={'MaxItems': 10})
>>> try:
...     _ = page_iterator.__iter__().next()
... except RateLimitExceeded:
...     print('Too fast!')
Too fast!
>>> raccount.ratelimit.max_count = 3
>>> _ = page_iterator.__iter__().next()
```

All of this functionality is thread safe

```python
>>> raccount.ratelimit.max_count = 1
>>> raccount.ratelimit.interval = timedelta(seconds=.1)
>>> def parallel_call(raccount):
...     raccount.ratelimit.block = True
...     _ = raccount.call_client('sts', 'get_caller_identity')
>>> t1 = threading.Thread(target=parallel_call, args=(raccount,))
>>> t1.start()
>>> _ = raccount.call_client('sts', 'get_caller_identity')
>>> t1.join()
```

As with `cs.aws_account.Session` and `cs.aws_account.Account`, there is a caching
singleton factory available for common initialization parameters.

```python
>>> from cs.aws_account import regional_account_factory
>>> kwargs_raccount = {
...     'RateLimit':   {'max_count':1, 'interval':1, 'block':False},
...     'Account':     {'SessionParameters': session_kwargs},
...     'region_name': 'us-east-1'
...    }
>>> regional_account_factory(**kwargs_raccount) is \
...                 regional_account_factory(**kwargs_raccount)
True
```


### Regional Account Containers

Typically, an application has a set of operations that need to be performed
across several AWS accounts and/or regions.  `cs.aws_account.RegionalAccounts`
provides a readonly dict-like interfaces for filtered groups of
`cs.aws_account.RegionalAccount` objects.  A couple things to note:

 - The `RegionalAccounts` is a read only, thread-safe, container whose contents is
   initialized based a filter specification (see below).
 - A `RegionalAccounts` object only contains `RegionalAccount` objects from a
   single `Account` (i.e. from a single AWS account)
 - You can specify a default rate limit that gets individually applied across
   contained 'RegionAccount` objects in addition to named-region rate limits.

#### The Container Filter Specification

The key to understanding `RegionalAccounts` is to understand the `dict`
specification that determines their contents.  The full filter spec is listed
below (in _Yaml_ format).  All keys are optional.

```yaml
Partitions:
 aws: # valid AWS partition name.  If absent, defaults 'aws'
  IncludeNonRegional: True|False # include non-regional endpoint names, defaults to False
  Regions: #if absent, defaults to all available regions
   include: [list, of, regions] #if absent, defaults to all available regions
   exclude: [list, of, regions] #takes precedence over include
```

Here is a sample Python filter (implements above spec):

```python
>>> filter1 = {'Partitions':
...                {'aws':
...                     {'Regions':
...                          {'include': ['us-east-1']}
...           }     }   }
```

`RegionalAccounts` containers act like read-only dicts

```python
>>> from cs.aws_account import RegionalAccounts
>>> rl_kwargs = {'max_count':1, 'interval':1, 'block':False}
>>> filter1_raccts = RegionalAccounts(rl_kwargs, {'SessionParameters': session_kwargs}, Filter=filter1)
>>> print([r for r in filter1_raccts])
['us-east-1']
>>> 'us-east-1' in filter1_raccts
True
>>> isinstance(filter1_raccts['us-east-1'], RegionalAccount)
True
>>> filter1_raccts['us-east-1'].region() == 'us-east-1'
True
>>> len(filter1_raccts)
1
>>> print(filter1_raccts.get('us-east-2', 'not there'))
not there
>>> print([k for k in filter1_raccts.keys()])
['us-east-1']
>>> isinstance(filter1_raccts.values()[0], RegionalAccount)
True
>>> len(filter1_raccts.items()) == 1
True
```

We can now compare filtered vs non-filtered containers

```python
>>> all_raccts = RegionalAccounts(rl_kwargs, {'SessionParameters': session_kwargs})
>>> len(all_raccts) > len(filter1_raccts)
True
>>> 'us-east-2' not in filter1_raccts
True
>>> len(filter1_raccts)
1
>>> 'us-east-2' in all_raccts
True
```

Filters can be mutated, but not replaced.  Mutations are *not* generally
thread-safe, but the most typcail operations are atomic (e.g. thread safe)
see http://effbot.org/pyfaq/what-kinds-of-global-value-mutation-are-thread-safe.htm

```python
>>> filter1_raccts.filter['Partitions']['aws']['Regions']['include'].append('us-east-2')
>>> filter1_raccts.filter['Partitions']['aws']['Regions']['include'] = ('us-east-1', 'us-east-2',)
>>> 'us-east-2' in filter1_raccts
True
>>> try:
...     filter1_raccts.filter = {}
... except ValueError:
...    print("not allowed!")
not allowed!
```

because the `RegionalAccounts` implementation leverages the caching
`regional_account_factory` factory to produce `RegionalAccount` objects, the
referenced objects in the 2 containers above are the same

```python
>>> all_raccts['us-east-1'] is filter1_raccts['us-east-1']
True
```

> The fact that these containers leverage caching factories to populate their
> contents enables common rate-limits to be applied across containers....that's
> a feature.


As with the previous types, there is a caching singleton factory available for
common initialization parameters.

```python
>>> from cs.aws_account import regional_accounts_factory
>>> regional_accounts_factory(RateLimit=rl_kwargs, Account={'SessionParameters': session_kwargs}) is \
...        regional_accounts_factory(RateLimit=rl_kwargs, Account={'SessionParameters': session_kwargs})
True
```


### Regional Account Set

So far we've seen a `Session`, `Account`, `RegionalAccount`, and `RegionalAccounts`.
All instances of these types can act against a single AWS account.  Real
world usage scenarios extend beyond single AWS accounts.  To deal with this,
we provide a new (and final) container type...the
`cs.aws_account.RegionalAccountSet`.  The purpose of this new container is to
provide easy threadsafe, iterable access to aggregated sets of
`RegionalAccounts` values (e.g. `RegionalAccount` objects)

Creating a group is straight forward.  Just keep in mind that `add()`,
`discard()` and `values()` calls refer to `RegionAccounts` containers, whilst
`__iter__()` returns `RegionAccount` objects

```python
>>> from cs.aws_account import RegionalAccountSet
>>> set1 = RegionalAccountSet(all_raccts)
>>> len(set1.values())
1
>>> isinstance(list(set1.values())[0], RegionalAccounts)
True
>>> len([ra for ra in set1]) > 1
True
>>> isinstance(set1.__iter__().next(), RegionalAccount)
True
```

New `RegionalAccounts` can be added to the group, but the result set of
itered `RegionalAccount` objects are checked for uniqueness

```python
>>> set1.add(filter1_raccts)
>>> len(list(set1)) == len(all_raccts.values())
True
```

We can also remove `RegionalAccounts` from the group

```python
>>> set1.discard(all_raccts)
>>> len(list(set1)) == len(filter1_raccts.values())
True
```

You can check the group to see which `RegionalAccounts` containers are available

```python
>>> [filter1_raccts] == list(set1.values())
True
```

There is also a factory available at
`cs.aws_account.regional_account_set.regional_account_set_factory` which accepts
an arbritrary number of dicts providing the call signature of
`cs.aws_account.regional_account_set.regional_accounts_factory`.


---

<p align="center">
  <img src="https://raw.githubusercontent.com/CrowdStrike/cs.aws_account/main/docs/img/cs-logo-footer.png"><br/>
  <img width="300px" src="https://raw.githubusercontent.com/CrowdStrike/cs.aws_account/main/docs/img/alliance_team.png">
</p>
<h3><p align="center">WE STOP BREACHES</p></h3>