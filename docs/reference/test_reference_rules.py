import random
import unittest
from reference_rules import (
    UNIT, CAP, INITIAL, RESERVE, ERA_BLOCKS, INITIAL_SUBSIDY,
    subsidy, cumulative, split, epoch_of, epoch_start, epoch_end,
    activation_height, exit_effective_height, withdraw_height,
    claim_height, epoch_budget, allocations, maximum_issuance,
)


class EconomicsTests(unittest.TestCase):
    def test_allocation_and_cap(self):
        self.assertEqual(sum([3_000_000_000, 2_000_000_000, 1_000_000_000, 500_000_000]) * UNIT, INITIAL)
        self.assertEqual(INITIAL + RESERVE, CAP)

    def test_first_subsidy(self):
        self.assertEqual(INITIAL_SUBSIDY, 1_664_764_079)
        self.assertEqual(subsidy(1), INITIAL_SUBSIDY)

    def test_first_split(self):
        s = split(1)
        self.assertEqual((s.miner, s.staking, s.founder), (998_858_448, 499_429_224, 166_476_407))

    def test_halving_boundary(self):
        self.assertEqual(subsidy(ERA_BLOCKS), INITIAL_SUBSIDY)
        self.assertEqual(subsidy(ERA_BLOCKS + 1), INITIAL_SUBSIDY >> 1)

    def test_cumulative_against_naive(self):
        for end in [0, 1, 2, 9, 10, 11, 22, 333]:
            self.assertEqual(cumulative(end, 10), sum(subsidy(h, 10) for h in range(1, end + 1)))

    def test_split_telescopes(self):
        sums = [0, 0, 0]
        for h in range(1, 1001):
            s = split(h, 20)
            self.assertEqual(s.miner + s.staking + s.founder, subsidy(h, 20))
            sums = [a + b for a, b in zip(sums, [s.miner, s.staking, s.founder])]
        total = cumulative(1000, 20)
        self.assertEqual(sums, [total - 4 * total // 10, 4 * total // 10 - total // 10, total // 10])

    def test_lifetime_exact(self):
        self.assertEqual(cumulative(ERA_BLOCKS * 31), 3_499_999_982_870_400)
        self.assertEqual(maximum_issuance(), 9_999_999_982_870_400)
        self.assertEqual(CAP - maximum_issuance(), 17_129_600)

    def test_lifetime_split(self):
        c = cumulative(ERA_BLOCKS * 31)
        self.assertEqual((c - 4*c//10, 4*c//10 - c//10, c//10),
                         (2_099_999_989_722_240, 1_049_999_994_861_120, 349_999_998_287_040))

    def test_exhaustion(self):
        self.assertEqual(subsidy(ERA_BLOCKS * 31 + 1), 0)
        self.assertEqual(cumulative(10**18), cumulative(ERA_BLOCKS * 31))

    def test_random_split_invariants(self):
        rng = random.Random(90421)
        for _ in range(1000):
            h = rng.randrange(1, ERA_BLOCKS * 40)
            s = split(h)
            self.assertGreaterEqual(min(s.miner, s.staking, s.founder), 0)
            self.assertEqual(s.miner + s.staking + s.founder, subsidy(h))
            self.assertLessEqual(INITIAL + cumulative(h), CAP)

    def test_original_rounding_failure_regression(self):
        h = 31_536_010
        c, p = cumulative(h), cumulative(h - 1)
        old_staking = 3*c//10 - 3*p//10
        old_founder = c//10 - p//10
        self.assertEqual((subsidy(h), old_staking, old_founder), (1, 1, 1))
        self.assertEqual(subsidy(h) - old_staking - old_founder, -1)
        s = split(h)
        self.assertEqual((s.miner, s.staking, s.founder), (0, 0, 1))

    def test_all_era_sizes_and_decimal_residues(self):
        for e in range(32):
            amount = INITIAL_SUBSIDY >> e
            for before in range(10):
                now = before + amount
                f = now//10 - before//10
                k = (4*now//10 - now//10) - (4*before//10 - before//10)
                self.assertGreaterEqual(min(amount-k-f, k, f), 0)

    def test_acceleration_does_not_claim_same_total(self):
        self.assertLess(cumulative(31 * 10, 10), RESERVE)
        self.assertEqual(subsidy(11, 10), INITIAL_SUBSIDY >> 1)

    def test_invalid_inputs(self):
        for bad in [-1, 0, 1.0, True, '1']:
            with self.assertRaises(ValueError):
                subsidy(bad)
        with self.assertRaises(ValueError):
            cumulative(-1)
        with self.assertRaises(ValueError):
            cumulative(1, 0)


class StakingArithmeticTests(unittest.TestCase):
    def test_epoch_boundaries(self):
        self.assertEqual([epoch_of(h) for h in [1, 720, 721, 1440, 1441]], [0, 0, 1, 1, 2])
        self.assertEqual((epoch_start(1), epoch_end(1)), (721, 1440))

    def test_no_same_epoch_entry(self):
        for h in [1, 719, 720]:
            self.assertEqual(activation_height(h), 721)
        self.assertEqual(activation_height(721), 1441)

    def test_seven_active_epochs(self):
        self.assertEqual(exit_effective_height(1, 5041), 5761)
        with self.assertRaises(ValueError):
            exit_effective_height(1, 5040)

    def test_late_exit(self):
        self.assertEqual(exit_effective_height(1, 5761), 6481)

    def test_seven_unbond_epochs(self):
        self.assertEqual(withdraw_height(5761), 10801)
        with self.assertRaises(ValueError):
            withdraw_height(5760)

    def test_claim_all_outputs_mature(self):
        self.assertEqual(claim_height(0), 820)
        self.assertEqual(claim_height(1), 1540)
        self.assertEqual(claim_height(1) - epoch_end(1), 100)

    def test_budget_matches_blocks(self):
        for e in range(3):
            self.assertEqual(epoch_budget(e), sum(split(h).staking for h in range(epoch_start(e), epoch_end(e) + 1)))

    def test_proportional_rounding(self):
        self.assertEqual(allocations(10, {'a': 1, 'b': 2}), ({'a': 3, 'b': 6}, 1, 0))

    def test_empty_epoch_skips(self):
        self.assertEqual(allocations(10, {}), ({}, 0, 10))
        self.assertEqual(allocations(10, {'a': 0}), ({'a': 0}, 0, 10))

    def test_dust_not_redistributed(self):
        ent, dust, skipped = allocations(2, {'a': 1, 'b': 1, 'c': 1})
        self.assertEqual(sum(ent.values()), 0)
        self.assertEqual((dust, skipped), (2, 0))

    def test_order_independence(self):
        self.assertEqual(allocations(17, {'a': 2, 'b': 7}), allocations(17, {'b': 7, 'a': 2}))

    def test_random_pool_conservation(self):
        rng = random.Random(127)
        for _ in range(1000):
            budget = rng.randrange(100000)
            weights = {str(i): rng.randrange(100) for i in range(rng.randrange(10))}
            ent, dust, skipped = allocations(budget, weights)
            self.assertEqual(sum(ent.values()) + dust + skipped, budget)
            self.assertGreaterEqual(min([dust, skipped] + list(ent.values())), 0)

    def test_reject_bad_weights(self):
        for v in [-1, 1.0, True]:
            with self.assertRaises(ValueError):
                allocations(10, {'a': v})


if __name__ == '__main__':
    unittest.main()
