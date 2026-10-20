"""Manual, file-only exchange of bounded versioned block-DAG bundles.

Bundles contain only blocks (never wallets, keys, or state caches).  Import is
intentionally prefix-committing: blocks accepted before a later error remain
in the local Chain database; callers should inspect the exception and retry
with a clean database if all-or-nothing behavior is required.

CLI::
    python examples/offline_exchange.py --db PATH export --out PATH
    python examples/offline_exchange.py --db PATH import --input PATH
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from samanvay import consensus, crypto, params
from samanvay.chain import Chain, MAX_DAG_BLOCKS
from samanvay.server import _strict_json

MAX_BUNDLE_BYTES = 32 * 1024 * 1024
BUNDLE_VERSION = 1


def _identity(chain: Chain) -> dict[str, str]:
    config_digest = crypto.sha256d(crypto.canonical(chain.config))
    return {
        "network_id": chain.config["network_id"],
        "config_digest": config_digest,
        "genesis": consensus.block_hash(consensus.genesis(chain.config)),
    }


def _read_bundle(path: os.PathLike[str] | str) -> dict:
    p = Path(path)
    if not p.is_file():
        raise ValueError("input bundle is not a regular file")
    try:
        size = p.stat().st_size
    except OSError as exc:
        raise ValueError("cannot stat input bundle") from exc
    if size > MAX_BUNDLE_BYTES:
        raise ValueError("bundle resource limit")
    try:
        with p.open('rb') as handle:
            raw = handle.read(MAX_BUNDLE_BYTES + 1)
        if len(raw) > MAX_BUNDLE_BYTES:
            raise ValueError("bundle resource limit")
        obj = _strict_json(raw)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError,
            RecursionError) as exc:
        raise ValueError("malformed bundle JSON") from exc
    if not isinstance(obj, dict):
        raise ValueError("bundle must be an object")
    return obj


def export_bundle(chain: Chain, output: os.PathLike[str] | str) -> int:
    """Write a deterministic snapshot, refusing to overwrite *output*."""
    out = Path(output)
    with chain.lock:
        rows = chain.db.execute(
            "SELECT block FROM blocks ORDER BY height ASC, hash ASC"
        ).fetchall()
        if len(rows) > MAX_DAG_BLOCKS:
            raise ValueError("DAG block limit")
        blocks = [json.loads(row[0]) for row in rows]
        tip = chain.tip
        bundle = {
            "version": BUNDLE_VERSION,
            "type": "samanvay-offline-block-dag",
            "identity": _identity(chain),
            "tip": {"height": tip["height"], "hash": tip["hash"],
                    "work": str(tip["work"])},
            "blocks": blocks,
        }
        data = crypto.canonical(bundle)
    if len(data) > MAX_BUNDLE_BYTES:
        raise ValueError("bundle resource limit")
    # O_EXCL provides the refusal-to-overwrite guarantee without a TOCTOU gap.
    try:
        fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
    except FileExistsError as exc:
        raise ValueError("refusing to overwrite output") from exc
    except OSError as exc:
        raise ValueError("cannot write output bundle") from exc
    return len(blocks)


def _validate_envelope(bundle: dict, chain: Chain) -> list:
    if set(bundle) != {"version", "type", "identity", "tip", "blocks"}:
        raise ValueError("malformed bundle envelope")
    if type(bundle["version"]) is not int or bundle["version"] != BUNDLE_VERSION:
        raise ValueError("unsupported bundle version")
    if bundle["type"] != "samanvay-offline-block-dag":
        raise ValueError("wrong bundle type")
    identity = bundle["identity"]
    if (not isinstance(identity, dict) or set(identity) !=
            {"network_id", "config_digest", "genesis"}):
        raise ValueError("malformed bundle identity")
    if identity != _identity(chain):
        raise ValueError("network/config/genesis identity mismatch")
    tip = bundle["tip"]
    if (not isinstance(tip, dict) or set(tip) != {"height", "hash", "work"}
            or type(tip["height"]) is not int or tip["height"] < 0
            or not isinstance(tip["hash"], str) or not consensus.HASH.fullmatch(tip["hash"])
            or not isinstance(tip["work"], str)):
        raise ValueError("malformed advertised tip")
    try:
        if int(tip["work"]) < 0 or str(int(tip["work"])) != tip["work"]:
            raise ValueError
    except (ValueError, TypeError, OverflowError):
        raise ValueError("malformed advertised work")
    blocks = bundle["blocks"]
    if not isinstance(blocks, list) or not blocks or len(blocks) > MAX_DAG_BLOCKS:
        raise ValueError("invalid or oversized block list")
    seen = set()
    for block in blocks:
        if not isinstance(block, dict):
            raise ValueError("malformed block")
        digest = consensus.block_hash(block)
        if digest in seen:
            raise ValueError("duplicate block")
        seen.add(digest)
    if tip["hash"] not in seen:
        raise ValueError("advertised tip missing")
    return blocks


def import_bundle(chain: Chain, source: os.PathLike[str] | str) -> int:
    """Validate and add blocks in bundle order; earlier additions remain on error."""
    bundle = _read_bundle(source)
    blocks = _validate_envelope(bundle, chain)
    advertised = bundle["tip"]
    accepted = 0
    with chain.lock:
        for block in blocks:
            digest = consensus.block_hash(block)
            known = chain.get(digest)
            if known is None:
                chain.add_block(block)  # Full consensus/state validation.
                accepted += 1
            else:
                if known["block"] != block:
                    raise ValueError("duplicate hash with altered block")
            row = chain.get(digest)
            if row is None:
                raise ValueError("block was not retained")
            expected_height = block["header"].get("height")
            if row["height"] != expected_height:
                raise ValueError("false block height")
        tip = chain.get(advertised["hash"])
        if (tip is None or tip["height"] != advertised["height"]
                or tip["work"] != int(advertised["work"])):
            raise ValueError("false advertised tip height/work")
    return accepted


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="offline Samanvay block-DAG exchange")
    parser.add_argument("--db", required=True, help="local SQLite database path")
    sub = parser.add_subparsers(dest="command", required=True)
    exp = sub.add_parser("export")
    exp.add_argument("--out", required=True)
    imp = sub.add_parser("import")
    imp.add_argument("--input", required=True)
    args = parser.parse_args(argv)
    chain = Chain(args.db, params.default_config())
    try:
        count = export_bundle(chain, args.out) if args.command == "export" else import_bundle(chain, args.input)
    finally:
        chain.close()
    print(json.dumps({"blocks": count, "command": args.command}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"offline exchange error: {exc}", file=sys.stderr)
        raise SystemExit(2)
