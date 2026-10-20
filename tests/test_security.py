import copy
import unittest
from samanvay import consensus, crypto, params


class SecurityRegressionTests(unittest.TestCase):
    def setUp(self):
        self.c = params.default_config()
        self.p = consensus.genesis(self.c)
        self.s = consensus.initial_state(self.c)
        self.key = crypto.generate_key()
        self.addr = crypto.address(crypto.public_key(self.key))
        for _ in range(4):
            self.step()

    def step(self, transactions=()):
        block = consensus.make_block(self.p, self.s, list(transactions), self.addr, self.c)
        self.s = consensus.apply_block(self.p, self.s, block, self.c)
        self.p = block
        self.assertEqual(consensus.supply_total(self.s), self.s['issued'])
        return block

    def tx(self, kind='transfer', key=None, **fields):
        key = key or self.key
        address = crypto.address(crypto.public_key(key))
        return crypto.sign_transaction(dict(version=1, network='tSAMV',
            network_id=self.c['network_id'], type=kind, sender=address,
            nonce=self.s['nonces'].get(address, 0), expiry=self.s['height']+100,
            fee=0, **fields), key)

    def test_same_height_state_injection_rejected(self):
        state = copy.deepcopy(self.s)
        state['balances'][self.addr] += 1
        state['issued'] += 1  # Even internally conserved state must match parent commitment.
        with self.assertRaises(ValueError):
            consensus.make_block(self.p, state, [], self.addr, self.c)

    def test_resigned_wrong_recipient_extra_fields_and_bool_amount(self):
        for fields in ({'to': 'bogus', 'amount': 1},
                       {'to': self.addr, 'amount': True},
                       {'to': self.addr, 'amount': 1, 'mint': 10},
                       {'to': self.addr, 'amount': params.CAP+1}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                consensus.make_block(self.p, self.s, [self.tx(**fields)], self.addr, self.c)

    def test_signed_profile_replay_is_rejected(self):
        transaction = self.tx(to=self.addr, amount=1)
        transaction['network_id'] = params.default_config('rules')['network_id']
        transaction = crypto.sign_transaction(transaction, self.key)
        with self.assertRaises(ValueError):
            self.step([transaction])

    def test_exact_envelope_and_boolean_header_fields_rejected(self):
        block = consensus.make_block(self.p, self.s, [], self.addr, self.c)
        for field in ('height', 'version', 'target', 'timestamp', 'nonce'):
            bad = copy.deepcopy(block)
            bad['header'][field] = True
            with self.subTest(field=field), self.assertRaises(ValueError):
                consensus.apply_block(self.p, self.s, bad, self.c)
        bad = copy.deepcopy(block)
        bad['admin_override'] = True
        with self.assertRaises(ValueError):
            consensus.apply_block(self.p, self.s, bad, self.c)

    def test_two_staker_dust_is_funded_and_cannot_be_swept(self):
        key2 = crypto.generate_key()
        addr2 = crypto.address(crypto.public_key(key2))
        self.step([self.tx(to=addr2, amount=10*params.UNIT)])
        tx1 = self.tx('lock', amount=params.UNIT)
        tx2 = self.tx('lock', key=key2, amount=2*params.UNIT)
        self.step([tx1, tx2])
        while self.s['height'] < 24:
            self.step()
        record = self.s['claims']['1']
        self.assertEqual(record['budget'], params.epoch_budget(1, self.c))
        self.assertEqual(record['dust'], 1)
        self.assertEqual(self.s['reward_pool'], record['budget'])
        lid = crypto.txid(tx1)
        while self.s['height'] < record['mature']-1:
            self.step()
        reward = record['entitlements'][lid]
        self.step([self.tx('claim', epoch=1, lock_id=lid, reward=reward)])
        with self.assertRaises(ValueError):
            self.step([self.tx('claim', epoch=1, lock_id=lid, reward=1)])
        self.assertEqual(self.s['claims']['1']['dust'], 1)

    def test_founder_fixture_key_is_bound_to_vesting_address(self):
        founder = crypto.address(crypto.public_key(consensus.TEST_ONLY_FOUNDER_PRIVATE_KEY))
        self.assertEqual(founder, self.s['founder'])
        while self.s['height'] < self.c['vesting_cliff']:
            self.step()
        self.assertEqual(self.s['balances'][founder], 0)
        self.step()
        released = 3_000_000_000*params.UNIT//self.c['vesting_period']
        self.assertGreaterEqual(self.s['balances'][founder], released)
        tx = self.tx('lock', key=consensus.TEST_ONLY_FOUNDER_PRIVATE_KEY, amount=params.UNIT)
        self.step([tx])
        self.assertIn(crypto.txid(tx), self.s['locks'])


if __name__ == '__main__':
    unittest.main()
