---
name: Design the noncustodial mobile wallet
slug: mobile-wallet-staking-mining
project: samanvay-layer1-wallet
priority: high
---

# Design the noncustodial mobile wallet

Preserve the requirement for a mobile wallet that supports SAMV custody, staking actions, and mining operations. The present project has only a CLI wallet and does not support mobile signing or protected recovery.

## Acceptance criteria

- Design noncustodial key creation, encrypted device storage, backup/restore, wrong-network and replay protection, transaction review, staking lock/claim/exit/withdraw, and recovery without a founder-controlled seed server.
- Define mobile mining support honestly: review on-device mining feasibility and platform policy separately from using a phone to monitor or control an owner-managed node/miner. Do not promise built-in phone mining or background operation without technical and store-policy evidence.
- Choose and disclose a light-client proof model or the gateway trust model; handle stale balances, deep reorgs, unavailable services, and malicious responses.
- Obtain independent key-custody, platform, security, and relevant jurisdiction review before store distribution or real-value use.
