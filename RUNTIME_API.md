# Runtime and CLI

Use `python3 -m samanvay` from the source directory. An optional installed console entry point is named `samanvay`. The source-run path is the one tested here.

## Persistence and forks

`Chain(path, config)` creates a WAL SQLite block DAG. The complete pinned config commitment and deterministic genesis identify the database. Opening with another profile/config fails. Cached states and cumulative work are reconstructed by replay on startup; invalid stored blocks fail closed. Cached state is not authoritative.

APIs: `tip`, `get(hash)`, `blocks(limit)`, `state()`, `add_block(block)`, `mine(miner, transactions=(), timestamp=None)`, and `close()`. Cumulative target-derived work is stored as decimal TEXT and compared as Python integers; genesis work is zero. A work tie uses the smaller tip hash. Every accepted block is validated against its own parent branch, with branch ancestors supplied for median time. Insert plus canonical-path update is one SQLite transaction. Reorganizations select the already validated branch state, rolling back orphan transfers/locks/claims without a founder decision.

The local runtime allows at most 10,000 DAG blocks, 8 MiB serialized state and 128 MiB logical serialized block-plus-cache data. Actual SQLite/WAL physical usage has additional overhead. Consensus has its own stricter typed schemas and resource ceilings; hitting any ceiling rejects further blocks. Full-state snapshots and replay are deliberately a prototype, not a scalable pruning design.

## Commands

Global flags precede the command: `--db PATH`, `--profile devnet|rules`.

```text
keygen --out wallet.json
address --key wallet.json
init
status
mine --miner ADDRESS [--count 1..1000] [--tx signed.json ...] [--timestamp INTEGER]
transfer --key wallet.json --to ADDRESS --amount USAMV --out signed.json
send --key wallet.json --to ADDRESS --amount USAMV --out signed.json
lock --key wallet.json --amount USAMV --out signed.json
exit --key wallet.json --lock-id TXID --out signed.json
withdraw --key wallet.json --lock-id TXID --out signed.json
claim --key wallet.json --lock-id TXID --epoch INTEGER --reward USAMV --out signed.json
build --json unsigned.json --out copy.json
sign --key wallet.json --tx unsigned.json --out signed.json
submit --block mined-block.json
sync --peer http://127.0.0.1:8765
serve [--host 127.0.0.1] [--port 8765]
```

Transaction builders also accept `--fee`, `--expiry`, `--nonce`; defaults use zero local fee, the current account nonce and a bounded expiry. Exact signed `network_id` is added automatically. `send` is a synonym for building a signed transfer file: it does NOT broadcast. `build` merely copies a JSON payload and does not validate a transaction. `sign` signs an explicitly supplied payload; every node still rejects invalid transactions. `submit --tx` is an alias for `submit --block`, not a transaction mempool.

Mining is foreground and finite. `mine --tx` includes each provided signed transaction in its first block only, preventing accidental repeat submission with `--count`. Transactions are not automatically relayed. Claims are explicit per-epoch signed operations, never a guaranteed return. Wallet files are unencrypted owner-only local test fixtures; no seed/mobile recovery system exists.

## Local HTTP

The server supports bounded `GET /status`, paginated `GET /blocks?offset=N`, and `POST /blocks` or `/submit` with a complete mined block. It has no key retrieval, signing, mining-control or general admin-RPC route. Status returns exact network/config/genesis commitments; sync checks these before importing blocks. Only block objects—not private keys or cached full states—are returned in block pages.

Only literal loopback peers/binds are accepted. Public addresses, DNS names, redirects, HTTPS URLs, credentials, query strings on peer base URLs, and mismatched networks are rejected. The demonstrated listener uses IPv4 loopback; no IPv6 connectivity claim is made. Requests require one Content-Length and application/json; duplicate JSON members, nonfinite constants, oversized bodies, invalid blocks and unsupported paths fail closed. Pagination, byte limits, socket timeouts and eight concurrent handler slots bound the transport. This is not public-network DoS protection or a reviewed P2P stack.

`serve` starts only when explicitly invoked and stops with Ctrl+C; it is a normal foreground server, not an installed service. Tests/demo start bounded temporary loopback servers and shut them down before exiting. No server remains running after this delivery.

### Snapshot-bound synchronization

`GET /blocks` returns `blocks`, `next_offset` and a `snapshot` SHA-256d commitment over all stored block hashes in height/hash order, joined with newline separators and no trailing newline. Subsequent page requests send `snapshot=TOKEN` alongside `offset=N`. A source DAG change invalidates the token and returns HTTP 409 rather than silently shifting page boundaries. The server does not retain old snapshots. Stop local mining and retry sync if the source changes; continuous-mining availability is not promised.

The hardened client rejects empty/repeated/skipped pages, invalid or changed snapshots, oversized cumulative block counts and malformed HTTP response framing. At completion it recomputes the received snapshot and checks the advertised tip's hash, height and cumulative work against locally validated data. A failed batch may leave its valid prefix imported; no full-batch atomicity is claimed. No snapshot commitment authenticates a peer or proves that an unknown external chain is complete.

## Offline independent-machine checks

`python3 examples/operator_rehearsal.py` runs a finite four-process fork/sync/restart rehearsal on one machine. It creates temporary databases and loopback listeners, verifies convergence and supply, then stops its workers. This does not establish operator independence.

`examples/offline_exchange.py` exports/imports bounded block-only files for manual exchange between volunteers, without opening any listener. See `docs/PRIVATE_OPERATOR_CHECK.md` for the exact commands, evidence checklist and limitations. Actual volunteers, private exchange and cross-machine results remain pending.
