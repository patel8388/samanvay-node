---
name: Review and publish the encrypted local keystore milestone
slug: review-encrypted-local-keystore
project: samanvay-layer1-wallet
priority: high
---

# Review and publish the encrypted local keystore milestone

The working tree contains an experimental local Scrypt/AES-GCM keystore, passphrase prompts, encrypted-wallet address display, and offline transaction signing. It is for disposable tSAMV only; legacy plaintext `keygen` remains test-only.

## Acceptance criteria

- The complete repository verification suite passes, including new keystore tests.
- Re-review the descriptor-bound, owner-only file operations and single-load CLI flow; publish limitations and any remaining findings.
- Confirm that passphrases are not accepted as command-line arguments or written to output files.
- Publish the focused change for public review; do not merge to a production/mainnet release or treat it as audited key custody.
- Preserve wrong-passphrase, tamper, no-overwrite, file-permission, and plaintext-compatibility regression tests.
- Before any production/network exposure, bound generic CLI JSON inputs/outputs and decide how interrupted writes are surfaced or cleaned. Current exclusive writes prevent overwrite but do not guarantee atomic completion if disk/write operations fail.
