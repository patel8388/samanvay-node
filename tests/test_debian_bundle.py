"""Static and dry-run checks for the Debian 12 preparation bundle."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "packaging" / "debian12"


class DebianBundleTests(unittest.TestCase):
    def test_scripts_and_unit_are_conservative(self):
        setup = (BUNDLE / "setup.sh").read_text()
        runner = (BUNDLE / "run-local.sh").read_text()
        unit = (BUNDLE / "samanvay-local@.service").read_text()
        self.assertIn("MODE=preflight", setup)
        self.assertIn("--no-index", setup)
        self.assertIn("--only-binary=:all:", setup)
        self.assertIn("cryptography-50.0.2", setup)
        self.assertIn("Python 3.12+ is unavailable", setup)
        self.assertIn("--host 127.0.0.1", runner)
        self.assertNotIn("0.0.0.0", runner)
        self.assertIn("MemoryMax=384M", unit)
        self.assertIn("TasksMax=16", unit)
        self.assertIn("CPUQuota=50%", unit)
        self.assertIn("Restart=no", unit)
        self.assertNotIn("Restart=always", unit)

    def test_python311_only_preflight_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as home:
            for name in ("python3", "python3.12", "python3.13", "python3.14"):
                fake = Path(tmp) / name
                fake.write_text("#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then echo Python 3.11.2; else exit 1; fi\n")
                fake.chmod(0o755)
            env = os.environ.copy()
            env.update(HOME=home, PATH=f"{tmp}:/usr/bin:/bin")
            result = subprocess.run([str(BUNDLE / "setup.sh")], cwd=ROOT, env=env, text=True, capture_output=True)
            output = result.stdout + result.stderr
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Python 3.12+ is unavailable", output)
            self.assertIn("3.11 is not supported", output)

    def test_default_preflight_is_no_mutation_and_fails_closed_here_if_needed(self):
        with tempfile.TemporaryDirectory() as home:
            before = set(Path(home).iterdir())
            env = os.environ.copy()
            env["HOME"] = home
            result = subprocess.run(
                [str(BUNDLE / "setup.sh"), "--preflight"],
                cwd=ROOT, env=env, text=True, capture_output=True,
            )
            output = result.stdout + result.stderr
            self.assertIn("Preflight", output)
            self.assertEqual(before, set(Path(home).iterdir()))
            # Missing Python, pip or offline dependencies must stop preparation.
            if result.returncode:
                self.assertIn("FAIL:", output)
                self.assertIn("No runtime changes made", output)

    def test_install_is_binary_only_and_does_not_build_project(self):
        setup = (BUNDLE / 'setup.sh').read_text()
        self.assertIn('--dry-run --ignore-installed --no-index --only-binary=:all:', setup)
        self.assertIn('PIP_CONFIG_FILE=/dev/null', setup)
        self.assertIn('--no-cache-dir', setup)
        self.assertIn('refusing to alter existing venv', setup)
        self.assertNotIn('--find-links "$WHEELHOUSE" "$ROOT_DIR"', setup)


if __name__ == "__main__":
    unittest.main()
