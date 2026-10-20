# Hardened local node; private operator checks next

The local no-value node now has stricter consensus-context, persistence and peer-input checks. The finite four-process rehearsal converged after competing forks, conserved supply, repeated sync without duplicate acceptance, and reopened with identical replayed state. This is evidence for the local prototype—not a public-testnet approval, an external audit or independent-operator qualification.

## What changed

**Consensus inputs.** Mining materializes transaction iterables once, preserving generator-based signed transactions. Supplied ancestor context must be connected and end at the claimed parent. The runtime supplies its actual parent branch; the low-level parent-only fallback remains for isolated transition tests.

**Database recovery.** Startup replay checks persisted row/header height and parent linkage, including the genesis row's intentional empty database parent and zero work. Cache reconstruction and selected-path changes are transactional: a later invalid row rolls back earlier repairs rather than leaving a partly rebuilt database. Cumulative work and states are still derived by validation, not trusted cached claims.

**Peer transport.** Requests and responses have stricter content-length, transfer-encoding and JSON framing checks. Page snapshots bind the ordered stored block set. Sync rejects empty, skipped, repeated, changed and oversized page sequences; recomputes the complete received snapshot; and checks the peer's advertised tip against locally validated height and cumulative work. A real 130-block transfer exercises more than one page.

**Manual private exchange.** A bounded, versioned block-only export/import tool supports volunteer tests without exposing a listener. It checks the pinned network/config/genesis identity and validates received blocks. Valid prefixes can remain after a later import error; imports are not whole-bundle atomic. No wallets, private keys or cached states are exported.

## What actually passed

`test-results.txt` contains the current complete verification totals. Added regressions cover valid and invalid transaction generators, ancestor substitution, persisted linkage/genesis-work tampering, replay rollback, hostile response framing, false advertised tips, page attacks, real multipage sync, offline bundle integrity/bounds and exact source-run CLI exchange.

The original 182-block staking/transfer demo passed again; see `demo-results.json`. The four-process rehearsal starts at heights 4, 6, 8 and 0, imports all competing branches, and converges at height 8 with the same state root. Two shorter mined branches reorganize. Repeated sync accepts zero new blocks, and restart replay is identical; see `operator-rehearsal-results.json`.

These processes run on **one computer**. Actual independent operators tested: **zero**. No real-value funds, paid services, public endpoints or mainnet deployment were used. All temporary local listeners were stopped.

## Debian 12 preparation, not installation

The setup materials target the owner's 1-vCPU, 1-GB-RAM, 10-GB-SSD VPS, but no SSH access was supplied and no VPS command was run. The bundle is source and preparation scripts, not a provisioned server or self-contained binary runtime.

[Debian's official Bookworm package record](https://packages.debian.org/bookworm/python3) lists Python 3.11 as the default. This project still requires Python 3.12+. The bundle must fail closed until an appropriate existing interpreter, virtual-environment support and approved offline dependencies are available. It must not replace the system Python, download packages or compile a runtime automatically. The scripts and tests run in the development environment; no claim of Debian/VPS execution or measured 1-GB fitness is made.

## Next gate

Use `PRIVATE_OPERATOR_CHECK.md` with at least four genuinely independent volunteers and their own existing computers. Collect matching source identities and final tip/state commitments across different exchange orders, competing continuations and restarts. The owner must identify willing volunteers and an existing private exchange channel. No recruitment, messages or cross-machine testing has occurred yet.

A fixed easy target remains trivially rewriteable. Difficulty adjustment, qualified architecture, external security review, sustained hostile-input fuzzing, disk/resource exhaustion testing, production transport and custody remain blockers. Successful offline tests would not authorize a public endpoint; public reachability requires a later explicit decision and additional release gates.
