"""Bounded, disposable local tSAMV consensus. NOT a production protocol.

Consensus validation has no input-controlled bypass. Mining calls a private
transition function, then validates the fully mined result through apply_block.
"""
import copy
import hashlib
import re
import time
from . import params, crypto

# Public fixture, not a secret. This genesis must NEVER hold anything valuable.
TEST_ONLY_FOUNDER_PRIVATE_KEY = '00' * 32
ADDRESS = re.compile(r's[0-9a-f]{39}\Z')
HASH = re.compile(r'[0-9a-f]{64}\Z')
HEADER_FIELDS = {'version', 'height', 'parent', 'timestamp', 'nonce', 'miner',
                 'txids', 'network_id', 'target', 'config_digest', 'state_root'}
FOUNDER_INITIAL = 3_000_000_000 * params.UNIT


def _root(state):
    return crypto.sha256d(crypto.canonical(state))


def _digest(c):
    return crypto.sha256d(crypto.canonical(c))


def _check_config(c):
    if (not isinstance(c, dict)
            or crypto.canonical(c) != crypto.canonical(params.default_config(c.get('profile')))):
        raise ValueError('only the complete pinned local profiles are supported')


def _address(value):
    return isinstance(value, str) and ADDRESS.fullmatch(value) is not None


def _amount(value):
    return type(value) is int and 0 <= value <= params.CAP


def _addr(label, c):
    if label == 'founder':
        public = crypto.public_key(TEST_ONLY_FOUNDER_PRIVATE_KEY)
    else:
        public = hashlib.sha256((c['network_id'] + '|' + label).encode()).hexdigest()
    return crypto.address(public, c['network'])


def initial_state(c):
    _check_config(c)
    founder = _addr('founder', c)
    pools = {_addr('developer', c): 2_000_000_000 * params.UNIT,
             _addr('treasury', c): 1_000_000_000 * params.UNIT,
             _addr('distribution', c): 500_000_000 * params.UNIT}
    return {'height': 0, 'issued': params.INITIAL, 'balances': {founder: 0, **pools},
            'pending': [], 'unreleased_initial': FOUNDER_INITIAL,
            'founder_released': 0, 'founder': founder,
            'restricted': {address: 'frozen-pool' for address in pools},
            'nonces': {}, 'locks': {}, 'rewards': {}, 'reward_pool': 0,
            'claims': {}, 'claim_owners': {}, 'fees': 0, 'skipped_epochs': [],
            'epoch_snapshot': None, 'config_digest': _digest(c)}


def genesis(c):
    state = initial_state(c)
    header = {'version': 1, 'height': 0, 'parent': '0' * 64, 'timestamp': 0,
              'nonce': 0, 'miner': '', 'txids': [], 'network_id': c['network_id'],
              'target': c['target'], 'config_digest': _digest(c),
              'state_root': _root(state)}
    return {'header': header, 'transactions': [], 'state_root': header['state_root']}


def block_hash(block):
    try:
        return crypto.sha256d(crypto.canonical(block['header']))
    except (KeyError, TypeError) as exc:
        raise ValueError('invalid block header') from exc


def _header_hash(header):
    try:
        return crypto.sha256d(crypto.canonical(header))
    except (TypeError, ValueError) as exc:
        raise ValueError('invalid ancestor header') from exc


def block_work(block):
    target = block['header'].get('target')
    if type(target) is not int or not 0 <= target < (1 << 256):
        raise ValueError('invalid target')
    return (1 << 256) // (target + 1)


def supply_total(state):
    """Reward entitlements are backing claims on reward_pool, not extra coins."""
    return (sum(state['balances'].values()) + sum(p['amount'] for p in state['pending'])
            + state['unreleased_initial'] + sum(x['amount'] for x in state['locks'].values())
            + state['reward_pool'])


def _state_limits(state, c):
    if (len(state['balances']) > c['max_accounts'] or len(state['locks']) > c['max_locks']
            or len(state['claims']) > c['max_epochs']
            or len(state['claim_owners']) > c['max_claims']
            or len(state['skipped_epochs']) > c['max_epochs']
            or len(state['pending']) > c['max_pending']
            or len(crypto.canonical(state)) > c['max_state_bytes']):
        raise ValueError('consensus state limit; reset disposable devnet')
    if not 0 <= state['issued'] <= c['cap'] or supply_total(state) != state['issued']:
        raise ValueError('supply conservation')
    if any(not _amount(v) for v in state['balances'].values()):
        raise ValueError('invalid balance')
    if state['reward_pool'] < 0 or state['unreleased_initial'] < 0:
        raise ValueError('negative reserve')


