"""Finite integration tests for the disposable local Samanvay runtime.

These tests deliberately exercise the public HTTP and CLI surfaces rather than
mocking transport or manufacturing coinbase balances.  They are kept bounded:
all chains use devnet's short timings and the easy, fixed testnet PoW target.
"""
from __future__ import annotations

import copy
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path

from samanvay import consensus, crypto, params
from samanvay.chain import Chain
from samanvay.server import _LocalHTTPServer, sync


ROOT = Path(__file__).resolve().parents[1]


class IntegrationTests(unittest.TestCase):
    _port = 30000 + (int(time.time() * 1000) % 20000)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.config = params.default_config("devnet")
        self.chains: list[Chain] = []
        self.servers: list[threading.Thread] = []
        self.miner_key = crypto.generate_key()
        self.miner = crypto.address(crypto.public_key(self.miner_key), self.config["network"])

    def tearDown(self):
        for server, thread in self.servers:
            server.shutdown()
            thread.join(timeout=3)
            server.server_close()
        for chain in self.chains:
            try:
                chain.close()
            except Exception:
                pass
        self.tmp.cleanup()

    def chain(self, name):
        c = Chain(self.root / (name + ".sqlite3"), self.config)
        self.chains.append(c)
        return c

    def mine(self, chain, miner=None, count=1):
        miner = miner or self.miner
        for _ in range(count):
            chain.mine(miner)

    def start_server(self, chain, port=None):
        server = _LocalHTTPServer(('127.0.0.1', port or 0), chain)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .02}, daemon=True)
        thread.start()
        self.servers.append((server, thread))
        return server.server_address[1]

    def cli(self, *args, check=True):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        p = subprocess.run([sys.executable, "-m", "samanvay", *map(str, args)],
                           cwd=ROOT, env=env, text=True, capture_output=True)
        if check and p.returncode:
            self.fail(f"CLI failed ({p.returncode}): {p.stderr}\n{p.stdout}")
        return p

    def test_real_two_node_http_sync_transfers_mined_blocks(self):
        a, b = self.chain("a"), self.chain("b")
        self.mine(a, miner=self.miner, count=3)
        pa, pb = self.start_server(a), self.start_server(b)
        accepted = sync(b, f"http://127.0.0.1:{pa}")
        self.assertGreaterEqual(accepted, 3)
        self.assertEqual(a.tip["hash"], b.tip["hash"])
        self.assertEqual(a.tip["height"], b.tip["height"])
        self.assertEqual(b.state(), a.state())

    def test_partition_fork_converges_to_longer_cumulative_work(self):
        a, b = self.chain("fork-a"), self.chain("fork-b")
        self.mine(a, miner=self.miner, count=3)
        other_miner = crypto.address(crypto.public_key(crypto.generate_key()))
        self.mine(b, miner=other_miner, count=5)
        self.assertNotEqual(a.tip["hash"], b.tip["hash"])
        self.assertNotEqual(a.blocks(2)[1]['hash'], b.blocks(2)[1]['hash'])
        pa, pb = self.start_server(a), self.start_server(b)
        sync(a, f"http://127.0.0.1:{pb}")
        self.assertEqual(a.tip["hash"], b.tip["hash"])
        self.assertEqual(a.tip["work"], b.tip["work"])
        self.assertEqual(a.state(), b.state())

    def test_orphaned_fork_rolls_back_staking_state(self):
        a, b = self.chain("stake-a"), self.chain("stake-b")
        key = crypto.generate_key()
        addr = crypto.address(crypto.public_key(key), self.config["network"])
        # Real funding only: mature a coinbase output, then spend it into a lock.
        self.mine(a, miner=addr, count=self.config["maturity"] + 1)
        tx = crypto.sign_transaction({"version": 1, "network": self.config["network"],
            "type": "lock", "sender": addr, "network_id": self.config["network_id"], "nonce": 0, "expiry": 1000,
            "fee": 0, "amount": params.UNIT}, key)
        a.mine(addr, [tx])
        self.mine(b, miner=self.miner, count=a.tip["height"] + 2)
        self.start_server(a); pb = self.start_server(b)
        sync(a, f"http://127.0.0.1:{pb}")
        self.assertEqual(a.tip["hash"], b.tip["hash"])
        self.assertNotIn(crypto.txid(tx), a.state().get("locks", {}))
        self.assertEqual(a.state(), b.state())

    def test_restart_reindexes_tampered_cached_state(self):
        path = self.root / "reindex.sqlite3"
        c = Chain(path, self.config); self.chains.append(c)
        self.mine(c, count=2)
        tip_hash = c.tip["hash"]
        c.close(); self.chains.remove(c)
        db = sqlite3.connect(path)
        db.execute("UPDATE blocks SET state=? WHERE hash=?", (json.dumps({"tampered": True}), tip_hash))
        db.commit(); db.close()
        repaired = Chain(path, self.config); self.chains.append(repaired)
        self.assertEqual(repaired.tip["hash"], tip_hash)
        self.assertNotIn("tampered", repaired.state())
        self.assertEqual(repaired.state()["height"], 2)

    def test_restart_rejects_corrupted_stored_block(self):
        path = self.root / "corrupt.sqlite3"
        c = Chain(path, self.config); self.chains.append(c); self.mine(c, count=1)
        c.close(); self.chains.remove(c)
        db = sqlite3.connect(path)
        db.execute("UPDATE blocks SET block=? WHERE height=1", ('{"corrupt":true}',))
        db.commit(); db.close()
        with self.assertRaises(ValueError):
            Chain(path, self.config)

    def test_http_surface_is_finite_json_and_rejects_non_loopback_peer(self):
        c = self.chain("http")
        port = self.start_server(c)
        conn = HTTPConnection("127.0.0.1", port, timeout=2)
        conn.request("GET", "/status")
        response = conn.getresponse()
        body = json.loads(response.read())
        conn.close()
        self.assertEqual(response.status, 200)
        self.assertEqual(body["height"], 0)
        with self.assertRaises(ValueError):
            sync(c, "http://8.8.8.8:80")

    def test_cli_keygen_init_mine_transfer_and_epoch_claim_syntax(self):
        db = self.root / "cli.sqlite3"
        keyfile = self.root / "miner.key"
        result = self.cli("keygen", "--out", keyfile)
        self.assertIn("public_key", json.loads(result.stdout))
        account = json.loads(keyfile.read_text())
        address = crypto.address(account["public_key"], self.config["network"])
        init = json.loads(self.cli("--db", db, "init").stdout)
        self.assertEqual(init["network"], self.config["network"])
        # Mine enough real blocks for this account's coinbase to mature.
        self.cli("--db", db, "mine", "--miner", address, "--count", self.config["maturity"] + 1)
        txfile = self.root / "transfer.json"
        self.cli("--db", db, "transfer", "--key", keyfile, "--to", address,
                 "--amount", 1, "--out", txfile)
        mined = self.cli("--db", db, "mine", "--miner", address, "--tx", txfile)
        self.assertTrue(json.loads(mined.stdout)["hash"])
        status = json.loads(self.cli("--db", db, "status").stdout)
        self.assertEqual(status["tip"]["height"], self.config["maturity"] + 2)
        # The parser must expose epoch-explicit claims; execution is covered by
        # consensus tests because creating a mature staking entitlement is costly.
        help_result = self.cli("claim", "--help")
        self.assertIn("--epoch", help_result.stdout)


if __name__ == "__main__":
    unittest.main()
