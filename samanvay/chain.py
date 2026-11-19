"""Bounded, replayable SQLite block DAG for the local Samanvay network."""
from __future__ import annotations
import json, sqlite3, threading
from pathlib import Path
from . import consensus, params, crypto

MAX_BLOCK_BYTES = 2 * 1024 * 1024
MAX_DAG_BLOCKS = 10_000
MAX_STATE_BYTES = 8 * 1024 * 1024
MAX_LOGICAL_DB_BYTES = 128 * 1024 * 1024
MAX_LIST = 1000

def _j(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def _loads(value): return json.loads(value)

def _config_commitment(config):
    # The complete ruleset is part of the local database identity.
    return crypto.sha256d(crypto.canonical(config))

class Chain:
    def __init__(self, path="samanvay.sqlite3", config=None):
        self.path = str(Path(path).expanduser())
        self.config = config or params.default_config()
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA foreign_keys=ON")
        try:
            self._schema()
            self._ensure_genesis()
        except Exception:
            self.db.close()
            raise

    def _schema(self):
        self.db.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL)")
        cols = {r[1]: r for r in self.db.execute("PRAGMA table_info(blocks)")}
        if cols and cols.get("work", (None, None, None))[2].upper() != "TEXT":
            # Old prototypes used INTEGER and could not represent 256-bit work.
            self.db.execute("ALTER TABLE blocks RENAME TO blocks_legacy")
            cols = {}
        self.db.execute("""CREATE TABLE IF NOT EXISTS blocks (
            hash TEXT PRIMARY KEY, parent TEXT NOT NULL, height INTEGER NOT NULL,
            work TEXT NOT NULL, block TEXT NOT NULL, state TEXT NOT NULL,
            main INTEGER NOT NULL DEFAULT 0)""")
        self.db.execute("CREATE INDEX IF NOT EXISTS blocks_height ON blocks(height)")
        self.db.execute("CREATE INDEX IF NOT EXISTS blocks_parent ON blocks(parent)")
        self.db.commit()
        if self.db.execute("SELECT 1 FROM meta WHERE k='config' ").fetchone() is None:
            self.db.execute("INSERT INTO meta(k,v) VALUES('config',?)", (_config_commitment(self.config),))
            self.db.commit()
        elif self.db.execute("SELECT v FROM meta WHERE k='config'").fetchone()[0] != _config_commitment(self.config):
            raise ValueError("genesis/config mismatch")

    def _ensure_genesis(self):
        with self.lock:
            expected = consensus.genesis(self.config)
            gh = consensus.block_hash(expected)
            rows = self.db.execute("SELECT hash,block FROM blocks WHERE height=0").fetchall()
            if not rows:
                state = consensus.initial_state(self.config)
                self.db.execute("INSERT INTO blocks VALUES(?,?,?,?,?,?,1)", (gh, "", 0, "0", _j(expected), _j(state)))
                self.db.commit()
            elif len(rows) != 1 or rows[0][0] != gh or _loads(rows[0][1]) != expected:
                raise ValueError("genesis/config mismatch")
            self._reindex()

    def _row(self, row):
        if not row: return None
        return {"hash": row["hash"], "parent": row["parent"], "height": row["height"],
                "work": int(row["work"]), "block": _loads(row["block"]), "state": _loads(row["state"])}
    @property
    def tip(self):
        return self._row(self.db.execute("SELECT * FROM blocks WHERE main=1 ORDER BY height DESC LIMIT 1").fetchone())
    def get(self, block_hash):
        return self._row(self.db.execute("SELECT * FROM blocks WHERE hash=?", (block_hash,)).fetchone())
    def blocks(self, limit=100):
        limit = max(1, min(int(limit), MAX_LIST))
        return [self._row(r) for r in self.db.execute("SELECT * FROM blocks ORDER BY height ASC, hash ASC LIMIT ?", (limit,))]

    def _branch(self, tip_hash):
        out=[]; cur=tip_hash
        while cur:
            row=self.get(cur)
            if row is None: raise ValueError("orphan DAG record")
            out.append(row); cur=row["parent"]
        return list(reversed(out))

    def _ancestors(self, tip_hash):
        out = []
        while tip_hash and len(out) < 11:
            row = self.get(tip_hash)
            if row is None:
                raise ValueError("orphan DAG record")
            out.append(row['block'])
            tip_hash = row['parent']
        return list(reversed(out))

    def _select_main(self):
        works = [(r['hash'], int(r['work'])) for r in
                 self.db.execute('SELECT hash,work FROM blocks')]
        best = min(works, key=lambda item: (-item[1], item[0]))[0]
        self.db.execute('UPDATE blocks SET main=0')
        self.db.executemany('UPDATE blocks SET main=1 WHERE hash=?',
                            [(r['hash'],) for r in self._branch(best)])

    def _reindex(self):
        rows = self.db.execute("SELECT * FROM blocks ORDER BY height ASC, hash ASC").fetchall()
        if len(rows) > MAX_DAG_BLOCKS: raise ValueError("DAG block limit")
        states = {}
        self.db.execute("BEGIN IMMEDIATE")
        try:
            for raw in rows:
                b = _loads(raw["block"]); h = raw["hash"]
                if consensus.block_hash(b) != h: raise ValueError("stored block hash mismatch")
                if (not isinstance(raw["height"], int) or raw["height"] < 0
                        or b.get("header", {}).get("height") != raw["height"]
                        or (raw["height"] != 0
                            and raw["parent"] != b.get("header", {}).get("parent"))):
                    raise ValueError("stored block linkage mismatch")
                if raw["height"] == 0:
                    state = consensus.initial_state(self.config); work = 0
                    if (raw["parent"] != "" or raw["work"] != "0"
                            or b != consensus.genesis(self.config)):
                        raise ValueError("invalid stored genesis")
                else:
                    parent = self.get(raw["parent"])
                    if not parent or parent["height"] != raw["height"]-1: raise ValueError("invalid stored parent")
                    ancestors = self._ancestors(parent["hash"])
                    state = consensus.apply_block(parent["block"], parent["state"], b, self.config, ancestors=ancestors)
                    work = parent["work"] + int(consensus.block_work(b))
                if len(_j(state).encode()) > MAX_STATE_BYTES: raise ValueError("state resource limit")
                self.db.execute("UPDATE blocks SET work=?,state=? WHERE hash=?", (str(work), _j(state), h))
                states[h] = work
            if not states: return
            best = min((h for h,w in states.items()), key=lambda h: (-states[h], h))
            self.db.execute("UPDATE blocks SET main=0")
            self.db.executemany("UPDATE blocks SET main=1 WHERE hash=?", [(r["hash"],) for r in self._branch(best)])
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def _add_block_locked(self, block):
        if not isinstance(block, dict): raise ValueError("block must be object")
        raw = _j(block).encode()
        max_block = int(self.config.get("max_block_bytes", MAX_BLOCK_BYTES))
        if len(raw) > min(max_block, MAX_BLOCK_BYTES): raise ValueError("block resource limit")
        txs = block.get("transactions")
        if not isinstance(txs, list) or len(txs) > int(self.config.get("max_transactions", 1000)): raise ValueError("transaction limit")
        h = consensus.block_hash(block)
        with self.lock:
            existing = self.get(h)
            if existing:
                if existing['block'] != block:
                    raise ValueError('duplicate hash with altered block envelope')
                return h, False
            if self.db.execute("SELECT COUNT(*) FROM blocks").fetchone()[0] >= MAX_DAG_BLOCKS: raise ValueError("DAG block limit")
            parent_hash = block.get("header", {}).get("parent", "")
            parent = self.get(parent_hash)
            if not parent: raise ValueError("unknown parent")
            ancestors = self._ancestors(parent_hash)
            state = consensus.apply_block(parent["block"], parent["state"], block, self.config, ancestors=ancestors)
            if len(_j(state).encode()) > MAX_STATE_BYTES: raise ValueError("state resource limit")
            logical = self.db.execute('SELECT COALESCE(SUM(length(block)+length(state)),0) FROM blocks').fetchone()[0]
            if logical + len(raw) + len(_j(state).encode()) > MAX_LOGICAL_DB_BYTES:
                raise ValueError('local logical database byte limit')
            work = parent["work"] + int(consensus.block_work(block))
            self.db.execute("INSERT INTO blocks VALUES(?,?,?,?,?,?,0)",
                            (h, parent_hash, parent["height"]+1, str(work), _j(block), _j(state)))
            return h, True

    def add_block(self, block):
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                h, inserted = self._add_block_locked(block)
                if inserted:
                    self._select_main()
                self.db.commit()
                return h
            except Exception:
                self.db.rollback()
                raise

    def add_blocks_atomic(self, blocks, expected_tip=None):
        """Import a bounded block batch atomically; expected_tip is (hash, height, work)."""
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                added = count = 0
                for block in blocks:
                    count += 1
                    if count > MAX_DAG_BLOCKS:
                        raise ValueError("block batch limit")
                    _, inserted = self._add_block_locked(block)
                    added += inserted
                if added:
                    self._select_main()
                if expected_tip is not None:
                    if (not isinstance(expected_tip, (tuple, list)) or len(expected_tip) != 3
                            or not isinstance(expected_tip[0], str)
                            or type(expected_tip[1]) is not int or type(expected_tip[2]) is not int):
                        raise ValueError("invalid expected peer tip")
                    tip = self.get(expected_tip[0])
                    if (tip is None or tip["height"] != expected_tip[1]
                            or tip["work"] != expected_tip[2]):
                        raise ValueError("peer advertised tip unavailable")
                self.db.commit()
                return added
            except Exception:
                self.db.rollback()
                raise

    def mine(self, miner, transactions=(), timestamp=None):
        with self.lock:
            t = self.tip
            block = consensus.make_block(t["block"], t["state"], list(transactions), miner, self.config,
                                         timestamp=timestamp, ancestors=self._ancestors(t['hash']))
            return self.add_block(block)
    def state(self): return self.tip["state"]
    def close(self): self.db.close()

def open_chain(path="samanvay.sqlite3", profile="devnet"):
    return Chain(path, params.default_config(profile))
