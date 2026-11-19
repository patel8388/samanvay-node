#!/usr/bin/env python3
"""Build a deterministic source ZIP from an already verified local source tree.
No dependency downloads, secret retrieval, public deployment or paid calls.
"""
import hashlib
import json
import re
import zipfile
from pathlib import Path
from samanvay import consensus, params

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT.parent / 'Samanvay_Debian12_Private_Testnet_Prep.zip'


def dump(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def main():
    tests = (ROOT / 'test-results.txt').read_text()
    totals = [int(number) for number in re.findall(r'Ran (\d+) tests', tests)]
    if len(totals) != 2 or tests.count('\nOK\n') != 2 or 'FAILED' in tests:
        raise RuntimeError('Run ./verify.sh > test-results.txt 2>&1 successfully before packaging')
    config_dir = ROOT / 'config'
    config_dir.mkdir(exist_ok=True)
    identities = {}
    for profile in ('devnet', 'rules'):
        config = params.default_config(profile)
        genesis = consensus.genesis(config)
        state = consensus.initial_state(config)
        identities[profile] = {'network_id': config['network_id'],
                               'genesis_hash': consensus.block_hash(genesis),
                               'config_digest': genesis['header']['config_digest'],
                               'initial_state_root': genesis['state_root']}
        dump(config_dir / (profile + '.json'), config)
        dump(config_dir / (profile + '-genesis.json'), genesis)
        dump(config_dir / (profile + '-initial-allocation.json'), {
            'no_value': True, 'issued_usamv': state['issued'],
            'founder_address': state['founder'], 'founder_unreleased_usamv': state['unreleased_initial'],
            'frozen_pool_balances_usamv': {address: state['balances'][address] for address in state['restricted']},
            'founder_fixture_key_is_public': True})
    dump(ROOT / 'release-status.json', {
        'version': '0.1.0.dev0', 'status': 'RUNNABLE_LOCAL_EXPERIMENT_ONLY',
        'mainnet_enabled': False, 'public_release_ready': False,
        'new_cash_spent': False, 'services_left_running': False,
        'node_tests_passed': totals[0], 'reference_tests_passed': totals[1],
        'demo_blocks': json.loads((ROOT / 'demo-results.json').read_text())['height'],
        'operator_rehearsal': json.loads((ROOT / 'operator-rehearsal-results.json').read_text()),
        'debian12_bundle': {'status': 'PREPARATION_ONLY_NOT_VPS_TESTED',
                            'installed_on_vps': False, 'ssh_access_used': False,
                            'requires_python': '3.12+', 'offline_dependencies_bundled': False,
                            'target_vcpu': 1, 'target_ram_gib': 1, 'target_disk_gib': 10},
        'profiles': identities,
        'not_implemented': ['qualified maintained upstream PoW base', 'independent review of prototype difficulty adjustment',
            'internet P2P', 'native mobile wallet', 'remote-miner pairing', 'sponsorship',
            'funded faucet', 'grant/council custody controller', 'lifetime social identity enforcement',
            'scalable pruning or authenticated claims', 'independent external security audit',
            'volunteer internet operators and public soak']})
    excluded_names = {'SHA256SUMS', 'CONTRACT.md'}
    def included(path):
        relative = path.relative_to(ROOT)
        return (path.is_file() and not any(part in {'__pycache__', '.git', '.local', '.venv', '.pytest_cache'} for part in relative.parts)
                and path.name not in excluded_names and path.suffix not in {'.pyc', '.db', '.key', '.sqlite3'}
                and '-wal' not in path.name and '-shm' not in path.name)
    files = sorted(path for path in ROOT.rglob('*') if included(path))
    checksums = ''.join(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + str(path.relative_to(ROOT)) + '\n'
                        for path in files)
    (ROOT / 'SHA256SUMS').write_text(checksums)
    files.append(ROOT / 'SHA256SUMS')
    with zipfile.ZipFile(OUTPUT, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(files):
            info = zipfile.ZipInfo('samanvay-node/' + str(path.relative_to(ROOT)), (2026, 10, 17, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100755 if path.suffix == '.sh' else 0o100644) << 16
            archive.writestr(info, path.read_bytes())
    print(str(OUTPUT))
    print('sha256', hashlib.sha256(OUTPUT.read_bytes()).hexdigest())
    print('files', len(files), 'bytes', OUTPUT.stat().st_size)


if __name__ == '__main__':
    main()
