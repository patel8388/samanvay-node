"""Local wallet helpers; private keys are read only from explicit owner-only files."""
from __future__ import annotations
import json, os, stat
from pathlib import Path
from . import crypto
MAX_FILE=64*1024

def keygen(path):
    p=Path(path).expanduser()
    if p.exists(): raise FileExistsError(str(p))
    private=crypto.generate_key(); public=crypto.public_key(private)
    p.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try: os.write(fd,(json.dumps({'private_key':private,'public_key':public},sort_keys=True)+'\n').encode())
    finally: os.close(fd)
    os.chmod(p,stat.S_IRUSR|stat.S_IWUSR)
    return {'public_key':public,'path':str(p)}
def load(path):
    p=Path(path).expanduser()
    if p.stat().st_size>MAX_FILE or p.stat().st_mode & 0o077: raise ValueError('key file must be small and owner-only')
    obj=json.loads(p.read_text()); key=obj.get('private_key')
    if not isinstance(key,str) or len(key)>256: raise ValueError('invalid private key')
    return key
def account(path,network):
    private=load(path); public=crypto.public_key(private)
    return {'private_key':private,'public_key':public,'address':crypto.address(public,network)}
def sign(tx,path): return crypto.sign_transaction(tx,load(path))
def make_transaction(kind,sender,nonce,expiry,fee,network,**fields):
    if any(type(x) is not int or x<0 for x in (nonce,expiry,fee)): raise ValueError('integer transaction fields required')
    tx={'version':1,'network':network,'type':kind,'sender':sender,'nonce':nonce,'expiry':expiry,'fee':fee}
    tx.update(fields); return tx
def build_signed(path,network,kind,nonce,expiry,fee,**fields):
    ac=account(path,network); return sign(make_transaction(kind,ac['address'],nonce,expiry,fee,network,**fields),path)
