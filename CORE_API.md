# Local tSAMV protocol and Python API

This is new original experimental code, not a qualified Bitcoin-derived client. It uses an account ledger and Ed25519. Both pinned profiles are disposable **tSAMV**, never mainnet. All configured values are committed to genesis and every block header. Custom runtime consensus overrides are rejected.

## Economic accounting

One tSAMV is 1,000,000 usamv. Cap: 10,000,000,000,000,000 usamv. Genesis issues 6.5B tSAMV: founder 3B unreleased, developer 2B frozen, treasury 1B frozen, distribution 0.5B frozen. Frozen balances have no spending/grant controller in this milestone and cannot transact or stake. This is conservative disabled custody, not a council implementation.

The founder address is derived from `TEST_ONLY_FOUNDER_PRIVATE_KEY = '00' * 32`, a deliberately PUBLIC test fixture. Anyone can spend its released test funds. It must never be reused for a valuable network. No founder key is required to mine, validate, or adopt a fork. Lifelong leadership is a proposed social charter, not implemented identity/governance enforcement.

The unchanged finite schedule uses 1,051,200-block eras and initial subsidy 1,664,764,079 usamv. Nested cumulative buckets implement the proposed 60/30/10 miner/staker/founder allocation, including the one-unit-era rounding correction. No admin mint, stake multiplier, tail emission or skipped-reward catch-up exists. Ordinary fees go entirely to the miner and do not increase issued supply.

`consensus.supply_total(state)` verifies:

```text
issued = balances + pending miner/founder outputs
       + unreleased founder initial principal + locked principal + reward_pool
```

Frozen pools are already inside balances. Entitlements and dust are already inside reward_pool. Neither is counted twice. This equality is checked after every transition and on parent state validation.

## Heights and epochs

Genesis height is 0; first subsidy-bearing block is 1. Epoch `e` covers `e*B+1` through `(e+1)*B`, inclusive. A lock confirmed in an epoch first participates at the next epoch start. Eligible weights are snapshotted **before transactions** at that start and held constant. Each block with positive snapshot weight issues exactly its scheduled staking share to the restricted pool. Empty epochs permanently skip their staking issuance. At epoch end, each lock receives `floor(budget*weight/total_weight)`. Dust stays in the pool with no claimant or sweep route.

Claims first become includable at `epoch_end + coinbase_maturity`. Claim records retain ownership independently of lock objects, so principal withdrawal does not erase earned rewards. Partial signed claims are permitted up to the original entitlement, never beyond it. No claim mints new coins.

A lock must remain active seven complete epochs. Exit requests are permitted during the last required active epoch; removal occurs at the next eligible boundary. Seven further full, non-rewarding unbond epochs pass before withdrawal. The helper functions define the exact earliest heights.

Founder principal releases zero through the cliff height, then `floor(3B * elapsed/period)` cumulatively, with first tranche at `cliff+1` and final tranche at `cliff+period`. Founder bonuses mature after the maximum of ordinary coinbase maturity and their configured extra delay. Miner fees and subsidy are both matured. Only released available balances can lock.

| Setting | Local devnet | Rules-timing local profile |
|---|---:|---:|
| Network ID | samanvay-local-devnet-v4 | samanvay-local-rules-v4 |
| Epoch blocks | 12 | 720 |
| Coinbase maturity | 3 | 100 |
| Active / unbond epochs | 7 / 7 | 7 / 7 |
| Founder cliff / linear period | 20 / 80 blocks | 262,800 / 1,051,200 blocks |
| Founder bonus delay | 20 blocks | 262,800 blocks |
| Target spacing / retarget interval | 1 second / 12 blocks | 600 seconds / 2,016 blocks |
| Maximum target change per retarget | 4× easier or harder | 4× easier or harder |

The rules-timing profile is not a public network. The bounded node is unsuitable for running a lifetime issuance/vesting simulation; arithmetic helpers test remote-era boundaries without mining millions of blocks. Block times are not guaranteed calendar durations.

## Cryptography and transaction schema

`crypto.generate_key()`, `public_key(private_hex)`, `address(public_hex, network='tSAMV')`, `sign_transaction(tx, private_hex)`, `verify_transaction_signature(tx)`, `txid(tx)`, and `canonical(obj)` provide local Ed25519 signing and canonical sorted JSON. `txid` and header hashes use SHA-256d. Addresses are prototype `s` plus 39 lowercase hex characters, not a reviewed checksummed wallet encoding.

