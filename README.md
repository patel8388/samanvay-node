# Samanvay: runnable local mining and staking node

**Milestone 0.1 — disposable tSAMV only. No value, redemption, mainnet entitlement or public launch.**

This repository now contains executable chain software, not just a plan or reward calculator. It implements a small independent local ledger with real SHA-256d Proof-of-Work, signed transfers, native rewarded locks, SQLite persistence and local peer synchronization. It is new Python source, not the unsuitable NOVA archive.

It is **not** the completed public Samanvay network. The planned maintained Bitcoin-derived base has not been qualified; this account-based prototype is a deliberate research implementation. Do not use real funds, real seed phrases or purchased mining services.

## Developers and volunteers welcome

We are seeking Python contributors, protocol and security reviewers, and **four genuinely independent volunteer operators** for bounded offline experiments. Participation is voluntary and unpaid unless separately agreed; there are no token grants, guaranteed rewards or future allocations promised for contributing.

Start with [CONTRIBUTING.md](CONTRIBUTING.md), choose a [help-wanted issue](https://github.com/patel8388/samanvay-node/issues?q=is%3Aissue%20is%3Aopen%20label%3A%22help%20wanted%22), or [introduce your volunteer interest](https://github.com/patel8388/samanvay-node/issues/new?template=volunteer.yml). Documentation and reproducibility tasks are suitable entry points. Difficulty adjustment, public networking and consensus changes require experienced design review; removing the loopback guard is **not** a starter task.

The human-driven [Paperclip coordination package](paperclip/samanvay-company/README.md) contains an importable project backlog; it has no agents, credentials, or automated execution settings.

Read the [threat model](docs/THREAT_MODEL.md), [security reporting policy](SECURITY.md) and [private operator check](docs/PRIVATE_OPERATOR_CHECK.md) before testing. Source publication is not authorization to expose a node on the internet.

## Run it now

Requirements: Python 3.12+ and `cryptography==50.0.2`. No API key, blockchain service or paid account is required. Electricity and machine time are not literally free. Use a disposable environment with no real keys or valuable data.

Clone and install into an isolated virtual environment (POSIX shell):

```bash
git clone https://github.com/patel8388/samanvay-node.git
cd samanvay-node
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

Then run:

```bash
python3 examples/local_demo.py
./verify.sh
```

The finite demo mines **182 real easy-target blocks**, funds two stakes from matured miner rewards, preserves one-usamv rounding dust, claims rewards, completes seven active plus seven unbond epochs, withdraws principal, claims another earned reward after withdrawal, and syncs a second local node to the same state. It shuts down its loopback server and deletes temporary keys/databases on exit. Example output is recorded in `demo-results.json`.

`verify.sh` runs syntax checks, the expanded node/hardening/setup-preparation suite, and the **27 original rule-calculation tests**. Exact current totals and outcomes are recorded in `test-results.txt`. Passing these finite tests is not a security audit, seven-day soak or proof of mainnet safety.

If the dependency is missing on another machine, install the pinned `requirements.txt` into that machine's own Python virtual environment. No dependency downloads or package installation are required to run in the development environment. An optional packaging configuration is included, but an independently rebuilt wheel or binary release has not been qualified.

## Current hardening and private setup preparation

The hardening pass checks supplied ancestor linkage, one-pass transaction iterables, transactional database replay, persisted linkage tampering, strict HTTP framing, snapshot-bound pagination and advertised-tip completeness. `python3 examples/operator_rehearsal.py` runs four local node processes through competing forks, repeated synchronization and restart replay. Recorded output is in `operator-rehearsal-results.json`; **independent operators tested: zero**.

`docs/PRIVATE_OPERATOR_CHECK.md` and `examples/offline_exchange.py` prepare bounded block-only file exchange between real volunteers, without public endpoints. Those volunteers and actual cross-machine results are still pending. `docs/HARDENING.md` records this pass and its limits.

`packaging/debian12/` contains the original preparation-only bundle for a 1-vCPU/1-GB/10-GB Debian 12 VPS. Its bundled status files predate the owner's subsequently reported VPS rehearsal; that report is not independent-operator or public-network qualification. Debian 12's default Python 3.11 does not meet this project's Python 3.12+ requirement; the bundle must stop safely until an appropriate interpreter and offline dependencies are available. No SSH access, firewall change, public bind, automatic startup or mainnet is included in this source publication.

## Mine and lock manually

All amounts below are integer **usamv**: `1 tSAMV = 1,000,000 usamv`.

```bash
mkdir -p .local
python3 -m samanvay keygen --out .local/miner.json
MINER=$(python3 -m samanvay address --key .local/miner.json | python3 -c 'import json,sys; print(json.load(sys.stdin)["address"])')
python3 -m samanvay --db .local/node-a.sqlite3 init
python3 -m samanvay --db .local/node-a.sqlite3 mine --miner "$MINER" --count 4
python3 -m samanvay --db .local/node-a.sqlite3 lock --key .local/miner.json --amount 1000000 --out .local/lock.json
python3 -m samanvay --db .local/node-a.sqlite3 mine --miner "$MINER" --tx .local/lock.json
python3 -m samanvay --db .local/node-a.sqlite3 status
```

This produces the lock at height 5, first eligible at height 13. The first eligible epoch ends at 24; its reward first becomes claimable at 27. These are accelerated test heights, not promised dates or APY. The demo covers the entire later exit/claim/withdraw flow automatically.

`transfer`, `send`, `lock`, `exit`, `withdraw`, and `claim` **write signed transaction files**, not payments sent by a website. Output JSON files are created owner-only and existing paths (including symlinks) are refused; choose a new path for each output. Explicitly include a file using `mine --tx signed.json`; transactions go only into the first block if `--count` is also supplied. There is no automatic mempool, transaction relay, wallet server or unattended miner. `submit --block block.json` accepts an already mined complete block. `claim` requires `--epoch`, `--lock-id`, and `--reward`; view exact entitlements in `status`. Use `python3 -m samanvay <command> --help` for each command.

### Encrypted local-wallet milestone

For an encrypted local test wallet, create a keystore and display its address:

```bash
python3 -m samanvay wallet create --out .local/wallet.json
python3 -m samanvay address --key .local/wallet.json
```

The CLI prompts twice for a new passphrase (minimum 12 UTF-8 bytes), never accepts it as a command-line argument, and prompts again when the encrypted wallet is opened for signing. The new file uses a fixed Scrypt KDF profile and AES-256-GCM, is created with owner-only permissions (`0600`), and refuses to overwrite an existing file. Existing signing commands accept either this encrypted format or the old plaintext test-key file.

This is **not audited production key custody or a mobile wallet**. The passphrase cannot be recovered; a copied keystore can be attacked offline; the host process can see decrypted key material while signing; and there is no hardware-backed storage, seed phrase, recovery service or mobile OS integration. The older `keygen` command intentionally remains a plaintext **disposable-test-only** workflow used by local examples. Do not put real assets or real wallet secrets into either format. See [wallet keystore notes](docs/WALLET_KEYSTORE.md).

The founder fixture key in source is deliberately public and must never be used for value.

## Try two local nodes

In one terminal, after preparing node A:

```bash
python3 -m samanvay --db .local/node-a.sqlite3 serve --host 127.0.0.1 --port 8765
```

In another terminal:

```bash
python3 -m samanvay --db .local/node-b.sqlite3 init
python3 -m samanvay --db .local/node-b.sqlite3 sync --peer http://127.0.0.1:8765
python3 -m samanvay --db .local/node-b.sqlite3 status
```

Stop the foreground server with Ctrl+C. Nothing automatically starts a daemon. Servers and clients reject non-loopback addresses and public binds. This is a small paginated HTTP development transport, **not** an internet P2P release. Two processes on one computer are not independent volunteer operators.

## Implemented and tested

- Own deterministic genesis, config commitments, separate local profile network IDs and signed replay domains.
- Exact 6.5B initial allocation and 10B maximum; the unchanged finite reward arithmetic uses nested 60/30/10 buckets without negative shares or extra staking minting.
- Real nonce/target SHA-256d mining with a bounded, deterministic prototype difficulty retarget; chain choice by valid cumulative target-derived work, never stake weight or founder permission.
- Ed25519 ownership checks, strict transaction/header schemas, integer-only amounts, nonce/expiry checks and committed state roots.
- Coinbase maturity, founder cliff/linear release, delayed founder bonuses; frozen developer/treasury/distribution custody.
- Native lock, next-epoch fixed weights, per-block restricted pool funding, empty-epoch skips, mature claims, exact dust backing, seven-active/seven-unbond exit and withdrawal.
- Atomic SQLite acceptance, persisted fork DAG, reorganization state rollback, restart replay, cache rebuild and corrupted-block rejection.
- Loopback-only bounded HTTP sync with network/genesis handshake, pagination, byte limits, timeouts and bounded connection workers.
- A finite two-node demo and regression coverage for adversarial signatures, replay, amounts, state injection, rewards, forks and persistence.

## Still missing before any public testnet

**Do not expose this software publicly or assign value to it.** The new local DAA is an experimental bounded foundation, not an independently reviewed or attack-qualified mining protocol; its starting target remains deliberately easy, and outside hashpower can rewrite this chain. Account/address design, full-state copying/hashing, reward-state retention, transport, cryptography integration and resource ceilings need independent review. No mature upstream PoW codebase has been pinned or security-audited.

Developer, treasury and distribution pools are deliberately frozen because reviewed independent council/grant custody is not implemented. That is not a working council, founder leadership system, faucet or grant-release feature. There is no founder master key or veto in consensus, but the lifetime leadership charter remains policy outside this code.

Native Android/iOS signing, protected mobile recovery, private remote-miner pairing, funded faucet and jointly signed sponsorship are **not implemented**. Zero-fee local transactions are not sponsored transactions. Neither a public endpoint nor independent volunteer operator has been established. No public soak, fuzzing campaign, external audit, legal review or production approval has occurred.

Hard state/storage/height ceilings intentionally stop this disposable network; they are not a sustainable lifetime chain. The `rules` profile retains proposed economic timing but is still locally bounded and insecure. Do not mistake it for mainnet or a full 124-year chain simulation.

## Files worth reading

- `CORE_API.md`: exact consensus schema, timings, invariants and resource ceilings.
- `RUNTIME_API.md`: runtime, command and transport behavior.
- `docs/INDEPENDENT_REVIEW.md`: behavioral test review, not an external audit.
- `docs/RELEASE_GATES.md`: remaining public-release blockers and architecture deviations.
- `test-results.txt`, `demo-results.json`: actual recorded test and demo results.
- `docs/PRIVATE_OPERATOR_CHECK.md`, `docs/HARDENING.md`: private qualification steps and hardening evidence.
- `packaging/debian12/README.md`: preparation-only VPS setup and unresolved prerequisites.
- `docs/reference/`: original plan, reference calculations and input checksums, preserved without modifying the original files.
- `config/`: pinned profiles and deterministic genesis artifacts.
- `SHA256SUMS`: source-release integrity manifest; not a security endorsement.

New source is MIT-licensed; the installed `cryptography` dependency has its own upstream licensing. Source checksums do not substitute for independent builds or security review.
