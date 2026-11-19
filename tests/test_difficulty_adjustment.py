import copy
import tempfile
import unittest
from pathlib import Path

from samanvay import consensus, crypto, params
from samanvay.chain import Chain


class DifficultyAdjustmentTests(unittest.TestCase):
    def setUp(self):
        self.config = params.default_config("devnet")
        self.parent = consensus.genesis(self.config)
        self.state = consensus.initial_state(self.config)
        self.history = [self.parent]
        self.miner = crypto.address(crypto.public_key(crypto.generate_key()),
                                    self.config["network"])

    def mine_at(self, timestamp):
        block = consensus.make_block(self.parent, self.state, [], self.miner,
                                      self.config, timestamp=timestamp,
                                      ancestors=self.history)
        self.state = consensus.apply_block(self.parent, self.state, block,
                                           self.config, ancestors=self.history)
        self.parent = block
        self.history.append(block)
        return block

    def test_profiles_pin_distinct_retarget_windows_and_replay_domains(self):
        devnet = params.default_config("devnet")
        rules = params.default_config("rules")
        self.assertEqual((devnet["target_spacing"], devnet["retarget_interval"],
                          devnet["max_adjustment_factor"]), (1, 12, 4))
        self.assertEqual((rules["target_spacing"], rules["retarget_interval"],
                          rules["max_adjustment_factor"]), (600, 2016, 4))
        self.assertNotEqual(devnet["network_id"], rules["network_id"])
        self.assertTrue(devnet["network_id"].endswith("-v4"))
        self.assertTrue(rules["network_id"].endswith("-v4"))

    def test_retarget_has_factor_four_bounds_and_never_exceeds_pow_limit(self):
        factor = self.config["max_adjustment_factor"]
        pow_limit = self.config["target"]
        parent_target = pow_limit // 8
        expected = 100
        self.assertEqual(consensus._retarget_target(parent_target, 0, expected,
                                                    pow_limit, factor), parent_target // 4)
        self.assertEqual(consensus._retarget_target(parent_target, 25, expected,
                                                    pow_limit, factor), parent_target // 4)
        self.assertEqual(consensus._retarget_target(parent_target, expected, expected,
                                                    pow_limit, factor), parent_target)
        self.assertEqual(consensus._retarget_target(parent_target, 4 * expected,
                                                    expected, pow_limit, factor),
                         parent_target * 4)
        self.assertEqual(consensus._retarget_target(parent_target, 4 * expected + 1,
                                                    expected, pow_limit, factor),
                         parent_target * 4)
        self.assertEqual(consensus._retarget_target(pow_limit // 2, 8 * expected,
                                                    expected, pow_limit, factor),
                         pow_limit)
        self.assertEqual(consensus._retarget_target(2, 0, expected,
                                                    pow_limit, factor), 1)

    def test_bad_retarget_inputs_are_rejected(self):
        pow_limit = self.config["target"]
        for args in ((0, 1, 1, pow_limit, 4),
                     (1, -1, 1, pow_limit, 4),
                     (1, 0, 0, pow_limit, 4),
                     (1, 0, 1, pow_limit, True),
                     (1, 0, 1, pow_limit, 1)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                consensus._retarget_target(*args)

    def test_first_full_window_keeps_target_and_resets_committed_history(self):
        for timestamp in range(1, self.config["retarget_interval"] + 1):
            block = self.mine_at(timestamp)
            self.assertEqual(block["header"]["target"], self.config["target"])
            self.assertEqual(len(self.state["difficulty_timestamps"]), timestamp)
        self.assertEqual(self.state["difficulty_timestamps"],
                         list(range(1, self.config["retarget_interval"] + 1)))

        next_block = consensus.make_block(self.parent, self.state, [], self.miner,
                                          self.config, timestamp=13)
        self.assertEqual(next_block["header"]["target"], self.config["target"])
        self.state = consensus.apply_block(self.parent, self.state, next_block,
                                           self.config)
        self.parent = next_block
        self.assertEqual(self.state["difficulty_timestamps"], [13])

    def test_completed_fast_window_adjusts_target_from_committed_timestamps(self):
        # This nondecreasing sequence satisfies the existing median-time rule;
        # its 12-block endpoint span is 3 seconds versus the 11-second target.
        timestamps = (1, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 4)
        for timestamp in timestamps:
            self.mine_at(timestamp)
        expected = self.config["target_spacing"] * (self.config["retarget_interval"] - 1)
        expected_target = self.config["target"] * 3 // expected
        block = consensus.make_block(self.parent, self.state, [], self.miner,
                                     self.config, timestamp=5,
                                     ancestors=self.history)
        self.assertEqual(block["header"]["target"], expected_target)
        self.assertLessEqual(int(consensus.block_hash(block), 16), expected_target)
        self.state = consensus.apply_block(self.parent, self.state, block,
                                           self.config, ancestors=self.history)
        self.parent = block
        self.history.append(block)
        self.assertEqual(self.state["difficulty_timestamps"], [5])

    def test_block_target_is_derived_from_parent_state_and_cannot_be_overridden(self):
        for timestamp in range(1, self.config["retarget_interval"] + 1):
            self.mine_at(timestamp)
        block = consensus.make_block(self.parent, self.state, [], self.miner,
                                     self.config, timestamp=13)
        altered = copy.deepcopy(block)
        altered["header"]["target"] -= 1
        with self.assertRaisesRegex(ValueError, "header domain/parent/target/limits"):
            consensus.apply_block(self.parent, self.state, altered, self.config)

    def test_window_shape_and_monotonicity_are_state_invariants(self):
        state = consensus.initial_state(self.config)
        parent = consensus.genesis(self.config)
        block = consensus.make_block(parent, state, [], self.miner, self.config,
                                     timestamp=1)
        state = consensus.apply_block(parent, state, block, self.config)
        malformed = copy.deepcopy(state)
        malformed["difficulty_timestamps"] = []
        with self.assertRaisesRegex(ValueError, "invalid difficulty timestamp window"):
            consensus._state_limits(malformed, self.config)
        malformed = copy.deepcopy(state)
        malformed["difficulty_timestamps"] = [True]
        with self.assertRaisesRegex(ValueError, "invalid difficulty timestamp window"):
            consensus._state_limits(malformed, self.config)

    def test_branch_local_retarget_drives_cumulative_work_and_restart_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "difficulty-fork.sqlite3"
            chain = Chain(path, self.config)
            other_miner = crypto.address(crypto.public_key(crypto.generate_key()),
                                         self.config["network"])
            try:
                for timestamp in range(1, 10):
                    chain.mine(self.miner, timestamp=timestamp)
                shared = chain.tip

                for timestamp in range(10, 13):
                    chain.mine(self.miner, timestamp=timestamp)
                normal_parent = chain.tip
                normal_block = consensus.make_block(
                    normal_parent["block"], normal_parent["state"], [], self.miner,
                    self.config, timestamp=13,
                    ancestors=chain._ancestors(normal_parent["hash"]))
                chain.add_block(normal_block)

                fast_parent = shared
                for timestamp in (10, 10, 10):
                    fast_block = consensus.make_block(
                        fast_parent["block"], fast_parent["state"], [], other_miner,
                        self.config, timestamp=timestamp,
                        ancestors=chain._ancestors(fast_parent["hash"]))
                    chain.add_block(fast_block)
                    fast_parent = chain.get(consensus.block_hash(fast_block))
                fast_next = consensus.make_block(
                    fast_parent["block"], fast_parent["state"], [], other_miner,
                    self.config, timestamp=11,
                    ancestors=chain._ancestors(fast_parent["hash"]))
                chain.add_block(fast_next)

                self.assertEqual(normal_block["header"]["target"], self.config["target"])
                self.assertEqual(fast_next["header"]["target"],
                                 self.config["target"] * 9 // 11)
                self.assertGreater(consensus.block_work(fast_next),
                                   consensus.block_work(normal_block))
                self.assertEqual(chain.tip["hash"], consensus.block_hash(fast_next))
                expected_state = chain.tip["state"]
            finally:
                chain.close()

            replayed = Chain(path, self.config)
            try:
                self.assertEqual(replayed.tip["hash"], consensus.block_hash(fast_next))
                self.assertEqual(replayed.state(), expected_state)
            finally:
                replayed.close()


if __name__ == "__main__":
    unittest.main()
