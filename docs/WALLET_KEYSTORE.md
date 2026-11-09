# Local encrypted wallet keystore (experimental)

This feature stores one Samanvay Ed25519 private key in an encrypted file for disposable **tSAMV-only** development. It is a step toward a wallet, not a production or mobile wallet release. No mainnet is enabled and no real value should be used.

## Create and use a wallet

Create a new encrypted keystore. The CLI asks for a passphrase twice and does not accept the passphrase as an argument, so it is not written into shell history:

```bash
python3 -m samanvay wallet create --out .local/wallet.json
python3 -m samanvay address --key .local/wallet.json
python3 -m samanvay --db .local/node.sqlite3 transfer \
  --key .local/wallet.json --to <tSAMV-address> --amount 100 \
  --out .local/transfer.json
```

The passphrase must be at least 12 UTF-8 bytes. Address display and signing prompt for it when needed. The transfer command writes an offline signed transaction JSON file; it does **not** broadcast or pay anyone. A signed file may be included in a locally mined block using the existing `mine --tx` flow.

The older `keygen` command and existing plaintext owner-only files remain supported for finite disposable examples. They are not encrypted, and anyone with one can use its test key. Do not convert, import or reuse a real key in this prototype.

## File and cryptography behavior

- The JSON envelope records a format/version, public key, random 16-byte salt, random 12-byte nonce, KDF and cipher identifiers, and ciphertext. It contains no plaintext private key or passphrase.
- The KDF is Scrypt with `N=32768, r=8, p=1`; the 32-byte derived key encrypts the raw 32-byte Ed25519 key with AES-256-GCM. The format metadata is authenticated as associated data; the public key is checked after decryption.
- Files are created with mode `0600` inside a final parent directory owned by the current user that is not group/world-writable; the file itself must also be owned by the current user. The loader walks path components through directory file descriptors without following symlinks, opens the final file without following symlinks, bounds reads, and checks file metadata before and after a read. Only the final parent directory's ownership/mode is checked; trusted OS ancestors may be owned by root or shared. Existing paths are never overwritten. It rejects duplicate JSON fields, unknown keystore fields, unsupported KDF parameters, malformed lengths, wrong passphrases and authentication failures. This implementation currently requires POSIX no-follow directory operations; Windows wallet-key access is not qualified and fails closed.
- The passphrase is not normalized. Use the exact same characters and encoding on recovery. A lost passphrase means the key cannot be recovered; there is no server-side reset or mnemonic backup.

These settings provide authenticated local encryption but have not been externally reviewed and are not a guarantee against a hostile process running as the same user or a compromised operating system. An encrypted file can still be copied and subjected to offline passphrase guessing, and the process must hold the decrypted key in memory while signing. A compromised host, debugger, clipboard or passphrase capture can defeat the protection. Back up an encrypted file only if you understand that the backup is spend-capable when unlocked; never keep the passphrase beside it.

## Not implemented

There is no hardware-backed key store, Android/iOS application, biometric protection, mnemonic import/export, multisig, recovery scheme, remote RPC, light-client proof, automatic broadcasting, or secure phone-to-miner pairing. This keystore does not make the prototype safe for public internet nodes or valuable assets. Key-custody and platform review, usability testing, recovery design, independent security review, and network qualification remain release gates.
