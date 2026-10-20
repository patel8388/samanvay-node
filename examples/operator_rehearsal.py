#!/usr/bin/env python3
"""Finite four-process rehearsal; NOT four independent volunteer operators.

No public listeners, purchases, keys, or persistent background processes.
"""
import argparse
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def command(db, *args):
    result = subprocess.run(
        [sys.executable, '-m', 'samanvay', '--db', str(db), *args],
        cwd=ROOT, capture_output=True, text=True, timeout=30, check=True)
    return json.loads(result.stdout)


def worker(db):
    from samanvay.chain import Chain
    from samanvay.server import _LocalHTTPServer
    chain = Chain(db)
    server = _LocalHTTPServer(('127.0.0.1', 0), chain)
    print(json.dumps({'port': server.server_address[1]}), flush=True)
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()
        chain.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker-serve', metavar='DATABASE', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker_serve:
        worker(args.worker_serve)
        return
    from samanvay import consensus, crypto
    servers = []
    try:
        with tempfile.TemporaryDirectory(prefix='samanvay-rehearsal-') as directory:
            databases = [Path(directory) / f'operator-{i}.sqlite3' for i in range(4)]
            peers = []
            for index, db in enumerate(databases):
                command(db, 'init')
                if index < 3:
                    miner = crypto.address(crypto.public_key(f'{index + 1:064x}'), 'tSAMV')
                    command(db, 'mine', '--miner', miner, '--count', str(4 + index * 2), '--timestamp', '1')
            initial = [command(db, 'status')['tip'] for db in databases]
            assert [tip['height'] for tip in initial] == [4, 6, 8, 0]
            assert len({tip['hash'] for tip in initial}) == 4
            for db in databases:
                proc = subprocess.Popen(
                    [sys.executable, str(Path(__file__).resolve()), '--worker-serve', str(db)],
                    cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                servers.append(proc)
                if not select.select([proc.stdout], [], [], 10)[0]:
                    raise RuntimeError('local rehearsal listener did not become ready')
                line = proc.stdout.readline()
                if not line:
                    raise RuntimeError('local rehearsal listener failed: ' + proc.stderr.read())
                peers.append('http://127.0.0.1:' + str(json.loads(line)['port']))
            # Every node receives every branch, in a different order. The fourth
            # process begins empty; the first two must roll back their shorter forks.
            accepted = []
            for index, db in enumerate(databases):
                total = 0
                for shift in range(1, 5):
                    peer_index = (index + shift) % 4
                    if peer_index != index:
                        total += command(db, 'sync', '--peer', peers[peer_index])['accepted']
                accepted.append(total)
            after = [command(db, 'status')['tip'] for db in databases]
            assert {tip['hash'] for tip in after} == {initial[2]['hash']}
            assert len({tip['block']['state_root'] for tip in after}) == 1
            assert all(consensus.supply_total(tip['state']) == tip['state']['issued'] for tip in after)
            # Idempotent repeated sync must not count known blocks as new.
            assert all(command(db, 'sync', '--peer', peers[(i + 1) % 4])['accepted'] == 0
                       for i, db in enumerate(databases))
            for proc in servers:
                proc.terminate()
            for proc in servers:
                proc.wait(timeout=5)
            restarted = [command(db, 'status')['tip'] for db in databases]
            assert all(a == b for a, b in zip(after, restarted))
            print(json.dumps({
                'result': 'PASS', 'no_value': True, 'public_endpoint_exposed': False,
                'independent_operators': 0, 'local_node_processes': 4,
                'initial_heights': [4, 6, 8, 0], 'final_height': after[0]['height'],
                'final_hash': after[0]['hash'], 'state_root': after[0]['block']['state_root'],
                'new_blocks_per_node': accepted, 'fork_reorganizations': 2,
                'all_states_equal': True, 'supply_conserved': True,
                'repeat_sync_idempotent': True, 'restart_replay_identical': True,
                'services_left_running': False,
                'note': 'One machine, four local processes; not independent-operator qualification.'
            }, sort_keys=True, indent=2))
    finally:
        for proc in servers:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
            if proc.stdout:
                proc.stdout.close()
            if proc.stderr:
                proc.stderr.close()


if __name__ == '__main__':
    main()