def _validate_tx(tx, c, height):
    if not isinstance(tx, dict) or len(crypto.canonical(tx)) > c['max_tx_bytes']:
        raise ValueError('transaction size/type')
    base = {'version', 'network', 'network_id', 'type', 'sender', 'nonce',
            'expiry', 'fee', 'public_key', 'signature'}
    extensions = {'transfer': {'amount', 'to'}, 'lock': {'amount'},
                  'exit': {'lock_id'}, 'withdraw': {'lock_id'},
                  'claim': {'lock_id', 'epoch', 'reward'}}
    kind = tx.get('type')
    if not isinstance(kind, str) or kind not in extensions:
        raise ValueError('transaction type')
    required = base | extensions[kind]
    # Optional zero amount on operations that do not move ordinary principal.
    permitted = required | ({'amount'} if kind in ('exit', 'withdraw', 'claim') else set())
    if set(tx) - permitted or not required <= set(tx):
        raise ValueError('transaction schema')
    if (type(tx['version']) is not int or tx['version'] != 1
            or tx['network'] != c['network'] or tx['network_id'] != c['network_id']
            or not _address(tx['sender']) or type(tx['nonce']) is not int
            or not 0 <= tx['nonce'] < (1 << 63) or type(tx['expiry']) is not int
            or not height <= tx['expiry'] <= height + c['max_expiry']
            or not _amount(tx['fee']) or not _amount(tx.get('amount', 0))):
        raise ValueError('transaction domain/type/amount/expiry')
    if kind in ('exit', 'withdraw', 'claim') and tx.get('amount', 0) != 0:
        raise ValueError('unexpected principal debit')
    if kind == 'transfer' and (not _address(tx['to']) or tx['amount'] <= 0):
        raise ValueError('invalid transfer')
    if kind in ('exit', 'withdraw', 'claim') and (not isinstance(tx['lock_id'], str)
                                                or not HASH.fullmatch(tx['lock_id'])):
        raise ValueError('invalid lock id')
    if kind == 'claim' and (type(tx['epoch']) is not int or tx['epoch'] < 0
                            or not _amount(tx['reward']) or tx['reward'] == 0):
        raise ValueError('invalid claim')
    if not crypto.verify_transaction_signature(tx):
        raise ValueError('signature')


def _credit(state, address, amount, c):
    if not _address(address) or not _amount(amount):
        raise ValueError('invalid account/credit')
    if address not in state['balances'] and len(state['balances']) >= c['max_accounts']:
        raise ValueError('account limit')
    state['balances'][address] = state['balances'].get(address, 0) + amount


def _release(state, height, c):
    remaining = []
    for payment in state['pending']:
        if payment['available'] <= height:
            _credit(state, payment['owner'], payment['amount'], c)
        else:
            remaining.append(payment)
    state['pending'] = remaining
    # No release during the cliff; first linear tranche at cliff + 1.
    elapsed = max(0, min(c['vesting_period'], height - c['vesting_cliff']))
    vested = FOUNDER_INITIAL * elapsed // c['vesting_period']
    delta = vested - state['founder_released']
    if delta < 0:
        raise ValueError('founder release regression')
    state['founder_released'] = vested
    state['unreleased_initial'] -= delta
    _credit(state, state['founder'], delta, c)


def _snapshot(state, height, c):
    if (height - 1) % c['epoch_blocks']:
        return
    weights = {lid: lock['amount'] for lid, lock in state['locks'].items()
               if lock['active_from'] <= height
               and (lock['exit_effective'] is None or lock['exit_effective'] > height)}
    state['epoch_snapshot'] = {'epoch': params.epoch_of(height, c), 'weights': weights,
                               'total': sum(weights.values()), 'budget': 0}


def _settle(state, height, c):
    if height % c['epoch_blocks']:
        return
    snap = state['epoch_snapshot']
    epoch = snap['epoch']
    if not snap['total']:
        state['skipped_epochs'].append(epoch)
        return
    budget = snap['budget']
    entitlements = {lid: budget * amount // snap['total']
                    for lid, amount in sorted(snap['weights'].items())}
    allocated = sum(entitlements.values())
    for lid, amount in entitlements.items():
        state['rewards'][lid] = state['rewards'].get(lid, 0) + amount
        state['claim_owners'][lid] = state['locks'][lid]['owner']
    state['claims'][str(epoch)] = {'budget': budget, 'allocated': allocated,
                                 'dust': budget - allocated,
                                 'mature': height + c['maturity'],
                                 'entitlements': entitlements, 'claimed': {}}
    # No minting here. Every block already issued its entire staking share into
    # the restricted pool. Dust has no claimant and can never be swept.


