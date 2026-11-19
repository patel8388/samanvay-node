# Contributing to Samanvay Node

Thanks for helping explore this experimental project. Contributions are **unpaid volunteer collaboration unless separately agreed**; there is no compensation, bounty, or financial promise. Please keep the project’s current status in mind: this is a Python 3.12 prototype, not mainnet software and not ready for a public testnet.

## Good ways to help

We welcome:

- Python implementation, test, and documentation improvements.
- Reproducible test reports and cross-platform fixes.
- Network and difficulty-design review from people with relevant experience. This is **not a beginner implementation task**; reviewers should be comfortable identifying protocol and incentive risks.
- Independent security review.
- Four independent operators for a rehearsal using the offline, block-only exchange described in [docs/PRIVATE_OPERATOR_CHECK.md](docs/PRIVATE_OPERATOR_CHECK.md). Operators should not expose a node publicly.

The test token **tSAMV has no value, redemption, or entitlement**, and participation does not create any such expectation.

## Local setup

Use a virtual environment; do not install project dependencies globally. From the repository root:

### macOS/Linux

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
./verify.sh
```

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m compileall -q samanvay tests
python -m unittest discover -s tests -v
Push-Location docs/reference
python -m unittest discover -s . -p test_reference_rules.py -v
Pop-Location
```

The prototype pins `cryptography==50.0.2`. `./verify.sh` requires Bash and runs the unittest node suite and 27 reference tests. Native Windows compatibility is not yet qualified; report platform-specific failures rather than assuming the POSIX packaging helpers work there. The examples include `examples/local_demo.py` and `examples/operator_rehearsal.py`. Before reporting a result, record your OS, Python version, command, and whether the complete verification passed. The latest recorded source verification totals are in `test-results.txt`; a four-process local rehearsal is separate evidence. An owner-reported VPS run is not independent operator validation.

## Safety boundaries

- Use disposable keys, databases, and test data only.
- Keep transport loopback-only; do not bind services to public interfaces or expose ports.
- Do not send wallet/private keys, passwords, SSH credentials, or personal device identifiers in issues, logs, pull requests, or chat.
- Do not present the bounded prototype retarget or its easy target ceiling as production proof; independent consensus and attack review are still needed.
- Do not treat local or owner-reported runs as independent network evidence.

## Issues and pull requests

1. Open a focused branch for one change or investigation.
2. Run the relevant focused tests, then `./verify.sh` when practical.
3. Explain what changed, what you tested, and any known limitation.
4. Keep documentation and examples honest about prototype status.
5. Submit a focused pull request for review; avoid unrelated formatting churn.

Public issues and PRs are for non-sensitive discussion. If you find a possible vulnerability, follow `SECURITY.md` instead of posting exploit details publicly. Contributions are made under the repository's MIT license; no separate CLA is required.
