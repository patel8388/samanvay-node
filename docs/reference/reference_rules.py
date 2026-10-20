"""Samanvay arithmetic/timing reference ONLY. No node, keys, signatures or networking.

All amounts are integer micro-units (usamv); all heights are subsidy-bearing
heights beginning at 1. Proposed epoch rules need independent protocol review.
"""
from dataclasses import dataclass

UNIT = 1_000_000
CAP = 10_000_000_000 * UNIT
INITIAL = 6_500_000_000 * UNIT
RESERVE = 3_500_000_000 * UNIT
ERA_BLOCKS = 1_051_200
INITIAL_SUBSIDY = RESERVE // (2 * ERA_BLOCKS)


def require_int(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError("expected integer at least %s" % minimum)


def subsidy(height, era_blocks=ERA_BLOCKS):
    require_int(height, 1)
    require_int(era_blocks, 1)
    # Accelerating eras does NOT increase initial subsidy or preserve lifetime issuance.
    era = (height - 1) // era_blocks
    return 0 if era >= INITIAL_SUBSIDY.bit_length() else INITIAL_SUBSIDY >> era


def cumulative(height, era_blocks=ERA_BLOCKS):
    require_int(height)
    require_int(era_blocks, 1)
    full, partial = divmod(height, era_blocks)
    limit = INITIAL_SUBSIDY.bit_length()
    total = era_blocks * sum(INITIAL_SUBSIDY >> e for e in range(min(full, limit)))
    if full < limit:
        total += partial * (INITIAL_SUBSIDY >> full)
    return total


@dataclass(frozen=True)
class Split:
    miner: int
    staking: int
    founder: int


def split(height, era_blocks=ERA_BLOCKS):
    require_int(height, 1)
    now = cumulative(height, era_blocks)
    before = cumulative(height - 1, era_blocks)
    # Nested cumulative buckets: founder tenth is a subset of non-miner 40%.
    # Independent floor(30%) + floor(10%) can overdraw a one-unit subsidy.
    staking = (4 * now // 10 - now // 10) - (4 * before // 10 - before // 10)
    founder = (now // 10) - (before // 10)
    return Split(now - before - staking - founder, staking, founder)


def epoch_of(height, blocks=720):
    require_int(height, 1)
    require_int(blocks, 1)
    return (height - 1) // blocks


def epoch_start(epoch, blocks=720):
    require_int(epoch)
    require_int(blocks, 1)
    return epoch * blocks + 1


def epoch_end(epoch, blocks=720):
    return epoch_start(epoch, blocks) + blocks - 1


def activation_height(lock_height, blocks=720):
    # Confirmed in epoch e -> active at first block of epoch e+1.
    return epoch_start(epoch_of(lock_height, blocks) + 1, blocks)


def exit_effective_height(lock_height, request_height, blocks=720, active_epochs=7):
    require_int(active_epochs, 1)
    require_int(request_height, 1)
    active = activation_height(lock_height, blocks)
    earliest = active + active_epochs * blocks
    # Request can be included in final active epoch, but cannot shorten the term.
    if request_height < earliest - blocks:
        raise ValueError("exit request too early")
    if request_height < lock_height:
        raise ValueError("request predates lock")
    return max(activation_height(request_height, blocks), earliest)


def withdraw_height(exit_height, blocks=720, unbond_epochs=7):
    require_int(exit_height, 1)
    require_int(blocks, 1)
    require_int(unbond_epochs, 1)
    if (exit_height - 1) % blocks:
        raise ValueError("exit must be at an epoch start")
    return exit_height + blocks * unbond_epochs


def claim_height(epoch, blocks=720, maturity=100):
    # Earliest inclusion: all epoch reward outputs are at least maturity blocks old.
    require_int(maturity, 1)
    return epoch_end(epoch, blocks) + maturity


def epoch_budget(epoch, blocks=720, era_blocks=ERA_BLOCKS):
    start, end = epoch_start(epoch, blocks), epoch_end(epoch, blocks)
    now, before = cumulative(end, era_blocks), cumulative(start - 1, era_blocks)
    return (4 * now // 10 - now // 10) - (4 * before // 10 - before // 10)


def allocations(budget, weights):
    """Model only; sorted labels are position IDs, not authenticated wallet owners.

    Returns (entitlements, unclaimable dust, skipped issuance). Empty epochs do
    not issue. Zero-weight entries are permitted for boundary test vectors.
    """
    require_int(budget)
    for weight in weights.values():
        require_int(weight)
    total = sum(weights.values())
    if total == 0:
        return {k: 0 for k in weights}, 0, budget
    result = {k: budget * v // total for k, v in sorted(weights.items())}
    return result, budget - sum(result.values()), 0


def maximum_issuance():
    return INITIAL + cumulative(ERA_BLOCKS * INITIAL_SUBSIDY.bit_length())
