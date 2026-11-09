---
name: Specify and review consensus and difficulty adjustment
slug: consensus-difficulty-design
project: samanvay-layer1-wallet
priority: urgent
---

# Specify and review consensus and difficulty adjustment

Design the target production consensus rules for Bitcoin-style PoW mining and staking rewards. The existing prototype uses a fixed easy target and is trivially rewriteable; do not remove its loopback guard as a substitute for proper design.

## Acceptance criteria

- Specify target retarget windows, timestamps, bounds, attack assumptions, fork choice, and test vectors before implementation.
- Prove the hard 10 billion SAMV supply ceiling across genesis allocation, PoW subsidy, staking reward funding, fees, claims, and reorganizations.
- Define how staking rewards coexist with PoW without stake weight deciding valid-chain acceptance or introducing unintended extra minting.
- Add boundary, adversarial, reorganization, and property-based tests; obtain independent review of consensus rules and economic arithmetic.
- Keep profile separation and replay domains explicit. No real SAMV or mainnet launch.
