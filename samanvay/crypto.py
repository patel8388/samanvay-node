"""Small, strict Ed25519 and canonical serialization layer."""
import hashlib, json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',',':'), ensure_ascii=False, allow_nan=False).encode('utf-8')
def sha256d(data): return hashlib.sha256(hashlib.sha256(data).digest()).hexdigest()
def _raw_private(h):
    if not isinstance(h,str) or len(h)!=64: raise ValueError('private key')
    try: return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(h))
    except Exception as e: raise ValueError('private key') from e
def generate_key(): return _raw_private(__import__('secrets').token_hex(32)).private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption()).hex()
def public_key(private_hex): return _raw_private(private_hex).public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()
def address(pub_hex, network='tSAMV'):
    if not isinstance(pub_hex,str) or len(pub_hex)!=64: raise ValueError('public key')
    try: bytes.fromhex(pub_hex)
    except Exception as e: raise ValueError('public key') from e
    if not isinstance(network,str) or not network: raise ValueError('network')
    return 's'+hashlib.sha256((network+'|'+pub_hex).encode()).hexdigest()[:39]
def _unsigned(tx): return {k:v for k,v in tx.items() if k not in ('signature','public_key')}
def sign_transaction(tx, private_hex):
    out=dict(tx); out['public_key']=public_key(private_hex)
    out['signature']=_raw_private(private_hex).sign(canonical(_unsigned(out))).hex(); return out
def verify_transaction_signature(tx):
    try:
        if not isinstance(tx,dict) or tx.get('sender')!=address(tx['public_key'],tx['network']): return False
        if len(tx['signature'])!=128: return False
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(tx['public_key'])).verify(bytes.fromhex(tx['signature']),canonical(_unsigned(tx))); return True
    except Exception: return False
def txid(tx): return sha256d(canonical(tx))