def _transition(state, block, c):
    ns = copy.deepcopy(state)
    height = block['header']['height']
    ns['height'] = height
    _release(ns, height, c)
    _snapshot(ns, height, c)  # Before transactions; no same-boundary front-running.
    fees, senders = 0, set()
    for tx in block['transactions']:
        _validate_tx(tx, c, height)
        sender, kind = tx['sender'], tx['type']
        if sender in ns['restricted']:
            raise ValueError('frozen genesis custody; no grant controller implemented')
        if sender in senders or tx['nonce'] != ns['nonces'].get(sender, 0):
            raise ValueError('nonce/replay; one transaction per sender per block')
        senders.add(sender)
        amount = tx.get('amount', 0)
        cost = amount + tx['fee']
        if ns['balances'].get(sender, 0) < cost:
            raise ValueError('insufficient available funds')
        _credit(ns, sender, 0, c)
        ns['balances'][sender] -= cost
        ns['nonces'][sender] = tx['nonce'] + 1
        fees += tx['fee']
        if kind == 'transfer':
            _credit(ns, tx['to'], amount, c)
        elif kind == 'lock':
            if amount < params.UNIT or len(ns['locks']) >= c['max_locks']:
                raise ValueError('stake minimum/limit')
            lid = crypto.txid(tx)
            ns['locks'][lid] = {'owner': sender, 'amount': amount, 'created': height,
                                 'active_from': params.activation_height(height, c),
                                 'exit_effective': None, 'withdraw_height': None}
        elif kind == 'exit':
            lock = ns['locks'].get(tx['lock_id'])
            if not lock or lock['owner'] != sender or lock['exit_effective'] is not None:
                raise ValueError('invalid exit owner/status')
            effective = params.exit_effective_height(lock['created'], height, c)
            lock['exit_effective'] = effective
            lock['withdraw_height'] = params.withdraw_height(effective, c)
        elif kind == 'withdraw':
            lock = ns['locks'].get(tx['lock_id'])
            if (not lock or lock['owner'] != sender or lock['withdraw_height'] is None
                    or height < lock['withdraw_height']):
                raise ValueError('invalid withdrawal owner/height')
            _credit(ns, sender, lock['amount'], c)
            del ns['locks'][tx['lock_id']]
        else:
            lid, epoch, amount = tx['lock_id'], tx['epoch'], tx['reward']
            record = ns['claims'].get(str(epoch))
            if ns['claim_owners'].get(lid) != sender or not record or height < record['mature']:
                raise ValueError('claim ownership/maturity')
            paid = record['claimed'].get(lid, 0)
            if paid + amount > record['entitlements'].get(lid, 0):
                raise ValueError('claim exceeds entitlement')
            record['claimed'][lid] = paid + amount
            ns['rewards'][lid] -= amount
            ns['reward_pool'] -= amount
            _credit(ns, sender, amount, c)
    split = params.split(height, c)
    miner = block['header']['miner']
    # Fees are existing funds; both subsidy and fees are coinbase-matured.
    for kind, owner, amount, delay in (
        ('miner', miner, split['miner'] + fees, c['maturity']),
        ('bonus', ns['founder'], split['founder'],
         max(c['maturity'], c['founder_bonus_maturity']))):
        if amount:
            ns['pending'].append({'kind': kind, 'owner': owner, 'amount': amount,
                                  'created': height, 'available': height + delay})
    ns['fees'] += fees
    ns['issued'] += split['miner'] + split['founder']
    snapshot = ns['epoch_snapshot']
    if snapshot['total']:
        snapshot['budget'] += split['staking']
        ns['reward_pool'] += split['staking']
        ns['issued'] += split['staking']
    _settle(ns, height, c)
    _state_limits(ns, c)
    return ns


