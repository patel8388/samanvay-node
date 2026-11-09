"""Local wallet helpers with explicit, owner-only test key storage.

Encrypted keystores are a development milestone, not audited production custody.
"""
from __future__ import annotations

import base64
import errno
import json
import os
import stat
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from . import crypto

MAX_FILE = 64 * 1024
KEYSTORE_FORMAT = "samanvay-keystore"
KEYSTORE_VERSION = 1
KDF_PARAMS = {"n": 1 << 15, "r": 8, "p": 1}
CIPHER = "aes-256-gcm"
MIN_PASSPHRASE_BYTES = 12
MAX_PASSPHRASE_BYTES = 1024
_AAD_DOMAIN = b"Samanvay local keystore v1\x00"


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate wallet JSON field")
        result[key] = value
    return result


def _target_and_parent(path, create_parent=False):
    p = Path(os.path.abspath(Path(path).expanduser()))
    if not p.name or p.name in {".", ".."}:
        raise ValueError("wallet path must name a file")
    if (os.name != "posix" or not hasattr(os, "O_NOFOLLOW")
            or os.open not in getattr(os, "supports_dir_fd", set())):
        raise ValueError("secure wallet file access requires POSIX no-follow directory operations")
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    directory_fd = os.open(os.sep, directory_flags)
    try:
        for component in p.parts[1:-1]:
            try:
                child_fd = os.open(component, directory_flags, dir_fd=directory_fd)
            except FileNotFoundError:
                if not create_parent:
                    raise
                try:
                    os.mkdir(component, 0o700, dir_fd=directory_fd)
                except FileExistsError:
                    pass
                try:
                    child_fd = os.open(component, directory_flags, dir_fd=directory_fd)
                except OSError as error:
                    if error.errno in (errno.ELOOP, errno.ENOTDIR):
                        raise ValueError("wallet path contains a symlink or non-directory component") from error
                    raise
            except OSError as error:
                if error.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise ValueError("wallet path contains a symlink or non-directory component") from error
                raise
            os.close(directory_fd)
            directory_fd = child_fd
        info = os.fstat(directory_fd)
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o022):
            raise ValueError("wallet directory must be owned by this user and not group/world-writable")
        return p, directory_fd
    except Exception:
        os.close(directory_fd)
        raise


