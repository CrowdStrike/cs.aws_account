![CrowdStrike cs.aws_account](https://raw.githubusercontent.com/CrowdStrike/cs.aws_account/main/docs/img/cs-logo.png)

# Contributing to this repository <!-- omit in toc -->

_Welcome!_ We're excited you want to take part in the CrowdStrike OSS community!

Please review this document for details regarding getting started with your first contribution, packages you'll need to install as a developer, and our Pull Request process.

> **Before you begin**: Have you read the [Code of Conduct](https://github.com/CrowdStrike/cs.aws_account/blob/main/CODE_OF_CONDUCT.md)?
> The Code of Conduct helps us establish community norms and how they'll be enforced.

- [How you can contribute](#how-you-can-contribute)
- [Bug reporting](#bug-reporting-is-handled-using-github-issues)
- [Pull Requests](#pull-requests)
    + [Contributor dependencies](#additional-contributor-package-requirements)
    + [Unit testing and Code Coverage](#unit-testing-and-code-coverage)
    + [Code Quality and Style (Linting)](#code-quality-and-style-linting)
    + [Breaking changes](#breaking-changes)
    + [Branch targeting](#branch-targeting)
    + [Pull Request Restrictions](#pull-request-restrictions)
    + [Approval and Merging](#approval-and-merging)
    + [Releases](#releases)
- [Suggestions](#suggestions)

## How you can contribute
- See something? Say something! Submit a [bug report](https://github.com/CrowdStrike/cs.aws_account/issues) to let the community know what you've experienced or found. Bonus points if you suggest possible fixes or what you feel may resolve the issue. For example: "_Attempted to use the XZY API class but it errored out. Could a more descriptive error code be returned?_"
- Submit a [Pull Request](#pull-requests)

## Bug reporting is handled using GitHub issues
[![GitHub issues](https://img.shields.io/github/issues-raw/crowdstrike/cs.aws_account?logo=github)](https://github.com/CrowdStrike/cs.aws_account/issues?q=is%3Aopen+is%3Aissue)
[![GitHub closed issues](https://img.shields.io/github/issues-closed-raw/crowdstrike/cs.aws_account?color=green&logo=github)](https://github.com/CrowdStrike/cs.aws_account/issues?q=is%3Aissue+is%3Aclosed)

We use [GitHub issues](https://github.com/CrowdStrike/cs.aws_account/issues) to track:

+ [bugs](https://github.com/CrowdStrike/cs.aws_account/issues?q=is%3Aissue+label%3A%22bug+%3Abug%3A%22) (`BUG`)
+ [documentation](https://github.com/CrowdStrike/cs.aws_account/issues?q=is%3Aissue+label%3A%22documentation+%3Abook%3A%22) and [linking](https://github.com/CrowdStrike/cs.aws_account/issues?q=is%3Aissue+label%3A%22broken+link+%3Alink%3A%22) issues (`DOC`, `LINK`)
+ [enhancements](https://github.com/CrowdStrike/cs.aws_account/issues?q=is%3Aissue+label%3A%22enhancement+%3Astar2%3A%22) (`ENH`)
+ [security concerns](https://github.com/CrowdStrike/cs.aws_account/issues?q=is%3Aissue+label%3Asecurity) (`SEC`)

[![Report Issue](https://raw.githubusercontent.com/CrowdStrike/cs.aws_account/main/docs/img/report-issue.png)](https://github.com/CrowdStrike/cs.aws_account/issues/new/choose)


---

## Pull Requests
In order for your pull request to be merged, it must pass code style and unit testing requirements. Pull requests that do not receive responses to feedback or requests for changes will be closed.

### All contributions will be submitted under the MIT license
When you submit code changes, your submissions are understood to be under the same MIT [license](LICENSE) that covers the project.
If this is a concern, contact the maintainers before contributing.

### Additional contributor package requirements
`requirements-dev.txt` contains Python modules required for unit test development. Review this file's contents and install missing requirements as needed or install them all with the following command.

```shell
pip3 install -r requirements-dev.txt
```

### Unit testing and Code Coverage
+ All submitted code must also have an associated unit test that tests common and edge cases of the change.
    - If the code submission is already covered by an existing unit test, additional unit tests are not required.
    - Please include coverage results in any Pull Requests. Any change that reduces the current overall coverage percentage may be closed without merging.
+ All new contributions __must__ pass unit testing before they will be merged.
    - For scenarios where unit testing passes in the PR and fails post-merge, a maintainer will address the issue. If the problem is programmatic and related to code within the pull request, the merge may be reverted.
+ We use `bandit` for static code analysis.
    - Please include bandit analysis results in your Pull Request.
    - Pull Requests that produce alerts in `bandit` may be closed without merging.
+ The util folder contains a BASH script, `run-tests.sh`, that contains the parameters used that match unit testing performed as part of our GitHub workflows, and will generate the coverage and bandit analysis required for making Pull Requests.

> You can run all unit tests by executing the command `run-tests.sh` from the root of the project directory after installing the project locally.

### Code Quality and Style (Linting)

All submitted code must meet minimum linting requirements. We use the Flake8 framework and pylint for our lint specification.
+ All code that is included within the installation package must pass linting workflows when the Pull Request checks have completed.
    - We use `flake8`, `pydocstyle` and `pylint` to power our linting workflows.
    - You will be asked to correct linting errors before your Pull Request will be approved.
+ Unit tests do not need to meet this requirement, but try to keep linting errors to a minimum.
+ Refer to the `lint.sh` script within the util folder to review our standard linting parameters.
> You can quickly check the linting for all code within the src folder by executing the command `lint.sh` from the root of the project directory after installing the project locally.

More information about _Flake8_ can be found [here](https://flake8.pycqa.org/en/latest/).

More information about _pydocstyle_ can be found [here](http://www.pydocstyle.org/en/stable/).

More information about _Pylint_ can be found [here](https://www.pylint.org/).

### Breaking changes
In an effort to maintain backwards compatibility, we thoroughly unit test every Pull Request for all versions of Python we support. These unit tests are intended to catch general programmatic errors and _potential breaking changes_.

> If you have to adjust a unit test locally in order to produce passing results, there is a possibility you are working with a potential breaking change.

Please fully document changes to unit tests within your Pull Request. If you did not specify "Breaking Change" on the punch list in the description, and the change is identified as possibly breaking, this may delay or prevent approval of your PR.

### Pull Request restrictions
Please review this list and confirm none of the following concerns exist within your request.
Pull requests containing any of these elements will be prevented from merging to the code base and may be closed.

| Concern | Restriction |
| :--- | :--- |
| **Archives** | Limited exceptions to be reviewed by maintainers on a case by case basis. |
| **Binaries** | Compiled binaries, regardless of intent should not be included. |
| **Disparaging references to 3rd party vendors in source or content** | We are here to collaborate, not bash the work of others. |
| **Inappropriate language, comments or references found within source or content** | Comments (and comment art) must not detract from code legibility or impact overall package size. **All** content published to this repository (source or otherwise) must follow the [Code of Conduct](https://github.com/CrowdStrike/cs.aws_account/blob/main/CODE_OF_CONDUCT.md). |
| **Intellectual property that is not yours** | Copywrited works, trademarks, source code or image assets belonging to others should not be posted to this repository whatsoever. CrowdStrike assets which are already released into the Public Domain will be accepted as long as their usage meets other restrictions, the rules specified in the [Code of Conduct](https://github.com/CrowdStrike/cs.aws_account/blob/main/CODE_OF_CONDUCT.md), and the guidelines set forth in the [CrowdStrike Brand Guide](https://crowdstrikebrand.com/brand-guide/). |
| **Relative links in README files** | This impacts our package deployment as these files are consumed as part of the build process. All link and image references within README files must contain the full URL. |

### Approval and Merging
All Pull Requests must be approved by at least one maintainer. Once approved, a maintainer will perform the merge and execute any backend processes related to package deployment.

At this point in time, `main` is a protected branch and should be the target of all Pull Requests.


---

<p align="center">
  <img src="https://raw.githubusercontent.com/CrowdStrike/cs.aws_account/main/docs/img/cs-logo-footer.png"><br/>
  <img width="350px" src="https://raw.githubusercontent.com/CrowdStrike/cs.aws_account/main/docs/img/turbine-panda.png">
</p>
<h3><p align="center">WE STOP BREACHES</p></h3>
