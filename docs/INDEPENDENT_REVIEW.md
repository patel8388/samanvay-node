# Internal consensus behavioral review — initial milestone

**Scope:** `samanvay/consensus.py`, `params.py`, `crypto.py`, `CORE_API.md`, and the behavioral suite in `tests/test_consensus.py`. This review owns only the consensus behavioral tests and this document; runtime/integration tests were not modified.

This historical review was produced within the development workflow, not by an external security auditor or independent volunteer operator. Subsequent hardening and current totals are recorded in `HARDENING.md` and `../test-results.txt`.

## Test milestone

Commands executed from `/workspace/samanvay-node`:

```text
python3 -m unittest tests.test_consensus -v
python3 -m unittest discover -s tests -v
```

Recorded initial result: **14 consensus tests passed; 32 repository tests passed.** The consensus fixture starts from the actual deterministic genesis/initial state and obtains test spending funds exclusively through a cached chain of mature mined coinbase outputs. It does not inject synthetic balances or alter parent commitments. Each signed transaction includes the exact profile `network_id`; malicious field variants are freshly signed so failures exercise address/domain/schema validation rather than merely stale signatures.

The suite covers nested 60/30/10 reference vectors and randomized arithmetic, exact 6.5B genesis accounting, deterministic genesis/config/state-root commitments, parent/state linkage, exact-target PoW and target-based work, malformed address/network/nonce/signature/schema/type input, rejected `_skip_root`/`_skip_pow` markers, delayed founder vesting and bonuses, pending miner maturity, non-minting fees, safe `None` exits, early claims, profile replay, epoch snapshot timing, staking-pool dust, seven-active/seven-unbond lifecycle, post-principal-withdraw claim ownership, complete reward claim, and supply conservation.

## Resolved requirements observed in the updated core

- **Epoch budget:** `params.epoch_budget()` computes the nested staking 30% bucket delta, rather than the whole cumulative subsidy. Independent vectors pass.
- **Genesis:** deterministic state/root with exactly 6.5B issued: 3B unreleased founder allocation, 2B frozen developer, 1B frozen treasury, and 0.5B frozen distribution. Genesis config digest and state root are committed.
- **Validation:** parent height/state linkage, exact header schema, network/config digest/target, state root, PoW, malformed transaction fields, signature, nonce/expiry, unsupported type checks, exact transaction `network_id`, and profile replay rejection are exercised and pass.
- **Vesting and maturity:** founder principal is not immediately liquid; first founder release occurs after the cliff, founder bonuses and miner coinbase are pending, and early claims are rejected.
- **Staking lifecycle:** funding is allocated per block to the fixed epoch snapshot before transactions; integer dust remains reserved in `reward_pool`; empty epochs are skipped; claims mature only at the recorded epoch maturity.
- **Lifecycle:** the accelerated profile still uses seven active and seven unbond epochs. The full lock/exit/withdraw vector passes, including a claim submitted after principal withdrawal and fully consuming that entitlement.
- **Fees and supply:** fees transfer existing funds to the miner’s pending output without inflating `issued`; `consensus.supply_total()` accounts balances, pending outputs, unreleased founder funds, locked principal, and reward pool exactly once.
- **Timestamp behavior:** test helpers use `make_block(..., timestamp=None)`, allowing the core’s automatic monotonic timestamp behavior rather than repeatedly forcing a constant wall-clock timestamp.

## Final disposition

**The initial behavioral suite passed for that local milestone.** The owned consensus suite and repository suite passed without core modifications at that stage; later hardening does modify the core. This remains a disposable local-only implementation; public deployment/value use remains prohibited by `RELEASE_GATES.md`.
