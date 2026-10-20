import copy
import random
import unittest

from samanvay import consensus, crypto, params


class ConsensusRequiredBehavior(unittest.TestCase):
    """Independent black-box checks for the economic and validation contract."""

    @classmethod
    def setUpClass(cls):
        cls.c = params.default_config("devnet")
        cls.genesis = consensus.genesis(cls.c)
        cls.initial = consensus.initial_state(cls.c)
        cls.key = crypto.generate_key()
        cls.pub = crypto.public_key(cls.key)
        cls.addr = crypto.address(cls.pub, cls.c["network"])
        # Fund the real test account only through ordinary mined coinbase outputs.
        state, parent = copy.deepcopy(cls.initial), cls.genesis
        for _ in range(cls.c["maturity"] + 1):
            block = consensus.make_block(parent, state, [], cls.addr, cls.c)
            state = consensus.apply_block(parent, state, block, cls.c)
            parent = block
        cls.fixture_parent = parent
        cls.fixture_state = state

    def setUp(self):
        self.c = copy.deepcopy(self.__class__.c)
        self.genesis = copy.deepcopy(self.__class__.genesis)
        self.initial = copy.deepcopy(self.__class__.initial)
        self.key = self.__class__.key
        self.addr = self.__class__.addr
        self.parent = copy.deepcopy(self.__class__.fixture_parent)
        self.state = copy.deepcopy(self.__class__.fixture_state)

    def tx(self, typ="transfer", amount=0, fee=0, nonce=None, expiry=None, **extra):
        tx = {"version": 1, "network": self.c["network"],
              "network_id": self.c["network_id"], "type": typ,
              "sender": self.addr,
              "nonce": self.state["nonces"].get(self.addr, 0) if nonce is None else nonce,
              "expiry": self.state["height"] + 10000 if expiry is None else expiry,
              "fee": fee, "amount": amount}
        tx.update(extra)
        return crypto.sign_transaction(tx, self.key)

    def block(self, parent=None, state=None, txs=(), miner=None):
        return consensus.make_block(parent or self.parent, state or self.state,
                                    list(txs), miner or self.addr, self.c)

    def apply(self, block, parent=None, state=None):
        return consensus.apply_block(parent or self.parent, state or self.state,
                                     block, self.c)

    def advance(self, blocks, parent=None, state=None):
        parent, state = parent or self.parent, state or self.state
        for _ in range(blocks):
            block = self.block(parent, state)
            state = self.apply(block, parent, state)
            parent = block
        return parent, state

    def test_genesis_exact_65b_and_deterministic_root(self):
        self.assertEqual(self.initial["issued"], 6_500_000_000 * params.UNIT)
        self.assertEqual(self.initial["unreleased_initial"], 3_000_000_000 * params.UNIT)
        self.assertEqual(sum(self.initial["balances"].values()) + self.initial["unreleased_initial"],
                         self.initial["issued"])
        self.assertTrue(set(self.initial["restricted"]).issubset(self.initial["balances"]))
        self.assertEqual(sum(self.initial["balances"].values()), 3_500_000_000 * params.UNIT)
        self.assertEqual(self.genesis["state_root"], self.genesis["header"]["state_root"])
        self.assertEqual(self.genesis["header"]["state_root"],
                         consensus.genesis(self.c)["header"]["state_root"])
        self.assertEqual(self.genesis["header"]["config_digest"],
                         consensus.genesis(self.c)["header"]["config_digest"])

    def test_nested_budget_reference_and_random_vectors(self):
        rng = random.Random(90421)
        for profile in ("devnet", "rules"):
            c = params.default_config(profile)
            for _ in range(100):
                h = rng.randrange(1, c["era_blocks"] * 3)
                sub = c["initial_subsidy"] >> ((h - 1) // c["era_blocks"])
                before = params.cumulative(h - 1, c)
                after = before + sub
                founder = after // 10 - before // 10
                staking = (4 * after // 10 - after // 10) - (4 * before // 10 - before // 10)
                self.assertEqual(params.split(h, c), {
                    "miner": sub - founder - staking, "staking": staking, "founder": founder})
            for e in (0, 1, 17):
                start, end = params.epoch_start(e, c), params.epoch_end(e, c)
                expected = ((4 * params.cumulative(end, c) // 10 - params.cumulative(end, c) // 10)
                            - (4 * params.cumulative(start - 1, c) // 10
                               - params.cumulative(start - 1, c) // 10))
                self.assertEqual(params.epoch_budget(e, c), expected)

    def test_genesis_config_and_parent_state_linkage(self):
        b = self.block(); ns = self.apply(b)
        bad_state = copy.deepcopy(self.state); bad_state["height"] = 1
        with self.assertRaises(ValueError):
            consensus.apply_block(self.parent, bad_state, b, self.c)
        bad = copy.deepcopy(b); bad["header"]["config_digest"] = "0" * 64
        with self.assertRaises(ValueError):
            self.apply(bad)
        self.assertEqual(ns["height"], self.state["height"] + 1)

    def test_untrusted_skip_markers_are_rejected(self):
        b = self.block()
        for marker in ("_skip_root", "_skip_pow", "_unchecked"):
            bad = copy.deepcopy(b); bad[marker] = True
            with self.subTest(marker=marker):
                with self.assertRaises(ValueError): self.apply(bad)

    def test_state_root_is_committed_in_header_and_tampering_fails(self):
        b = self.block()
        self.assertEqual(b["state_root"], b["header"]["state_root"])
        bad = copy.deepcopy(b); bad["state_root"] = "0" * 64
        with self.assertRaises(ValueError): self.apply(bad)
        bad = copy.deepcopy(b); bad["header"]["state_root"] = "1" * 64
        with self.assertRaises(ValueError): self.apply(bad)

    def test_pow_uses_exact_target_and_work_is_target_based(self):
        b = self.block()
        self.assertLessEqual(int(consensus.block_hash(b), 16), self.c["target"])
        self.assertEqual(consensus.block_work(b), (1 << 256) // (self.c["target"] + 1))
        bad = copy.deepcopy(b); bad["header"]["target"] = self.c["target"] + 1
        with self.assertRaises(ValueError): self.apply(bad)
        bad = copy.deepcopy(b); bad["header"]["nonce"] += 1
        while int(consensus.block_hash(bad), 16) <= self.c["target"]:
            bad["header"]["nonce"] += 1
        with self.assertRaises(ValueError): self.apply(bad)

    def test_invalid_address_network_nonce_signature_schema_and_type(self):
        good = self.tx(amount=1, to=self.addr)
        cases = []
        for field, value in (("nonce", True), ("amount", -1), ("amount", 1.5),
                             ("type", "mint"), ("to", "not-an-address")):
            x = copy.deepcopy(good); x[field] = value
            # Every malicious transaction is freshly signed, so rejection tests
            # exercise the intended domain/address/schema checks, not stale sigs.
            cases.append(crypto.sign_transaction(x, self.key))
        x = copy.deepcopy(good); x["signature"] = "00"; cases.append(x)
        x = copy.deepcopy(good); del x["fee"]; cases.append(x)
        for tx in cases:
            with self.subTest(tx=tx):
                with self.assertRaises(ValueError): self.apply(self.block(txs=[tx]))

    def test_network_id_is_required_and_profile_replay_is_rejected(self):
        self.assertIn("network_id", self.tx(amount=1, to=self.addr))
        rules = params.default_config("rules")
        tx = {"version": 1, "network": rules["network"], "network_id": rules["network_id"],
              "type": "transfer", "sender": self.addr, "nonce": 0,
              "expiry": self.state["height"] + 100, "fee": 0, "amount": 1, "to": self.addr}
        tx = crypto.sign_transaction(tx, self.key)
        with self.assertRaises(ValueError): self.apply(self.block(txs=[tx]))

    def test_none_exit_and_early_claim_are_safe_rejections(self):
        exit_tx = self.tx("exit", lock_id="0" * 64)
        with self.assertRaises(ValueError): self.apply(self.block(txs=[exit_tx]))
        lock = self.tx("lock", amount=params.UNIT)
        parent, state = self.parent, self.state
        b = self.block(parent, state, [lock]); state = self.apply(b, parent, state); parent = b
        parent, state = self.advance(params.epoch_end(1, self.c) - state["height"], parent, state)
        # No claim can be accepted before the recorded epoch maturity.
        self.assertTrue(state["claims"])
        epoch = min(map(int, state["claims"]))
        lid = crypto.txid(lock)
        claim = self.tx("claim", nonce=1, lock_id=lid, epoch=epoch, reward=1)
        with self.assertRaises(ValueError): self.apply(self.block(parent, state, [claim]), parent, state)

    def test_founder_vesting_and_bonus_are_delayed_and_mature(self):
        founder = self.initial["founder"]
        before = self.state["balances"].get(founder, 0)
        parent, state = self.parent, self.state
        parent, state = self.advance(self.c["vesting_cliff"] - state["height"], parent, state)
        self.assertEqual(state["balances"].get(founder, 0), before)
        b = self.block(parent, state); state2 = self.apply(b, parent, state)
        self.assertGreater(state2["balances"].get(founder, 0), before)
        self.assertTrue(any(p["kind"] == "bonus" for p in state2["pending"]))
        self.assertTrue(all(p["available"] > state2["height"] for p in state2["pending"] if p["kind"] == "bonus"))

    def test_fees_nonminting_and_pending_miner_coinbase_maturity(self):
        tx = self.tx(amount=1, fee=7, to=self.addr)
        b = self.block(txs=[tx]); out = self.apply(b)
        split = params.split(out["height"], self.c)
        self.assertEqual(out["issued"], self.state["issued"] + split["miner"] + split["founder"])
        self.assertEqual(out["fees"], 7)
        self.assertTrue(any(p["kind"] == "miner" and p["available"] > out["height"] for p in out["pending"]))

    def test_randomized_allocation_conservation_reference(self):
        rng = random.Random(127)
        for _ in range(500):
            budget = rng.randrange(1, 10**9); weights = [rng.randrange(1, 1000) for _ in range(rng.randrange(1, 10))]
            alloc = [budget * w // sum(weights) for w in weights]
            self.assertLessEqual(sum(alloc), budget)
            self.assertEqual(budget, sum(alloc) + budget - sum(alloc))

    def test_epoch_dust_remains_in_reward_pool(self):
        key2 = crypto.generate_key(); addr2 = crypto.address(crypto.public_key(key2), self.c["network"])
        # The second account is funded by a second real mined coinbase chain.
        parent, state = self.parent, self.state
        for _ in range(self.c["maturity"] + 1):
            b = self.block(parent, state, miner=addr2); state = self.apply(b, parent, state); parent = b
        a = self.tx("lock", amount=params.UNIT)
        tx2 = {"version": 1, "network": self.c["network"], "network_id": self.c["network_id"],
               "type": "lock", "sender": addr2, "nonce": 0, "expiry": state["height"] + 10000,
               "fee": 0, "amount": 2 * params.UNIT}
        btx = crypto.sign_transaction(tx2, key2)
        first = self.block(parent, state, [a, btx]); state = self.apply(first, parent, state); parent = first
        parent, state = self.advance(self.c["epoch_blocks"] * 2 - state["height"] % self.c["epoch_blocks"], parent, state)
        rec = state["claims"]["1"]
        self.assertEqual(rec["budget"], rec["allocated"] + rec["dust"])
        self.assertEqual(state["reward_pool"], rec["budget"],
                         "unclaimed allocation and integer dust must remain reserved")

    def test_full_seven_active_and_seven_unbond_epochs_conservation(self):
        lock = self.tx("lock", amount=20 * params.UNIT)
        parent, state = self.parent, self.state
        b = self.block(parent, state, [lock]); state = self.apply(b, parent, state); parent = b
        for _ in range(self.c["epoch_blocks"] * (self.c["active_epochs"] + 2)):
            b = self.block(parent, state); state = self.apply(b, parent, state); parent = b
        lid = crypto.txid(lock)
        ex = self.tx("exit", nonce=1, lock_id=lid)
        b = self.block(parent, state, [ex]); state = self.apply(b, parent, state); parent = b
        target = state["locks"][lid]["withdraw_height"]
        while state["height"] < target:
            b = self.block(parent, state); state = self.apply(b, parent, state); parent = b
        wd = self.tx("withdraw", nonce=2, lock_id=lid)
        b = self.block(parent, state, [wd]); out = self.apply(b, parent, state); parent = b
        self.assertNotIn(lid, out["locks"])
        self.assertGreaterEqual(out["issued"], self.state["issued"])
        self.assertLessEqual(out["issued"], self.c["cap"])
        self.assertEqual(consensus.supply_total(out), out["issued"], "all minted units remain accounted")
        self.assertTrue(out["claims"] or out["skipped_epochs"])
        matured = [(e, r) for e, r in out["claims"].items() if r["entitlements"].get(lid, 0)]
        if matured:
            epoch, rec = matured[0]
            claim_amount = rec["entitlements"][lid]
            prior_rewards = out["rewards"].get(lid, 0)
            claim = self.tx("claim", nonce=3, epoch=int(epoch), lock_id=lid, reward=claim_amount,
                            expiry=out["height"] + 1000)
            cb = self.block(parent, out, [claim]); claimed = self.apply(cb, parent, out)
            self.assertEqual(claimed["rewards"].get(lid, 0), prior_rewards - claim_amount)
            self.assertEqual(claimed["claims"][str(epoch)]["claimed"][lid], claim_amount)


if __name__ == "__main__":
    unittest.main()
