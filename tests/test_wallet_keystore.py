import contextlib
import io
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from samanvay import __main__ as cli
from samanvay import crypto, wallet


PASSPHRASE = "correct horse battery staple 2026"


class WalletKeystoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.keystore = self.root / "wallet.json"
        self.created = wallet.create_encrypted(self.keystore, PASSPHRASE)

    def tearDown(self):
        self.temp.cleanup()

    def test_encrypted_file_round_trip_and_address(self):
        document = json.loads(self.keystore.read_text())
        self.assertEqual(document["format"], wallet.KEYSTORE_FORMAT)
        self.assertNotIn("private_key", document)
        self.assertTrue(wallet.is_encrypted(self.keystore))
        private = wallet.load(self.keystore, PASSPHRASE)
        self.assertEqual(crypto.public_key(private), self.created["public_key"])
        account = wallet.account(self.keystore, "tSAMV", PASSPHRASE)
        self.assertEqual(account["address"], crypto.address(self.created["public_key"], "tSAMV"))
        with self.assertRaisesRegex(ValueError, "passphrase required"):
            wallet.load(self.keystore)

    def test_wrong_passphrase_and_tampered_ciphertext_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "wrong passphrase or damaged"):
            wallet.load(self.keystore, "a different long passphrase")
        document = json.loads(self.keystore.read_text())
        import base64
        raw = bytearray(base64.b64decode(document["ciphertext"]))
        raw[0] ^= 1
        document["ciphertext"] = base64.b64encode(raw).decode("ascii")
        self.keystore.write_text(json.dumps(document))
        self.keystore.chmod(0o600)
        with self.assertRaisesRegex(ValueError, "wrong passphrase or damaged"):
            wallet.load(self.keystore, PASSPHRASE)

    def test_parameters_and_duplicate_json_fields_fail_closed(self):
        document = json.loads(self.keystore.read_text())
        document["kdf_params"]["n"] = 1 << 16
        self.keystore.write_text(json.dumps(document))
        self.keystore.chmod(0o600)
        with self.assertRaisesRegex(ValueError, "unsupported keystore"):
            wallet.load(self.keystore, PASSPHRASE)
        self.keystore.write_text('{"private_key":"x","private_key":"y"}')
        self.keystore.chmod(0o600)
        with self.assertRaisesRegex(ValueError, "duplicate wallet JSON"):
            wallet.load(self.keystore)

    def test_passphrase_strength_and_no_overwrite(self):
        with self.assertRaisesRegex(ValueError, "12 to 1024"):
            wallet.create_encrypted(self.root / "short.json", "too short")
        with self.assertRaises(FileExistsError):
            wallet.create_encrypted(self.keystore, PASSPHRASE)
        self.assertEqual(len(wallet.load(self.keystore, PASSPHRASE)), 64)

    def test_failed_sync_does_not_publish_partial_wallet_or_output(self):
        writers = (
            ("interrupted-wallet.json", lambda path: wallet.create_encrypted(path, PASSPHRASE)),
            ("interrupted-output.json", lambda path: wallet.write_json_new(path, {"ready": True})),
        )
        for name, writer in writers:
            with self.subTest(name=name):
                target = self.root / name
                with patch("samanvay.wallet.os.fsync", side_effect=OSError("simulated sync failure")):
                    with self.assertRaisesRegex(OSError, "simulated sync failure"):
                        writer(target)
                self.assertFalse(target.exists())
                self.assertEqual(list(self.root.glob(".samanvay-tmp-*")), [])

    def test_owner_only_regular_file_checks(self):
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(self.keystore.stat().st_mode), 0o600)
            self.keystore.chmod(0o640)
            with self.assertRaisesRegex(ValueError, "owner-only"):
                wallet.load(self.keystore, PASSPHRASE)
            self.keystore.chmod(0o600)
            link = self.root / "wallet-link.json"
            link.symlink_to(self.keystore)
            with self.assertRaisesRegex(ValueError, "regular, owner-only"):
                wallet.load(link, PASSPHRASE)
            shared_dir = self.root / "shared"
            shared_dir.mkdir()
            shared_dir.chmod(0o777)
            with self.assertRaisesRegex(ValueError, "wallet directory"):
                wallet.create_encrypted(shared_dir / "wallet.json", PASSPHRASE)
            actual_dir = self.root / "actual"
            actual_dir.mkdir()
            actual_wallet = actual_dir / "wallet.json"
            wallet.keygen(actual_wallet)
            parent_link = self.root / "parent-link"
            parent_link.symlink_to(actual_dir, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "wallet path contains"):
                wallet.load(parent_link / "wallet.json")

    def test_metadata_change_during_read_is_rejected(self):
        original_fstat = os.fstat
        call_count = 0

        def changed_final_stat(fd):
            nonlocal call_count
            result = original_fstat(fd)
            call_count += 1
            if call_count != 3:  # parent directory, then file before/after read
                return result
            values = {name: getattr(result, name) for name in (
                "st_dev", "st_ino", "st_uid", "st_gid", "st_mode", "st_size",
                "st_mtime_ns", "st_ctime_ns",
            )}
            values["st_ctime_ns"] += 1
            return SimpleNamespace(**values)

        with patch("samanvay.wallet.os.fstat", side_effect=changed_final_stat):
            with self.assertRaisesRegex(ValueError, "changed during read"):
                wallet.load(self.keystore, PASSPHRASE)

    def test_wallet_file_must_be_owned_by_current_user(self):
        original_fstat = os.fstat
        call_count = 0

        def foreign_owner(fd):
            nonlocal call_count
            result = original_fstat(fd)
            call_count += 1
            if call_count != 2:  # parent directory, then wallet file
                return result
            values = {name: getattr(result, name) for name in (
                "st_dev", "st_ino", "st_uid", "st_gid", "st_mode", "st_size",
                "st_mtime_ns", "st_ctime_ns",
            )}
            values["st_uid"] = os.getuid() + 1
            return SimpleNamespace(**values)

        with patch("samanvay.wallet.os.fstat", side_effect=foreign_owner):
            with self.assertRaisesRegex(ValueError, "owned by this user"):
                wallet.load(self.keystore, PASSPHRASE)

    def test_interactive_unlock_reads_one_validated_file(self):
        with patch("samanvay.wallet._read_document", wraps=wallet._read_document) as read_document:
            private = wallet.load_with_prompt(self.keystore, lambda prompt: PASSPHRASE)
        self.assertEqual(read_document.call_count, 1)
        self.assertEqual(crypto.public_key(private), self.created["public_key"])

    def test_cli_output_is_owner_only_no_overwrite_and_no_symlink(self):
        target = self.root / "output.json"
        cli._write(target, {"value": 1})
        self.assertEqual(json.loads(target.read_text()), {"value": 1})
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
        with self.assertRaises(FileExistsError):
            cli._write(target, {"value": 2})
        self.assertEqual(json.loads(target.read_text()), {"value": 1})

        protected = self.root / "protected.json"
        protected.write_text("leave untouched")
        link = self.root / "output-link.json"
        link.symlink_to(protected)
        with self.assertRaises(FileExistsError):
            cli._write(link, {"value": 3})
        self.assertEqual(protected.read_text(), "leave untouched")

        invalid = self.root / "nonfinite.json"
        with self.assertRaises(ValueError):
            cli._write(invalid, {"value": float("nan")})
        self.assertFalse(invalid.exists())

    def test_legacy_plaintext_test_key_still_loads(self):
        path = self.root / "legacy.json"
        wallet.keygen(path)
        self.assertFalse(wallet.is_encrypted(path))
        private = wallet.load(path)
        self.assertEqual(len(private), 64)
        self.assertEqual(wallet.account(path, "tSAMV")["public_key"], crypto.public_key(private))

    def test_encrypted_wallet_signs_offline_transaction(self):
        signed = wallet.build_signed(
            self.keystore, "tSAMV", "transfer", 0, 20, 0,
            passphrase=PASSPHRASE,
            network_id="test-network", to="s" + "1" * 39, amount=100,
        )
        self.assertTrue(crypto.verify_transaction_signature(signed))
        self.assertEqual(signed["sender"], crypto.address(self.created["public_key"], "tSAMV"))

    def test_cli_create_address_and_signed_transaction_use_passphrase_prompts(self):
        create_prompts = [PASSPHRASE, PASSPHRASE]
        output = io.StringIO()
        with patch("samanvay.__main__.getpass.getpass", side_effect=create_prompts):
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli.main(["wallet", "create", "--out", str(self.root / "cli-wallet.json")]), 0)
        self.assertTrue(json.loads(output.getvalue())["encrypted"])
        cli_wallet = self.root / "cli-wallet.json"

        output = io.StringIO()
        with patch("samanvay.__main__.getpass.getpass", return_value=PASSPHRASE):
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli.main(["address", "--key", str(cli_wallet)]), 0)
        self.assertIn("address", json.loads(output.getvalue()))

        db = self.root / "node.sqlite3"
        signed_path = self.root / "signed.json"
        with patch("samanvay.__main__.getpass.getpass", return_value=PASSPHRASE):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main([
                    "--db", str(db), "transfer", "--key", str(cli_wallet),
                    "--to", "s" + "2" * 39, "--amount", "1", "--out", str(signed_path),
                ]), 0)
        signed = json.loads(signed_path.read_text())
        self.assertTrue(crypto.verify_transaction_signature(signed))
        self.assertFalse(json.loads(cli_wallet.read_text()).get("private_key"))

    def test_cli_passphrase_mismatch_does_not_create_file(self):
        target = self.root / "mismatch.json"
        with patch("samanvay.__main__.getpass.getpass", side_effect=[PASSPHRASE, "not the same passphrase"]):
            with self.assertRaisesRegex(ValueError, "do not match"):
                cli.main(["wallet", "create", "--out", str(target)])
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