Every signed transaction requires integer `version=1`, `network='tSAMV'`, exact `network_id`, supported `type`, `sender`, integer `nonce`, integer height `expiry`, integer `fee`, `public_key`, and `signature`. All fields other than public_key/signature are signed. Public-key binding is checked against sender. Replay isolation depends on signed network_id as well as nonce/expiry. Unknown fields are rejected.

Type-specific fields:

- `transfer`: positive integer `amount`, valid `to` address.
- `lock`: integer `amount >= 1,000,000`.
- `exit`, `withdraw`: `lock_id` (64 lowercase hex).
- `claim`: `lock_id`, integer `epoch >= 0`, positive integer `reward`.

An optional `amount=0` is accepted on exit/withdraw/claim; any nonzero amount is rejected. Only one transaction per sender per block is currently allowed. Zero fees are a local experimental policy, not sponsorship or a free-forever service. Transactions have no automatic relay/mempool; miners explicitly include signed files.

## Blocks and validation API

```python
params.default_config(profile='devnet'|'rules') -> dict
consensus.initial_state(config) -> dict
consensus.genesis(config) -> block
consensus.block_hash(block) -> str
consensus.block_work(block) -> int
consensus.make_block(parent, state, transactions, miner_address, config,
                     timestamp=None, ancestors=None) -> mined_block
consensus.apply_block(parent, state, block, config, ancestors=None) -> new_state
consensus.supply_total(state) -> int
```

Parameter helpers: `subsidy`, `cumulative`, `split`, `epoch_of`, `epoch_start`, `epoch_end`, `activation_height`, `exit_effective_height`, `withdraw_height`, `claim_height`, `epoch_budget`.

Header schema is exact: version, height, parent, timestamp, nonce, miner, txids, network_id, target, config_digest, state_root. State_root is committed inside the mined header and duplicated at block top level; both must agree. The supplied parent state must hash to its parent header commitment. No `_skip_*` or caller-controlled validation bypass is accepted.

Both profiles start with the same deliberately easy proof-of-work limit `(2**248)-1`; the target can never become easier than that limit. The prototype retargets only after a complete window of mined blocks: for the next block after each window, it compares the first and last timestamps in the committed window with `(interval-1) * target_spacing`, scales the previous target by actual/expected elapsed time using integer floor arithmetic, limits each change to at most 4× easier or harder, and clamps the result to `[1, initial_target]`. The first window uses the initial target. Window timestamps live in committed chain state and reset at each window boundary. Each block's target is checked exactly, and chain choice remains valid cumulative target-derived work; staking weight and founder permission do not select blocks. This changes PoW target/work only: the existing issuance schedule, staking budget, reward accounting and 10B supply ceiling are unchanged. Timestamp rules still require nondecreasing parent time, strictly greater than the median of up to 11 prior branch headers, and no more than 7,200 seconds into the validating node's future. The one-second devnet spacing is only for accelerated local tests.

This is a bounded implementation foundation, **not a reviewed production DAA**. The target is intentionally easy, the timestamp/retarget choices have not had independent consensus or attack analysis, the rules profile is still locally bounded, and modest hashpower can rewrite either profile. No public mining or valuable use is safe. The profile parameters and replay domains changed to v4; old v3 prototype databases do not match the new genesis/config and must not be reused.

The runtime always obtains median-time ancestors from the stored parent branch. Supplied ancestor lists in the low-level API must be connected and end at the claimed parent; the most recent 11 entries are used. Omitting context retains the low-level parent-only fallback for isolated transition tests, not a full-chain validation guarantee. Difficulty history is separately carried in the committed parent state. Mining materializes transaction iterables once so generator-based callers cannot lose transactions between commitment and execution.

## Resource ceilings and limitations

Per profile: 1,000,000-byte blocks; 1,000 transactions per block; 100,000 bytes per transaction; 4,096 accounts; 512 current locks; 4,096 lifetime rewarded lock IDs; 1,024 settled/empty epochs; 20,000 pending outputs; 8 MiB serialized state; height 10,000. Runtime additionally stops at 10,000 total DAG blocks and 128 MiB logical block-plus-cache bytes (not an exact physical-disk bound). Hitting a ceiling stops further acceptance; this disposable prototype requires a disclosed reset, not an admin override.

Only epoch boundaries iterate locks to establish/settle weights; nevertheless complete state copying, hashing, conservation checks and per-block cached snapshots remain expensive. This is NOT a scalable authenticated-claim/pruning design. Full replay validates stored blocks after restart, but fault injection, disk exhaustion, extensive fuzzing and independent security audit remain missing.
