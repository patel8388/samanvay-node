# Help build and review Samanvay

Samanvay is an experimental Python 3.12 local node with SHA-256d mining, signed transfers, rewarded token locks and SQLite persistence. It is **not production software, mainnet or ready for a public testnet**. All tSAMV balances have no value, redemption or future allocation entitlement.

## People we need

- **Python and test contributors:** reproducible setup, cross-platform reports, small documentation fixes, negative tests and bounded property/fuzz testing.
- **Protocol reviewers:** independently evaluate the bounded prototype difficulty adjustment, timestamp handling, cumulative-work chain choice, mining assumptions and rewarded-locking invariants.
- **Network/security reviewers:** review a safe bounded transport design, resource ceilings, input validation and failure recovery. The current loopback guard must stay in place.
- **Four independent volunteer operators:** run the documented [offline block-only check](PRIVATE_OPERATOR_CHECK.md) on separate existing machines. Four processes managed by one person are not four independent operators.

This is unpaid volunteer collaboration unless separately agreed. There are no bounties, token grants or investment opportunities promised. Nobody needs to purchase hosting or mining equipment, expose a port, provide SSH access, or share a private key.

Start with [CONTRIBUTING.md](../CONTRIBUTING.md) and [open issues](https://github.com/patel8388/samanvay-node/issues). Use the volunteer introduction template with the role you prefer, relevant public experience if you want to share it, and a small first task. No résumé, legal name or personal contact information is needed in public. Review [SECURITY.md](../SECURITY.md) before reporting vulnerabilities.

## Short invitation for community-approved sharing

> Looking for volunteer Python contributors and experienced protocol/security reviewers for Samanvay, an experimental Python 3.12 no-value local blockchain prototype. Mining, rewarded token locking and a bounded prototype difficulty adjustment are implemented, but independent consensus review, public P2P and operator qualification remain missing. We have small documentation/reproducibility tasks plus bounded review tasks, and need four independent operators for offline block-only testing. No investment, valuable tokens, promised rewards or public-node deployment. Code and participation guide: https://github.com/patel8388/samanvay-node/blob/main/CONTRIBUTING.md

This is a draft invitation, not evidence that a community has accepted the project or that volunteers have joined. Ask permission where required; do not send unsolicited bulk messages or tag unrelated developers.

## Where to look next

1. **[Python Discord](https://www.pythondiscord.com/):** relevant for Python testing and development collaborators. Its [rules](https://www.pythondiscord.com/pages/rules/) prohibit unapproved advertising; ask moderators which channel, if any, permits this invitation before posting.
2. **[CodeTriage](https://www.codetriage.com/):** routes open-source issues to potential contributors. Submit the repository only after it has clear, genuinely small issues and onboarding. [Submission](https://www.codetriage.com/repos/new) requires login; no listing or acceptance is claimed here.
3. **[OpenSSF working groups](https://openssf.org/community/openssf-working-groups/):** useful for secure-development practices and pointers to reviewers. This is not a free audit service or an endorsement request.
4. **[OWASP local chapters](https://owasp.org/chapters/) and [community](https://owasp.org/www-community/):** possible routes for educational threat-model, Python input-validation and resource-limit review. Consensus expertise is a separate need; do not describe informal peer feedback as an audit.

These are researched outreach routes, not recruited people. External posting, applications and personal outreach have not been performed.
