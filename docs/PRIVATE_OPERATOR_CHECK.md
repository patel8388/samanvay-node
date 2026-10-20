# Private operator check: disposable tSAMV only

The next real-world gate needs **at least four genuinely independent volunteer operators**. They have not been recruited or tested by this source change. Four processes on the development computer are only a rehearsal. No public listener, router change, paid service or mainnet deployment is authorized.

## What volunteers can test without public endpoints

Each volunteer uses their own existing computer, checks the same source integrity manifest, runs the verification suite, and creates a fresh disposable database. Volunteers exchange **block-only JSON files** through an existing private channel chosen by the owner. Each computer validates signatures, proof of work, state transitions and chain choice locally. No HTTP port needs to be reachable across computers.

Do not send wallet files, private keys, real seed phrases or databases. Block bundles contain public test addresses, transactions and ledger history, so they are not confidential wallet backups. This workflow checks cross-machine consensus and manual partition recovery; it does **not** qualify internet P2P, latency, Sybil resistance or denial-of-service protection.

## Start separately on each computer

Requirements remain Python 3.12+ and the pinned dependency in `requirements.txt`. Only use already-authorized resources; do not purchase hosting or mining services. From the extracted source directory:

```bash
sha256sum -c SHA256SUMS
./verify.sh
mkdir -p .local
python3 -m samanvay keygen --out .local/operator.json
python3 -m samanvay --db .local/operator.sqlite3 init
python3 -m samanvay address --key .local/operator.json
```

Copy the displayed test address into the following command. Have different volunteers choose 4, 6, 8 and 10 blocks respectively so their disconnected branches differ. These are tiny, easy-target research runs, not hashpower benchmarks.

```bash
python3 -m samanvay --db .local/operator.sqlite3 mine --miner TEST_ADDRESS --count 4
python3 examples/offline_exchange.py --db .local/operator.sqlite3 export --out .local/round-1.json
```

The exporter refuses to overwrite a file. Use a fresh filename for each round. It exports the stored fork DAG, not just the selected tip, and never exports a wallet or cached state.

## Exchange, validate, compare

Each volunteer privately receives the other operators' bundles and imports each into their **disposable** local database:

```bash
python3 examples/offline_exchange.py --db .local/operator.sqlite3 import --input RECEIVED_BUNDLE.json
python3 -m samanvay --db .local/operator.sqlite3 status
```

Imports are bounded and revalidate blocks locally. A rejected bundle can leave an already-validated prefix in the disposable database; it does not mean the full bundle was accepted. Keep the error, preserve the input for review, and do not treat partial import as successful qualification. Never import unreviewed material into a database containing anything you value.

After all four have imported all round-one bundles, compare the complete selected tip hash, block state root, cumulative work and issued supply. Equal-height branch ties use the deterministic hash tie-breaker. Everyone should converge even if they receive bundles in different orders. Stop the CLI and run `status` again to verify disk replay produces the same result.

For a second round, disconnect again. Two operators mine competing continuations of different lengths. Exchange those new bundles in different orders and repeat the comparison. Import the same bundle twice: the second import should report no newly accepted blocks. Preserve evidence of any rejection or divergence rather than resetting it away.

## Record evidence, not just “works”

For each volunteer, collect a pseudonymous operator label, OS/CPU architecture, Python and dependency versions, verified source/archive checksum, verification output, bundle checksums, import output, and final selected tip hash, height, work and state root before and after restart. Record errors, approximate execution time, peak memory and database growth if available. Do not publish personal device identifiers or secret keys.

A successful round requires independent machines and operators, matching source identities, passing suites, identical final state commitments after different import orders, correct longer-work fork recovery, repeat-import idempotence and restart replay. Any unexplained divergence blocks advancement.

## What remains blocked

Offline success is not a public-testnet approval or a security audit. Reviewed difficulty adjustment, qualified architecture, hostile-input fuzzing, resource/exhaustion recovery, safe custody, and a later separately authorized network/soak phase remain outstanding. The fixed easy target is trivially rewriteable. Test balances have no value, redemption or mainnet entitlement.

The owner must provide willing volunteers and agree on their private exchange channel before actual independent testing can be claimed. Do not expose this prototype publicly to make the volunteer step easier.
