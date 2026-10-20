import json, tempfile, threading, unittest
from pathlib import Path
from samanvay.chain import Chain
from samanvay import consensus, params
from samanvay.server import _peer_url

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.td=tempfile.TemporaryDirectory(); self.path=Path(self.td.name)/'a.sqlite3'
        self.c=Chain(self.path, params.default_config('devnet'))
    def tearDown(self): self.c.close(); self.td.cleanup()
    def test_genesis_work_is_zero_and_replay_is_deterministic(self):
        genesis=self.c.tip; self.assertEqual(genesis['work'],0)
        self.assertEqual(self.c.state(), self.c.tip['state'])
        self.c.close(); self.c=Chain(self.path, params.default_config('devnet'))
        self.assertEqual(self.c.tip['hash'],genesis['hash']); self.assertEqual(self.c.state(),genesis['state'])
    def test_rejects_invalid_block_atomically(self):
        before=self.c.tip['hash']; bad={'header':{'parent':before}}
        with self.assertRaises(ValueError): self.c.add_block(bad)
        self.assertEqual(self.c.tip['hash'],before)
        self.assertEqual(self.c.db.execute('select count(*) from blocks').fetchone()[0],1)
    def test_work_column_is_text_and_decimal(self):
        typ=self.c.db.execute('pragma table_info(blocks)').fetchall()[4][2]
        self.assertEqual(typ.upper(),'TEXT')
        self.assertIsInstance(self.c.db.execute('select work from blocks').fetchone()[0],str)
    def test_literal_loopback_peer_only(self):
        self.assertEqual(_peer_url('http://127.0.0.1:8765').hostname,'127.0.0.1')
        for url in ('http://localhost:8765','http://8.8.8.8:80','https://127.0.0.1:1'):
            with self.assertRaises(ValueError): _peer_url(url)
    def test_config_commitment_rejects_altered_genesis(self):
        altered=params.default_config('devnet').copy(); altered['network_id']='altered'
        with self.assertRaises(ValueError): Chain(self.path, altered)

if __name__=='__main__': unittest.main()
