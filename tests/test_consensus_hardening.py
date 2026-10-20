import sqlite3
import tempfile
import unittest
from pathlib import Path

from samanvay import consensus, crypto, params
from samanvay.chain import Chain


class ConsensusHardeningTests(unittest.TestCase):
    def setUp(self):
        self.config = params.default_config("devnet")
        self.genesis = consensus.genesis(self.config)
        self.state = consensus.initial_state(self.config)
        self.key = crypto.generate_key()
        self.miner = crypto.address(crypto.public_key(self.key), self.config["network"])
        self.parent = self.genesis
        self.state = consensus.initial_state(self.config)
        for _ in range(self.config["maturity"] + 1):
            block = consensus.make_block(self.parent, self.state, [], self.miner, self.config)
            self.state = consensus.apply_block(self.parent, self.state, block, self.config)
            self.parent = block

    def test_generator_transactions_cannot_be_dropped(self):
        bad_tx = {"not": "a transaction"}
        with self.assertRaises(ValueError):
            consensus.make_block(self.parent, self.state, (tx for tx in (bad_tx,)),
                                 self.miner, self.config)

    def test_valid_generator_executes_signed_transfer(self):
        recipient = crypto.address(crypto.public_key(crypto.generate_key()), self.config['network'])
        tx = crypto.sign_transaction({
            'version': 1, 'network': self.config['network'],
            'network_id': self.config['network_id'], 'type': 'transfer',
            'sender': self.miner, 'to': recipient, 'amount': 1, 'fee': 0,
            'nonce': 0, 'expiry': self.state['height'] + 10}, self.key)
        block = consensus.make_block(self.parent, self.state, iter([tx]), self.miner, self.config)
        result = consensus.apply_block(self.parent, self.state, block, self.config)
        self.assertEqual(block['transactions'], [tx])
        self.assertEqual(result['balances'][recipient], 1)
        self.assertEqual(result['nonces'][self.miner], 1)

    def test_failed_reindex_rolls_back_earlier_cache_repairs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'chain.sqlite3'
            chain = Chain(path, self.config)
            chain.mine(self.miner)
            chain.close()
            db = sqlite3.connect(path)
            db.execute("UPDATE blocks SET state='{}' WHERE height=0")
            db.execute('UPDATE blocks SET parent=? WHERE height=1', ('0' * 64,))
            db.commit()
            db.close()
            with self.assertRaises(ValueError):
                Chain(path, self.config)
            db = sqlite3.connect(path)
            try:
                self.assertEqual(db.execute('SELECT state FROM blocks WHERE height=0').fetchone()[0], '{}')
            finally:
                db.close()

    def test_supplied_ancestors_must_end_at_parent(self):
        block = consensus.make_block(self.parent, self.state, [], self.miner, self.config)
        with self.assertRaises(ValueError):
            consensus.apply_block(self.parent, self.state, block, self.config,
                                  ancestors=[self.genesis])

    def test_reindex_rejects_tampered_row_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "chain.sqlite3"
            chain = Chain(path, self.config)
            chain.mine(self.miner)
            chain.close()
            db = sqlite3.connect(path)
            db.execute("UPDATE blocks SET parent=? WHERE height=1", ("0" * 64,))
            db.commit()
            db.close()
            with self.assertRaises(ValueError):
                Chain(path, self.config)

    def test_reindex_rejects_tampered_genesis_work(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "chain.sqlite3"
            chain = Chain(path, self.config)
            chain.close()
            db = sqlite3.connect(path)
            db.execute("UPDATE blocks SET work=? WHERE height=0", ("1",))
            db.commit()
            db.close()
            with self.assertRaises(ValueError):
                Chain(path, self.config)


if __name__ == "__main__":
    unittest.main()
