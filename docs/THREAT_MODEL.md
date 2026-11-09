# Threat model: experimental, no-value local node

This is a review starting point, not an audit or a claim of complete coverage. All balances are disposable tSAMV: no value, redemption or mainnet entitlement. Source publication does not authorize a public network.

## What must remain true

Every accepted block must preserve the configured supply ceiling, valid ownership signatures, restricted allocation rules, coinbase maturity, branch-local reward accounting and deterministic state roots. Chain choice must follow valid cumulative proof of work, not founder permission or stake weight. Restart and reorganization must reconstruct the same validated state.

## Trust boundaries and known risks

| Boundary | Threat | Current limit / review needed |
| --- | --- | --- |
| Block and transaction input | Forged signatures, replay, malformed types, oversized data and reward theft | Strict schemas and existing tests are not a proof of safety; add adversarial tests and bounded fuzzing. |
| Chain selection | Outside hashpower rewriting history | Fixed easy target; no difficulty adjustment. Never use valuable assets. Review mining assumptions and timestamps before any networking expansion. |
| Peer HTTP and offline bundles | Resource exhaustion, malicious pagination, divergent histories | HTTP stays loopback-only. Offline block imports remain untrusted, bounded inputs; use disposable environments and examine partial-import failures. |
| SQLite and cached state | Tampering, replay divergence, crash/reorg inconsistencies, disk exhaustion | Replay and fork tests exist. Independent resource, recovery and durability review remains necessary. |
| Keys and signing | Local key theft or reuse with real assets | A new Scrypt/AES-GCM local test keystore is available, but it is unaudited, can be attacked offline, and exposes the key to the host process while signing. The legacy `keygen` format remains plaintext; the founder fixture key is public. Never use real assets or seeds, share wallet files or commit generated keys. |
| Dependencies and builds | Compromised dependencies, misleading checksums or release artifacts | Review pinned dependencies and licenses. SHA256SUMS proves file consistency only, not publisher trust or code safety. |
| Reward and lock rules | Rounding errors, boundary errors, double claims and invalid eligibility | Independently check integer arithmetic, epoch boundaries, fork rollback, unclaimed backing and supply conservation. |
| Contributors and operators | False independence or premature launch claims | Four processes or VPS nodes controlled by one person are not independent operators; record independent evidence without collecting secrets or personal device identifiers. |

## Safe reviewer workflow

1. Inspect the source before execution. Use an unprivileged disposable VM, container or isolated account with no valuable files, wallet seeds or service credentials.
2. Run the verification suite and finite examples. Keep listeners on loopback; do not modify firewall/router settings or buy hosting/mining services for this review.
3. For independent cross-machine testing, follow [PRIVATE_OPERATOR_CHECK.md](PRIVATE_OPERATOR_CHECK.md) and exchange block-only JSON through an agreed private channel. Never exchange keys or databases.
4. Report exact source identity, environment versions, reproducible failures and expected invariants. Redact personal paths and identifiers. Follow [SECURITY.md](../SECURITY.md) for exploitable findings rather than putting exploit details in a public issue.

## Gates still open

Independent architecture/security review, reviewed difficulty adjustment, hostile-input and resource testing, qualified bounded P2P, independent operators and separately authorized network/soak work are outstanding. Mobile custody, grant/council custody, sponsorship and a funded faucet are not implemented. See [RELEASE_GATES.md](RELEASE_GATES.md). Passing tests is neither an audit nor public-testnet approval.
