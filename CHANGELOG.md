# Version 1.3.2
## Added features and functionality
+ Added: Decorator for retrying throttled API calls that slip through boto's throttle/retry logic.
    - `cs/aws_account/retry.py`
    - `cs/aws_account/account.py`
    - `cs/aws_account/regional_account.py`
    - `cs/aws_account/session.py`
    - Thanks to @molatif-dev for the addition!

## Issues Resolved
+ Fixed: Removed TTL from cached account attributes that don't change.
    - `cs/aws_account/session.py`
    - Thanks to @molatif-dev for the fix!

## Other
+ Bump cs.ratelimit from 1.3.0 to 1.3.1
+ Bump boto3 from 1.28.46 to 1.28.47
+ Bump botocore from 1.31.46 to 1.31.47
+ Bump gitpython from 3.1.32 to 3.1.36

---
# Version 1.3.1
## Issues Resolved
+ Fixed: RegionalAccounts sending wrong argument to the regional account factory.
    - `cs/aws_account/regional_accounts.py`

---
# Version 1.3.0
**Stable Open Source Release**
