# Security policy

## Scope and status

Samanvay Node is an experimental Python 3.12 prototype. It has **not received an independent security audit**, is not mainnet software, and is not ready for a public testnet. Transport is intended to remain loopback-only; the current design uses a fixed easy target and has no difficulty adjustment. Do not run it on public interfaces or with valuable data.

The test token **tSAMV has no value, redemption, or entitlement**. There is no bounty, compensation, or guaranteed reward for reports.

## Reporting a suspected vulnerability

Please do not put exploitable security details, working exploit code, private keys, credentials, or sensitive logs in a public issue.

- If GitHub **Private vulnerability reporting** is enabled for this repository, use that channel.
- If it is not enabled, contact the repository owner through an available private contact before disclosing exploit details. This project does not publish an email address here; do not guess one or send secrets to an unverified address.

A useful private report can include a short impact summary, affected revision or file, safe reproduction outline, and mitigation ideas. Redact keys, passwords, SSH material, device identifiers, and other personal data. Use disposable keys and databases for any reproduction, and keep any test node loopback-only.

Please allow the owner to acknowledge and investigate before public disclosure. There is **no promised response SLA**, and receipt, remediation, credit, or disclosure timing is not guaranteed. If private reporting is unavailable or the issue is not sensitive, use a public issue while omitting exploit-enabling details.