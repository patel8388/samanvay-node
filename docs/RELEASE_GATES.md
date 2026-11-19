# What this milestone does—and does not authorize

This repository is new experimental source for a **local, disposable, no-value devnet**. It is not the previously rejected NOVA implementation. It is not a qualified Bitcoin-derived client, an audited chain, a public network launch, or a valuable SAMV release. Test balances are not redeemable and carry no mainnet allocation or airdrop entitlement.

## Important design deviations

The target plan calls for evaluating a maintained, pinned Bitcoin-derived base. This milestone instead builds a small Python reference node so the mining and rewarded-locking state machine can actually run and be tested. That is a deliberate research prototype, not fulfillment of the qualified-base release gate. It uses an account ledger and Ed25519 signing rather than Bitcoin UTXOs, scripts, or signature tooling. It does not inherit Bitcoin security.

SHA-256d, an easy starting target and a bounded timestamp-window retarget are local experimental choices, not a frozen public mining algorithm or independently reviewed difficulty-adjustment algorithm. The short devnet profile accelerates lock and maturity testing; the rules profile preserves proposed plan timing. Every profile has a separate genesis and replay domain. Never present accelerated height durations as real calendar vesting.

Public endpoints, router/firewall changes, new cash expenditure, native mobile releases and mainnet are not part of this milestone. Source availability does not make this software safe for public exposure.

## Must remain blocked before a public testnet

- A qualified base or independently justified replacement architecture, dependency/license review and independent reproducible builds.
- Independent consensus/security review of all custom staking, signatures, genesis allocation, vesting and reorganization logic.
- Independent review of the prototype difficulty adjustment, realistic network time handling, attack/hashpower analysis and miner interoperability.
- Production-quality bounded P2P transport, hostile-input fuzzing, DoS/Sybil/partition handling and recovery under disk exhaustion.
- Reviewed grant and treasury custody, independent council members and enforceable grant-release controls. A lifetime founder charter is social policy; no special founder approval is needed to validate or mine a block.
- Safe jointly signed sponsorship, funded bounded faucet, protected mobile signing and recovery, private scoped miner pairing and revocation.
- At least four genuinely independent volunteer operators, two independently reachable peers, explicit endpoint approvals, and a measured multi-day soak. Multiple local processes do not satisfy operator independence.

No warning substitutes for these missing safeguards. Do not use real money, real seed phrases, purchased mining equipment, token sales or paid cloud services for this prototype.

## Resource and trust limits

Local HTTP synchronization is a development transport, not a public P2P protocol or light-client proof system. A CLI wallet is not an Android/iOS application. Reading balances from an API is trusting that node; a state hash by itself is not a mobile light-client security proof.

SQLite block replay favors inspectability over scalability. State snapshots, replay and hard ceilings need independent stress testing before raising their limits. The prototype's easy target ceiling and unreviewed retarget remain trivially attackable and cannot protect valuable assets. Python integer arithmetic avoids machine overflow, but consensus must still reject malformed types, oversized values and out-of-range amounts.

Follow the final implementation's API notes and independent review for exactly which features and limits are present. Missing functionality must stay disabled rather than simulated as working security.
