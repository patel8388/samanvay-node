import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from samanvay import consensus, crypto, params
from samanvay.chain import Chain

_SPEC = importlib.util.spec_from_file_location(
    "offline_exchange", Path(__file__).parents[1] / "examples" / "offline_exchange.py")
offline = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(offline)

MINER = crypto.address(crypto.public_key("00" * 32))


class OfflineExchangeTests(unittest.TestCase):
    def test_documented_source_run_cli_round_trip_and_repeat(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            source_path, target_path = Path(d) / 'source.sqlite3', Path(d) / 'target.sqlite3'
            chain = Chain(source_path)
            chain.mine(MINER, timestamp=1)
            expected = chain.tip['hash']
            chain.close()
            bundle = Path(d) / 'blocks.json'
            def run(db, *args):
                result = subprocess.run(
                    [sys.executable, 'examples/offline_exchange.py', '--db', str(db), *args],
                    cwd=root, capture_output=True, text=True, timeout=15, check=True)
                return json.loads(result.stdout)
            self.assertEqual(run(source_path, 'export', '--out', str(bundle))['blocks'], 2)
            self.assertEqual(run(target_path, 'import', '--input', str(bundle))['blocks'], 1)
            self.assertEqual(run(target_path, 'import', '--input', str(bundle))['blocks'], 0)
            target = Chain(target_path)
            try:
                self.assertEqual(target.tip['hash'], expected)
            finally:
                target.close()

    def test_file_byte_bound_and_nonfinite_json(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'bundle.json'
            path.write_bytes(b' ' * 17)
            with patch.object(offline, 'MAX_BUNDLE_BYTES', 16):
                with self.assertRaises(ValueError):
                    offline._read_bundle(path)
            path.write_bytes(b'{"value":NaN}')
            with self.assertRaises(ValueError):
                offline._read_bundle(path)

    def test_forks_export_deterministically_and_restart_preserves_state(self):
        with tempfile.TemporaryDirectory() as d:
            a_path, b_path = Path(d) / "a.sqlite3", Path(d) / "b.sqlite3"
            bundle1, bundle2 = Path(d) / "one.json", Path(d) / "two.json"
            a = Chain(a_path, params.default_config())
            genesis = a.tip["block"]
            a.mine(MINER, timestamp=1)
            parent = a.tip["block"]
            # Build two valid competing children through independent Chain state
            a.mine(MINER, timestamp=2)
            fork = Chain(b_path, params.default_config())
            fork.add_block(parent)
            fork.mine(MINER, timestamp=3)
            # Bring the fork back to A, then export the complete DAG.
            for row in fork.blocks():
                if row["height"] > 0:
                    a.add_block(row["block"])
            before = a.state()
            self.assertEqual(offline.export_bundle(a, bundle1), 4)
            self.assertEqual(offline.export_bundle(a, bundle2), 4)
            self.assertEqual(bundle1.read_bytes(), bundle2.read_bytes())
            a.close(); fork.close()
            restarted = Chain(a_path, params.default_config())
            self.assertEqual(restarted.state(), before)
            target = Chain(Path(d) / "target.sqlite3", params.default_config())
            self.assertEqual(offline.import_bundle(target, bundle1), 3)
            self.assertEqual(target.tip["hash"], restarted.tip["hash"])
            target.close(); restarted.close()

    def test_wrong_identity_and_tampering_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            source = Chain(Path(d) / "source.sqlite3", params.default_config())
            source.mine(MINER, timestamp=1)
            good = Path(d) / "good.json"
            offline.export_bundle(source, good)
            obj = json.loads(good.read_text())
            obj["identity"]["network_id"] = "wrong-network"
            wrong = Path(d) / "wrong.json"
            wrong.write_text(json.dumps(obj))
            target = Chain(Path(d) / "target.sqlite3", params.default_config())
            with self.assertRaises(ValueError):
                offline.import_bundle(target, wrong)
            obj = json.loads(good.read_text())
            obj["tip"]["work"] = "999999"
            tampered = Path(d) / "tampered.json"
            tampered.write_text(json.dumps(obj))
            with self.assertRaises(ValueError):
                offline.import_bundle(target, tampered)
            # A bad later block demonstrates documented prefix-commit behavior.
            obj = json.loads(good.read_text())
            obj["blocks"].append(obj["blocks"][-1])
            prefix = Path(d) / "prefix.json"
            prefix.write_text(json.dumps(obj))
            with self.assertRaises(ValueError):
                offline.import_bundle(target, prefix)
            self.assertIsNotNone(target.get(consensus.block_hash(source.tip["block"])))
            target.close(); source.close()

    def test_output_never_overwrites_and_strict_json_rejects_duplicates(self):
        with tempfile.TemporaryDirectory() as d:
            chain = Chain(Path(d) / "node.sqlite3", params.default_config())
            out = Path(d) / "bundle.json"
            offline.export_bundle(chain, out)
            with self.assertRaises(ValueError):
                offline.export_bundle(chain, out)
            duplicate = Path(d) / "duplicate.json"
            duplicate.write_bytes(b'{"version":1,"version":1}')
            with self.assertRaises(ValueError):
                offline.import_bundle(chain, duplicate)
            chain.close()


if __name__ == "__main__":
    unittest.main()
