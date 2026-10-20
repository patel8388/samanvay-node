"""Local command-line node. No background mining or public bind by default."""
import argparse
import json
import sys
from . import wallet, crypto, consensus
from .chain import open_chain


def out(value):
    print(json.dumps(value, sort_keys=True, indent=2))


def _read(path):
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


def _write(path, value):
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(value, handle, sort_keys=True, indent=2)
        handle.write('\n')


def main(argv=None):
    parser = argparse.ArgumentParser(prog='samanvay', description='Disposable local tSAMV only; NEVER use real value.')
    parser.add_argument('--db', default='samanvay.sqlite3')
    parser.add_argument('--profile', default='devnet', choices=['devnet', 'rules'])
    commands = parser.add_subparsers(dest='cmd', required=True)
    keygen = commands.add_parser('keygen')
    keygen.add_argument('--out', required=True)
    address = commands.add_parser('address')
    address.add_argument('--key', required=True)
    for name in ('init', 'status'):
        commands.add_parser(name)
    mine = commands.add_parser('mine')
    mine.add_argument('--miner', required=True)
    mine.add_argument('--timestamp', type=int)
    mine.add_argument('--count', type=int, default=1)
    mine.add_argument('--tx', action='append', default=[], help='signed transaction JSON file; first mined block only')

    def txparser(name):
        command = commands.add_parser(name)
        command.add_argument('--key', required=True)
        command.add_argument('--fee', type=int, default=0)
        command.add_argument('--expiry', type=int)
        command.add_argument('--nonce', type=int)
        command.add_argument('--out', required=True, help='writes a signed transaction; does not broadcast')
        return command

    for name in ('transfer', 'send'):
        command = txparser(name)
        command.add_argument('--to', required=True)
        command.add_argument('--amount', type=int, required=True, help='integer usamv, 1 tSAMV = 1000000')
    command = txparser('lock')
    command.add_argument('--amount', type=int, required=True)
    for name in ('exit', 'withdraw'):
        command = txparser(name)
        command.add_argument('--lock-id', required=True)
    command = txparser('claim')
    command.add_argument('--lock-id', required=True)
    command.add_argument('--epoch', type=int, required=True)
    command.add_argument('--reward', type=int, required=True)
    command = commands.add_parser('build')
    command.add_argument('--json', required=True)
    command.add_argument('--out', required=True)
    command = commands.add_parser('sign')
    command.add_argument('--key', required=True)
    command.add_argument('--tx', required=True)
    command.add_argument('--out', required=True)
    command = commands.add_parser('submit', help='submit a complete mined block, not an unsigned transaction')
    command.add_argument('--block', '--tx', dest='block', required=True)
    command = commands.add_parser('sync')
    command.add_argument('--peer', required=True)
    command = commands.add_parser('serve')
    command.add_argument('--host', default='127.0.0.1')
    command.add_argument('--port', type=int, default=8765)
    args = parser.parse_args(argv)
    if args.cmd == 'keygen':
        out(wallet.keygen(args.out))
        return 0
    if args.cmd == 'address':
        account = wallet.account(args.key, 'tSAMV')
        out({'address': account['address'], 'public_key': account['public_key']})
        return 0
    chain = open_chain(args.db, args.profile)
    try:
        if args.cmd == 'init':
            out({'initialized': True, 'genesis': consensus.block_hash(consensus.genesis(chain.config)),
                 'network': 'tSAMV', 'network_id': chain.config['network_id'], 'asset': 'tSAMV — NO VALUE'})
        elif args.cmd == 'status':
            out({'tip': chain.tip, 'network': 'tSAMV', 'network_id': chain.config['network_id'], 'asset': 'tSAMV — NO VALUE'})
        elif args.cmd == 'mine':
            if not 1 <= args.count <= 1000:
                raise ValueError('count must be 1..1000; mining is finite and foreground')
            transactions = [_read(path) for path in args.tx]
            hashes = []
            for index in range(args.count):
                timestamp = args.timestamp + index if args.timestamp is not None else None
                hashes.append(chain.mine(args.miner, transactions if index == 0 else (), timestamp=timestamp))
            out({'hash': hashes[-1], 'mined': len(hashes), 'height': chain.tip['height']})
        elif args.cmd in ('transfer', 'send', 'lock', 'exit', 'withdraw', 'claim'):
            account = wallet.account(args.key, chain.config['network'])
            nonce = args.nonce if args.nonce is not None else chain.state()['nonces'].get(account['address'], 0)
            expiry = args.expiry if args.expiry is not None else chain.tip['height'] + chain.config['max_expiry']
            kind = 'transfer' if args.cmd == 'send' else args.cmd
            fields = {'network_id': chain.config['network_id']}
            if kind == 'transfer':
                fields.update(to=args.to, amount=args.amount)
            elif kind == 'lock':
                fields.update(amount=args.amount)
            elif kind in ('exit', 'withdraw'):
                fields.update(lock_id=args.lock_id)
            else:
                fields.update(lock_id=args.lock_id, reward=args.reward, epoch=args.epoch)
            tx = wallet.build_signed(args.key, chain.config['network'], kind, nonce, expiry, args.fee, **fields)
            _write(args.out, tx)
            out({'signed': args.out, 'txid': crypto.txid(tx), 'broadcast': False})
        elif args.cmd == 'build':
            _write(args.out, _read(args.json))
            out({'built': args.out, 'validated': False})
        elif args.cmd == 'sign':
            _write(args.out, wallet.sign(_read(args.tx), args.key))
            out({'signed': args.out, 'broadcast': False})
        elif args.cmd == 'submit':
            out({'hash': chain.add_block(_read(args.block))})
        elif args.cmd == 'sync':
            from .server import sync
            out({'accepted': sync(chain, args.peer)})
        elif args.cmd == 'serve':
            from .server import serve
            serve(chain, args.host, args.port)
    finally:
        chain.close()
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError) as error:
        print('Error: ' + str(error), file=sys.stderr)
        sys.exit(1)