def _read_document(path):
    p, directory_fd = _target_and_parent(path)
    try:
        try:
            fd = os.open(p.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                         dir_fd=directory_fd)
        except OSError as error:
            if error.errno == errno.ELOOP:
                raise ValueError("wallet must be a regular, owner-only file") from error
            raise
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("wallet must be a regular, owner-only file")
            if info.st_uid != os.getuid():
                raise ValueError("wallet file must be owned by this user")
            if info.st_mode & 0o077:
                raise ValueError("wallet file must be owner-only")
            if info.st_size > MAX_FILE:
                raise ValueError("wallet file is too large")
            raw = handle.read(MAX_FILE + 1)
            after = os.fstat(handle.fileno())
        if len(raw) > MAX_FILE or after.st_size > MAX_FILE:
            raise ValueError("wallet file is too large")
        if len(raw) != after.st_size:
            raise ValueError("wallet file changed during read")
        if ((info.st_dev, info.st_ino, info.st_uid, info.st_gid, info.st_mode,
             info.st_size, info.st_mtime_ns, info.st_ctime_ns)
                != (after.st_dev, after.st_ino, after.st_uid, after.st_gid, after.st_mode,
                    after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
            raise ValueError("wallet file changed during read")
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_json_object)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("invalid wallet JSON") from error
    finally:
        os.close(directory_fd)
    if not isinstance(value, dict):
        raise ValueError("invalid wallet document")
    return value


def _validate_passphrase(passphrase):
    if not isinstance(passphrase, str):
        raise ValueError("passphrase must be text")
    encoded = passphrase.encode("utf-8")
    if not MIN_PASSPHRASE_BYTES <= len(encoded) <= MAX_PASSPHRASE_BYTES:
        raise ValueError("passphrase must be 12 to 1024 UTF-8 bytes")
    return encoded


def _b64(data):
    return base64.b64encode(data).decode("ascii")


def _unb64(value, field):
    if not isinstance(value, str):
        raise ValueError("invalid keystore " + field)
    try:
        return base64.b64decode(value, validate=True)
    except Exception as error:
        raise ValueError("invalid keystore " + field) from error


def _metadata(public_key, salt):
    return {
        "format": KEYSTORE_FORMAT,
        "version": KEYSTORE_VERSION,
        "kdf": "scrypt",
        "kdf_params": KDF_PARAMS,
        "cipher": CIPHER,
        "public_key": public_key,
        "salt": _b64(salt),
    }


def _derive_key(passphrase, salt):
    return Scrypt(salt=salt, length=32, **KDF_PARAMS).derive(passphrase)


def _make_keystore(private_key, passphrase):
    passphrase_bytes = _validate_passphrase(passphrase)
    public_key = crypto.public_key(private_key)
    salt = os.urandom(16)
    nonce = os.urandom(12)
    metadata = _metadata(public_key, salt)
    aad = _AAD_DOMAIN + crypto.canonical(metadata)
    ciphertext = AESGCM(_derive_key(passphrase_bytes, salt)).encrypt(
        nonce, bytes.fromhex(private_key), aad
    )
    return {
        **metadata,
        "nonce": _b64(nonce),
        "ciphertext": _b64(ciphertext),
    }


def _write_new(path, document):
    p, directory_fd = _target_and_parent(path, create_parent=True)
    payload = (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    if len(payload) > MAX_FILE:
        os.close(directory_fd)
        raise ValueError("wallet file is too large")
    fd = None
    try:
        fd = os.open(p.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=directory_fd)
        os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
        handle = os.fdopen(fd, "wb")
        fd = None
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.fsync(directory_fd)
    finally:
        if fd is not None:
            os.close(fd)
        os.close(directory_fd)
    return p


def write_json_new(path, document):
    """Write a new owner-only JSON file without following or overwriting paths."""
    payload = (json.dumps(document, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    p, directory_fd = _target_and_parent(path, create_parent=True)
    fd = None
    try:
        fd = os.open(p.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=directory_fd)
        os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
        handle = os.fdopen(fd, "wb")
        fd = None
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.fsync(directory_fd)
    finally:
        if fd is not None:
            os.close(fd)
        os.close(directory_fd)
    return p


def keygen(path):
    """Create the legacy plaintext format for disposable local test keys only."""
    private = crypto.generate_key()
    public = crypto.public_key(private)
    p = _write_new(path, {"private_key": private, "public_key": public})
    return {"public_key": public, "path": str(p)}


def create_encrypted(path, passphrase):
    """Create a new Scrypt/AES-GCM encrypted keystore without overwriting files."""
    private = crypto.generate_key()
    public = crypto.public_key(private)
    document = _make_keystore(private, passphrase)
    p = _write_new(path, document)
    return {"public_key": public, "path": str(p), "encrypted": True}


def is_encrypted(path):
    return _read_document(path).get("format") == KEYSTORE_FORMAT


def load_with_prompt(path, prompt):
    """Load one validated wallet document, prompting only for encrypted files."""
    document = _read_document(path)
    if document.get("format") == KEYSTORE_FORMAT:
        return _decrypt_keystore(document, prompt("Wallet passphrase: "))
    return _load_plain_document(document)


def _decrypt_keystore(document, passphrase):
    expected_fields = {
        "format", "version", "kdf", "kdf_params", "cipher", "public_key",
        "salt", "nonce", "ciphertext",
    }
    if set(document) != expected_fields:
        raise ValueError("invalid keystore fields")
    if (document["format"] != KEYSTORE_FORMAT or type(document["version"]) is not int
            or document["version"] != KEYSTORE_VERSION or document["kdf"] != "scrypt"
            or document["kdf_params"] != KDF_PARAMS or document["cipher"] != CIPHER):
        raise ValueError("unsupported keystore format or parameters")
    public_key = document["public_key"]
    if not isinstance(public_key, str) or len(public_key) != 64:
        raise ValueError("invalid keystore public key")
    try:
        bytes.fromhex(public_key)
    except ValueError as error:
        raise ValueError("invalid keystore public key") from error

    passphrase_bytes = _validate_passphrase(passphrase)
    salt = _unb64(document["salt"], "salt")
    nonce = _unb64(document["nonce"], "nonce")
    ciphertext = _unb64(document["ciphertext"], "ciphertext")
    if len(salt) != 16 or len(nonce) != 12 or len(ciphertext) != 48:
        raise ValueError("invalid keystore data length")
    metadata = {key: document[key] for key in (
        "format", "version", "kdf", "kdf_params", "cipher", "public_key", "salt"
    )}
    aad = _AAD_DOMAIN + crypto.canonical(metadata)
    try:
        private = AESGCM(_derive_key(passphrase_bytes, salt)).decrypt(nonce, ciphertext, aad).hex()
    except InvalidTag as error:
        raise ValueError("wrong passphrase or damaged keystore") from error
    if crypto.public_key(private) != public_key:
        raise ValueError("wrong passphrase or damaged keystore")
    return private


def _load_plain_document(document):
    key = document.get("private_key")
    if not isinstance(key, str) or len(key) > 256:
        raise ValueError("invalid private key")
    # Validate legacy plaintext keys before returning them.
    crypto.public_key(key)
    return key


def load(path, passphrase=None):
    document = _read_document(path)
    if document.get("format") == KEYSTORE_FORMAT:
        if passphrase is None:
            raise ValueError("passphrase required for encrypted wallet")
        return _decrypt_keystore(document, passphrase)
    return _load_plain_document(document)


def account_from_private(private, network):
    public = crypto.public_key(private)
    return {"private_key": private, "public_key": public, "address": crypto.address(public, network)}


def account(path, network, passphrase=None):
    return account_from_private(load(path, passphrase), network)


def sign(tx, path, passphrase=None):
    return crypto.sign_transaction(tx, load(path, passphrase))


def make_transaction(kind, sender, nonce, expiry, fee, network, **fields):
    if any(type(value) is not int or value < 0 for value in (nonce, expiry, fee)):
        raise ValueError("integer transaction fields required")
    tx = {"version": 1, "network": network, "type": kind, "sender": sender,
          "nonce": nonce, "expiry": expiry, "fee": fee}
    tx.update(fields)
    return tx


def build_signed(path, network, kind, nonce, expiry, fee, passphrase=None, **fields):
    private = load(path, passphrase)
    return build_signed_from_private(private, network, kind, nonce, expiry, fee, **fields)


def build_signed_from_private(private, network, kind, nonce, expiry, fee, **fields):
    sender = crypto.address(crypto.public_key(private), network)
    tx = make_transaction(kind, sender, nonce, expiry, fee, network, **fields)
    return crypto.sign_transaction(tx, private)