def _validate_envelope(parent, state, block, c, ancestors):
    _check_config(c)
    if (not isinstance(parent, dict) or not isinstance(parent.get('header'), dict)
            or not isinstance(state, dict)):
        raise ValueError('invalid parent/state')
    if (not isinstance(block, dict) or set(block) != {'header', 'transactions', 'state_root'}
            or len(crypto.canonical(block)) > c['max_block_bytes']):
        raise ValueError('block schema/size')
    header = block['header']
    if not isinstance(header, dict) or set(header) != HEADER_FIELDS:
        raise ValueError('header schema')
    if (state.get('config_digest') != _digest(c)
            or state.get('height') != parent['header']['height']
            or _root(state) != parent['header']['state_root']
            or parent.get('state_root') != parent['header']['state_root']):
        raise ValueError('parent state commitment')
    _state_limits(state, c)
    for key in ('version', 'height', 'timestamp', 'nonce', 'target'):
        if type(header[key]) is not int:
            raise ValueError('header integer type')
    if (header['version'] != 1 or header['height'] != state['height'] + 1
            or header['height'] > c['max_blocks'] or header['parent'] != block_hash(parent)
            or header['network_id'] != c['network_id'] or header['config_digest'] != _digest(c)
            or header['target'] != c['target'] or not 0 <= header['nonce'] < (1 << 64)
            or not _address(header['miner'])):
        raise ValueError('header domain/parent/target/limits')
    txs = block['transactions']
    if (not isinstance(txs, list) or len(txs) > c['max_transactions']
            or header['txids'] != [crypto.txid(tx) for tx in txs]
            or not isinstance(header['state_root'], str) or not HASH.fullmatch(header['state_root'])
            or block['state_root'] != header['state_root']):
        raise ValueError('transaction/state commitment')
    # Nondecreasing parent clock plus strict median-of-up-to-11 prior headers.
    # For a tiny local network this is intentionally not a public DAA/time design.
    if header['timestamp'] < parent['header']['timestamp'] or header['timestamp'] > int(time.time()) + c['future_seconds']:
        raise ValueError('timestamp bounds')
    if ancestors is not None and not isinstance(ancestors, list):
        raise ValueError('invalid ancestor list')
    supplied = ancestors or []
    if len(supplied) > 11:
        supplied = supplied[-11:]
    prior = []
    for index, item in enumerate(supplied):
        if not isinstance(item, dict):
            raise ValueError('invalid ancestor')
        ancestor_header = item.get('header', item)
        if not isinstance(ancestor_header, dict):
            raise ValueError('invalid ancestor header')
        prior.append(ancestor_header)
        if index:
            previous = supplied[index - 1]
            previous_header = previous.get('header', previous)
            if ancestor_header.get('parent') != _header_hash(previous_header):
                raise ValueError('disconnected ancestors')
    if prior and prior[-1] != parent['header']:
        raise ValueError('ancestor tip mismatch')
    if not prior or prior[-1] != parent['header']:
        prior.append(parent['header'])
    times = sorted(item['timestamp'] for item in prior[-11:])
    if header['timestamp'] <= times[len(times) // 2]:
        raise ValueError('timestamp median')


def apply_block(parent, state, block, c, ancestors=None):
    _validate_envelope(parent, state, block, c, ancestors)
    if int(block_hash(block), 16) > c['target']:
        raise ValueError('insufficient proof of work')
    result = _transition(state, block, c)
    if _root(result) != block['header']['state_root']:
        raise ValueError('invalid computed state root')
    return result


def make_block(parent, state, transactions, miner_address, c, timestamp=None, ancestors=None):
    _check_config(c)
    try:
        transactions = list(transactions)
    except TypeError as exc:
        raise ValueError('transactions must be iterable') from exc
    # Explicit historical timestamps remain possible in tests, but must validate.
    if timestamp is None:
        timestamp = max(int(time.time()), parent['header']['timestamp'] + 1)
    header = {'version': 1, 'height': state['height'] + 1, 'parent': block_hash(parent),
              'timestamp': timestamp, 'nonce': 0, 'miner': miner_address,
              'txids': [crypto.txid(tx) for tx in transactions], 'network_id': c['network_id'],
              'target': c['target'], 'config_digest': _digest(c), 'state_root': '0' * 64}
    block = {'header': header, 'transactions': transactions, 'state_root': '0' * 64}
    _validate_envelope(parent, state, block, c, ancestors)
    root = _root(_transition(state, block, c))
    header['state_root'] = block['state_root'] = root
    for nonce in range(1_000_000):
        header['nonce'] = nonce
        if int(block_hash(block), 16) <= c['target']:
            return block
    raise ValueError('finite local mining attempt limit')
