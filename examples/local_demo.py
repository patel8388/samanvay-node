#!/usr/bin/env python3
"""Disposable no-value demonstration. Run: python3 examples/local_demo.py

Creates temporary databases, mines real easy-target SHA256d blocks, funds two
stakes, claims, exits, withdraws, and syncs a second local node. No paid calls.
Keys and databases are deleted when this finite demonstration exits.
"""
import json
import sys
import tempfile
import threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from samanvay import consensus, crypto, params
from samanvay.chain import Chain
from samanvay.server import _LocalHTTPServer, sync


def run():
    config = params.default_config('devnet')
    alice_key, bob_key = crypto.generate_key(), crypto.generate_key()
    alice = crypto.address(crypto.public_key(alice_key))
    bob = crypto.address(crypto.public_key(bob_key))
    with tempfile.TemporaryDirectory(prefix='samanvay-no-value-') as directory:
        node = Chain(Path(directory) / 'node-a.sqlite3', config)
        other = Chain(Path(directory) / 'node-b.sqlite3', config)
        server = None
        try:
            def mine(transactions=()):
                digest = node.mine(alice, transactions)
                state = node.state()
                assert consensus.supply_total(state) == state['issued']
                return digest

            def until(height):
                while node.tip['height'] < height:
                    mine()

            def signed(key, kind, **fields):
                sender = crypto.address(crypto.public_key(key))
                return crypto.sign_transaction(dict(version=1, network='tSAMV',
                    network_id=config['network_id'], type=kind, sender=sender,
                    nonce=node.state()['nonces'].get(sender, 0),
                    expiry=node.tip['height']+1000, fee=0, **fields), key)

            until(4)  # First miner output is now mature.
            mine([signed(alice_key, 'transfer', to=bob, amount=10*params.UNIT)])
            alice_lock = signed(alice_key, 'lock', amount=params.UNIT)
            bob_lock = signed(bob_key, 'lock', amount=2*params.UNIT)
            mine([alice_lock, bob_lock])
            lid = crypto.txid(alice_lock)
            until(24)
            first = node.state()['claims']['1']
            assert first['dust'] == 1
            until(first['mature']-1)
            mine([signed(alice_key, 'claim', epoch=1, lock_id=lid,
                         reward=first['entitlements'][lid])])
            # Lock at height 6 activates at 13. Seven complete active epochs end
            # at height 96; requesting during epoch 7 permits exit at height 97.
            request = params.activation_height(6, config) + 6*config['epoch_blocks']
            until(request-1)
            mine([signed(alice_key, 'exit', lock_id=lid)])
            withdrawal = node.state()['locks'][lid]['withdraw_height']
            until(withdrawal-1)
            mine([signed(alice_key, 'withdraw', lock_id=lid)])
            assert lid not in node.state()['locks']
            # A separate previously earned epoch remains claimable after principal withdrawal.
            after_exit_claim = node.state()['claims']['2']['entitlements'][lid]
            mine([signed(alice_key, 'claim', epoch=2, lock_id=lid, reward=after_exit_claim)])
            server = _LocalHTTPServer(('127.0.0.1', 0), node)
            thread = threading.Thread(target=server.serve_forever,
                                      kwargs={'poll_interval': .02}, daemon=True)
            thread.start()
            accepted = sync(other, 'http://127.0.0.1:' + str(server.server_address[1]))
            assert other.tip['hash'] == node.tip['hash']
            assert other.state() == node.state()
            summary = {'asset': 'tSAMV — NO VALUE — NO REDEMPTION',
                       'profile': config['network_id'],
                       'height': node.tip['height'], 'tip_hash': node.tip['hash'],
                       'chainwork': node.tip['work'], 'synced_new_blocks': accepted,
                       'peer_states_equal': other.state() == node.state(),
                       'cap_usamv': config['cap'], 'issued_usamv': node.state()['issued'],
                       'supply_conserved': consensus.supply_total(node.state()) == node.state()['issued'],
                       'first_epoch_dust_usamv': first['dust'],
                       'principal_withdrawn': lid not in node.state()['locks'],
                       'claim_after_withdrawal_usamv': after_exit_claim,
                       'temporary_keys_and_databases_deleted_on_exit': True}
            server.shutdown()
            thread.join(timeout=3)
            return summary
        finally:
            if server is not None:
                server.server_close()
            node.close()
            other.close()


if __name__ == '__main__':
    print(json.dumps(run(), indent=2, sort_keys=True))
