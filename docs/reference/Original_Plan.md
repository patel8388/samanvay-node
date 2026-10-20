# Samanvay Network: mining, rewarded staking and mobile access

**Updated direction:** an independent Layer 1 with Proof-of-Work mining, protocol-funded staking rewards, Android/iOS wallet capabilities, a maximum supply of **10 billion SAMV**, developer grants and lifelong founder leadership without veto. Start with disposable tSAMV on existing equipment and no new project cash. This is a revised design proposal—not deployed software, an audited protocol, authorization to spend, or a promise of returns.

## 1. What changes now

The latest request supersedes the earlier “mining only, no staking” requirement. **Both mining rewards and staking rewards are now included.** To preserve Bitcoin-style mining without introducing an unreviewed dual-consensus system, the proposed architecture is **PoW consensus plus rewarded token locking**. Staking is a protocol reward feature, not validator selection or an additional finality layer.

| Requirement | Updated commitment |
|---|---|
| Independent Layer 1 | Own genesis, ledger, network identifiers, rules and releases; no inherited security from another chain |
| Mining | Real PoW block production; valid-chain selection by greatest cumulative work |
| Staking | Noncustodial SAMV locking with a variable share of a capped reward pool; no guaranteed APY |
| Mobile staking | View eligibility, lock, claim, request exit and withdraw from Android/iOS wallets |
| Mobile mining | Manage an owned remote miner or monitor a chosen pool from a phone; direct phone mining is experimental and platform-restricted |
| Supply | 10B maximum; 6.5B initially allocated and up to 3.5B progressively issued |
| Founder | Retain 30% initial allocation and 10% of scheduled subsidy, with vesting/maturity restrictions |
| Developers | Retain 20% for independently approved milestone grants |
| Leadership | Personal lifelong founder/steward role, two of seven council nominations, no veto |
| Sponsored transfers | Eligible users pay zero only when an actual funded sponsor pays the fee |
| Testnet | Existing hardware, donated connectivity and volunteer work; no new cash or valuable assets |

**Main trade-off:** staking is funded from the existing reward reserve, not additional minting. The proposed subsidy split changes from 90% miners / 10% founder to **60% miners / 30% stakers / 10% founder**. This reduces miner subsidy and may reduce hashpower; test security and participation before freezing these percentages. Rewarded locking does not itself secure the PoW chain against majority-hashpower attacks.

A hybrid PoW/PoS validator system is **not** included. If stake-based block production or stake-finality is later wanted, it requires a separate consensus specification, review and revised plan—not a silent configuration change.

## 2. Architecture and implementation

### Keep mining real

Evaluate and pin a maintained Bitcoin-derived PoW codebase with compatible licensing, reproducible builds and reviewed lineage. Reuse mature networking, UTXO accounting, signature validation and mining interfaces where practical. No actual release has yet been qualified for this complete design.

Miners construct blocks and search for a header hash below the difficulty target. Every full node independently validates signatures, initial allocations, difficulty, issuance, founder outputs and staking rules. Follow the **valid chain with greatest cumulative proof of work**. Invalid blocks do not become valid through more hashpower, stake votes or founder approval.

Proposed parameters to test:

- **120-second nominal block target**, not a delivery-time guarantee.
- Reviewed difficulty adjustment, median-time and timestamp bounds suitable for a small network; do not blindly copy Bitcoin’s long retarget period.
- **100-block coinbase maturity**, including outputs allocated to founder and staking reward pools. Maturity is not finality.
- Explicit block/resource limits, reorganization handling, transaction policy and wallet confirmation policies.
- Permissionless mining and full-node validation; no founder license, deposit or staking balance required.

The [Bitcoin developer guide](https://developer.bitcoin.org/devguide/block_chain.html) is background for PoW, cumulative work, rewards and maturity—not evidence that this chain inherits Bitcoin’s security.

### Choose the algorithm before public testing

SHA-256d is the literal Bitcoin-style baseline, but competitive mining is ASIC-dominated and a small compatible chain may face much larger outside hashpower. If broad desktop participation is the priority, evaluate one established CPU/GPU-oriented algorithm instead. Do not invent a hash function or promise permanent ASIC resistance, mobile profitability or equal earnings across hardware.

Choose **one** algorithm after measuring verification cost, independent miner availability, outside/rentable attack hashpower and power consumption. Mobile compatibility is not sufficient reason to weaken mining security. No merged mining, mandatory parent chain or external settlement token is assumed.

### Staking is substantial new protocol work

A stock Bitcoin-derived client does **not** provide the proposed staking system automatically. Initial distribution, restricted vesting, subsidy splitting, noncustodial staking locks, eligibility accounting, claims, unlock rules and sponsorship require explicit consensus and wallet engineering.

The staking state must be deterministically reconstructible and validated by every full node. A website database, founder server or ordinary multisig cannot substitute for consensus-enforced rewards and locks. Do not market an off-chain custodial savings balance as native staking. If reviewed enforcement is not ready, keep staking in a disposable prototype and delay feature-complete public launch.

Do not bolt PoW onto CometBFT and call it a configuration change. Cosmos validator, delegation and feegrant modules are not assumed available. This design does not use validator staking, stake-weighted chain selection, stake slashing or a PoS fallback.

Initial scope: native transfers, full nodes, mining, native locking/claims, mobile wallet, bounded faucet, sponsored transactions, receipts and monitoring. Defer general smart contracts, EVM, bridges, DeFi, oracles and extra VMs.

## 3. Supply and allocation: retain the 10B ceiling

Use six decimals: `1 SAMV = 1,000,000 usamv`. The hard ceiling is `10,000,000,000,000,000 usamv`. Use separate tSAMV network identifiers, genesis, address parameters and replay protection; symbols alone do not isolate networks.

| Allocation | Share of cap | SAMV budget | Treatment |
|---|---:|---:|---|
| Founder | 30% | 3,000,000,000 | Initial allocation with restricted vesting |
| Developer and ecosystem grants | 20% | 2,000,000,000 | Initial allocation; milestone grants and escrow |
| Mining, staking and founder subsidy reserve | 35% | Up to 3,500,000,000 | Unissued initially; released by the capped block schedule |
| Community treasury and sponsorship | 10% | 1,000,000,000 | Initial allocation; separately governed custody |
| Community access and distribution | 5% | 500,000,000 | Initial allocation; public distribution rules |
| **Maximum** | **100%** | **10,000,000,000** | **No reward outside this ceiling** |

Create **6.5B initially**, not all 10B. Define a reproducible, consensus-verified initial distribution mechanism; do not assume Bitcoin’s unspendable genesis coinbase can fund it. This is a premine/initial-allocation model with PoW, **not a Bitcoin fair launch**. Publish initial holdings separately from liquid circulation.

No administrator mint key, cap-exempt staking interest, founder top-up, burn-and-remint allowance or tail emission is included. Staking principal is existing SAMV: locking and unlocking it does not create supply. Claiming an already funded staking reward must not mint it a second time.

### Vesting and staking eligibility

Retain the founder’s **12-month cliff followed by 48 months of linear release**. Define enforceable height/time rules; PoW calendar estimates are approximate. Founder subsidy outputs additionally retain the proposed 365-day-equivalent restriction and ordinary coinbase maturity, subject to reviewed implementation.

**Unvested founder funds, restricted founder bonuses, unawarded developer funds, community distribution custody and treasury balances are ineligible for staking.** Only actually released, unrestricted founder coins may stake, on exactly the same terms as everyone else. Publish founder/affiliate stake concentration; a large initial allocation can still dominate rewards after vesting.

Developers receive milestone grants, not mining authority. Retain the suggested 25% on accepted delivery and 75% over 24 months, using enforceable escrow or clearly disclosed custody. Restricted grant tranches cannot stake; released unrestricted grants may. Publish beneficial ownership, acceptance evidence, conflicts and unlock terms. Unawarded grants are not founder property. A multisig is not automatic vesting or automatic clawback.

## 4. Mining, staking and founder rewards

### One finite subsidy schedule

Proposed halving era: **1,051,200 subsidy-bearing blocks**, approximately four years at a two-minute target. Genesis/initial-distribution issuance is excluded; first subsidy index is `h = 1`.

```text
R = 3_500_000_000_000_000          # total reward budget, usamv
H = 1_051_200                     # blocks per era
S0 = floor(R / (2 * H))           # 1_664_764_079 usamv
e = floor((h - 1) / H)
S(h) = S0 >> e                    # guarded shift; zero after exhaustion
C(h) = sum(S(i), i=1..h)          # scheduled maximum on this branch
C(0) = 0

F(h) = floor(C(h) / 10)           # cumulative founder share
N(h) = floor(4 * C(h) / 10)       # cumulative non-miner share
K(h) = N(h) - F(h)               # cumulative staking share, nested rounding
staking_budget(h) = K(h) - K(h-1)
founder_bonus(h) = F(h) - F(h-1)
miner_subsidy(h) = S(h) - staking_budget(h) - founder_bonus(h)
miner_reward(h) = miner_subsidy(h) + permitted_transaction_fees(h)
```

Use checked integer arithmetic and guarded shifts. **Testnet-preparation erratum:** independent floors for cumulative 30% staking and 10% founder can overdraw a one-usamv block: at subsidy height 31,536,010 the old rule assigned one usamv to each and left miner subsidy -1. Nested rounding above makes every share nonnegative and preserves the lifetime totals below. Individual block allocations can change by one usamv; these remain proposed rules requiring independent review, not frozen consensus. `C`, `K`, `N` and `F` describe **scheduled entitlements**, not a right to recover previously skipped rewards. Implement branch-local/reorg-safe accounting and efficient closed-form or incremental computation, not an unbounded per-block sum.

| First subsidy-bearing block | SAMV |
|---|---:|
| Miner subsidy, approximately 60% | 998.858448 |
| Staking budget, approximately 30% | 499.429224 |
| Founder bonus, approximately 10% | 166.476407 |
| **Total subsidy ceiling** | **1,664.764079** |

All ordinary transaction fees go to the miner; neither founder nor stakers have a reserved fee share. Founder may mine and stake eligible released coins under ordinary rules, but receives no bonus multiplier. No valid block means no subsidy; stale-branch rewards and their claims roll back.

### Exact lifetime ceiling

With all maximum scheduled rewards issued and claimed:

| Quantity | SAMV |
|---|---:|
| Initial allocations | 6,500,000,000 |
| Maximum miner subsidy | 2,099,999,989.722240 |
| Maximum staking allocation | 1,049,999,994.861120 |
| Maximum founder subsidy | 349,999,998.287040 |
| Total scheduled reward issuance | 3,499,999,982.870400 |
| Unissued rounding remainder | 17.129600 |
| **Maximum aggregate issuance** | **9,999,999,982.870400** |

There are 31 nonzero-subsidy eras, approximately 124 nominal years—not guaranteed lifetime income. The cap is a ceiling, not a requirement to issue exactly 10B. Founder initial principal plus reserved founder bonus is just under 3.35B before transfers and any ordinary mining/staking earnings. Those ordinary earnings come from the existing respective pools, not extra issuance.

Require exact founder and eligible staking allocations in valid reward outputs; permit underclaiming only the miner’s own allowance if specified by the reviewed implementation. Underclaimed miner subsidy is never recoverable later. Empty staking epochs skip issuance of their scheduled staking share, with no future catch-up. Accordingly actual issuance may be lower than the table. After subsidies end, founder bonuses and subsidy-funded staking rewards stop; miners depend on fees or disclosed outside funding.

## 5. How rewarded staking works

### Proposed user terms for testing

| Rule | Proposed test setting |
|---|---|
| Minimum lock | 1 SAMV; revise only after dust/state-growth testing |
| Reward epoch | 720 blocks, approximately one day |
| Entry | Lock confirmed funds before an epoch starts; new locks become eligible at the next boundary |
| Weight | Eligible locked principal for that epoch; rewards accumulate across active epochs without a duration multiplier |
| Minimum active lock | 7 full reward epochs |
| Exit | Exit request takes effect at the next epoch boundary; then 7 full epochs of non-rewarding unbonding |
| Withdrawal | Principal withdrawable after the exit delay; exact height shown in the wallet |
| Reward claim | Explicit signed claim after epoch settlement and maturity; normal or sponsored transaction fees |
| Compounding | Optional user-signed claim and new lock; no hidden automatic relock |

These are proposed parameters, not finalized protocol promises. Block-based periods are estimates in calendar time. Define exact inclusive/exclusive heights in the specification and test every boundary. A phone need not remain online for an eligible lock to accrue rewards.

### Deterministic accounting, no discretionary payouts

At each epoch boundary, full nodes derive the eligible stake set from confirmed lock/exit transactions. Hold weights fixed for that epoch so late deposits cannot capture earlier rewards. New locks begin no earlier than the next boundary; exit requests remove weight at the next boundary once the minimum active term is satisfied. The exit delay begins there and does not earn rewards. Restricted allocations and reward-pool balances are excluded.

For an epoch with eligible total `W`, each position of weight `w` receives at most `floor(epoch_budget * w / W)` base units. `epoch_budget` is the sum of scheduled staking shares for blocks in that epoch, issued only when eligible weight exists. No eligible stake means that epoch’s staking share remains unissued forever. The miner/founder shares do not absorb it.

Issue staking shares into a consensus-restricted reward pool, never a founder-controlled payout wallet. Settle claims only after the entire epoch’s reward outputs satisfy coinbase maturity and a specified confirmation policy. Unclaimed entitlements remain reserved to their rightful owners; integer division dust stays unclaimable in the pool, with no founder sweep or discretionary redistribution. Do not expire claims or spend their backing without an explicit future protocol change. Account for pool balances, entitlements and paid claims without double-counting supply.

Every full node must reject duplicate claims, forged ownership, reward overspending, ineligible stakes, premature withdrawals and spending another user’s principal. Use a reviewed bounded-state or authenticated-claim design; a rule that loops through every staker on every block is not acceptable. Publish resource ceilings, claim proofs, pruning/state-growth behavior and recovery rules before implementation. An API may display entitlements, but cannot determine them authoritatively.

### Honest reward display

Show locked principal, eligibility height, active epochs, accrued/claimable reward, fees, exit status and withdrawable height. An estimate may use recent epoch rewards and eligible total stake, but must disclose that halvings, participation, block production, rounding and reorganizations change outcomes. **No fixed APY, guaranteed daily payout, fiat value or investment return.**

There is no validator misbehavior to slash in this design; principal remains exposed to software bugs, key theft, lock delays, chain reorganizations and SAMV price risk. Staking does not give holders block-production authority, finality or a right to vote away other users’ funds.

## 6. Mobile capabilities

### Android and iOS wallet

Provide a noncustodial mobile wallet with key creation/import, encrypted local storage using platform-backed facilities where supported, backup/restore checks, clear transaction review and optional biometric access. Biometric unlock is not a seed backup. Never send seeds to a staking service, miner, sponsor, analytics endpoint or remote RPC.

Required screens: balances and pending confirmations; send/receive with QR; lock/claim/exit/withdraw staking; reward estimates and history; remote mining status; sponsored fee availability; clear tSAMV versus SAMV network labels. Notification permissions are optional; a delayed push must not affect protocol entitlement.

Use a reviewed light-client/header-proof design where feasible, or explicitly disclose reliance on selected gateways and cross-check independent providers. Do not label a gateway wallet a full node or claim that Merkle inclusion alone establishes complete consensus validity. Wallets must handle wrong-network addresses, replay isolation, deep reorganizations, unavailable services and stale balances. Avoid a mandatory founder API.

### Mining from a phone: separate three meanings

1. **Remote mining management — primary mobile feature.** Pair with the user’s existing desktop/server miner or a voluntarily chosen pool; show hashrate, worker status, accepted/rejected shares, payouts and errors. Pool payout receipts are pool claims until confirmed on-chain. Remote start/stop needs authenticated, narrowly scoped controls over a private channel; never expose administrative mining RPC publicly. A phone can disconnect without stopping a remote worker.
2. **Direct on-device PoW — optional Android research only.** A separate reviewed build may demonstrate real hashing on supported hardware, subject to the chosen algorithm, current distribution rules and device restrictions. It is not the default store app, not a launch dependency and not promised competitive or profitable. Require explicit consent, foreground operation, charging preference, temperature/battery limits, immediate stop and measured performance. No hidden/background or browser mining. Alternative distribution is not a security endorsement or a guaranteed workaround for platform restrictions.
3. **Tap-to-earn is not mining.** Faucet rewards, daily check-ins, referrals and simulated hashrate must be labeled honestly and funded only from a disclosed community budget. They do not produce valid PoW blocks or justify new cap-exempt issuance.

**iOS:** plan wallet/staking transactions and remote mining monitoring/control, not direct on-device mining. **Android store app:** likewise plan wallet/staking and remote mining rather than built-in hashing. Platform policy references and distribution gates are recorded below. No paid cloud-mining package, leased hardware, guaranteed hashpower or cloud yield is included.

### Mobile acceptance gates

Demonstrate backup/restore, transaction signing and independent address verification; lost-phone recovery without a server seed; secure pairing and revocation; lock and reward correctness while the app is offline; interrupted claims without duplication; exit/withdraw after phone reinstall; low-battery/network behavior; signing tamper rejection; and iOS/Android policy review. A responsive web wallet may be a testnet fallback, but cannot promise native background mining or store distribution.

## 7. Sponsored transfers and fees

Keep normal network fees and resource limits. Display “Network fee: 0 — sponsored by [application]” only when a funded sponsor actually covers the transaction. Mining, staking entry, claim and exit transactions are not inherently free; define which are eligible and show the user’s exact cost before signing.

For UTXO sponsorship, qualify a noncustodial jointly constructed transaction using separate sender-principal and sponsor-fee inputs. Both parties verify all outputs, amounts, change and maximum fees. Never request the sender’s keys. Fee/input accounting, dust, race conditions and supported signing tooling are development gates, not assumed features.

Use restricted enrollment, per-user and global daily exposure limits, expiry/revocation and finite sponsor wallets. Address creation is not proof of personhood. Handle fee rises, conflicts, replacements if enabled, rebroadcasts and reorgs without duplicate payouts or surprise user charges. If safe sponsorship is unavailable, stop or offer explicitly approved self-payment; never silently turn custodial or charge a user.

When sponsor funding runs out, stop new sponsored submissions transparently. Treasury tokens cannot pay electricity without outside purchasing power. No free-forever service is promised. Keep private invoice/identity information off-chain; a receipt is not bank settlement or proof of delivery.

## 8. Lifelong founder leadership, no veto

The founder retains a **personal lifelong Founder and Network Steward role**: publish a roadmap, initiate proposals, request a time-bounded public council review, participate in development and nominate **two members of a seven-person developer-grant council**. The founder may occupy one nominee seat, not an eighth seat. Other contributors retain independent proposal/release routes.

The role has no automatic 24-month expiry. It is personal, nontransferable and not hereditary; nomination privileges end at death, with seats transitioning to community selection. A charter cannot prevent future forks or guarantee permanent unilateral control.

The founder cannot unilaterally mint, freeze/confiscate funds, rewrite history, pause the chain, force upgrades, set other users’ staking payouts, exclude valid miners or redirect grant/treasury funds. No master key, founder-only checkpoint, special vote multiplier, mandatory release signature or blocking countersignature.

### Council and treasury

Use two founder nominees and five genuinely independent members; disclose beneficial affiliations. Founder employees/controlled entities do not count as independent. Council authority covers developer grants only.

| Action | Proposed approval | Public review | Can independents approve without founder nominees? |
|---|---|---|---|
| Ordinary developer grant | 4 of 7 | At least 7 days | Yes, four of five |
| Exceptional developer grant | 5 of 7 | At least 14 days | Yes, all five |

Exceptional means more than 1% of the original developer pool per recipient/program within a rolling 90-day period, counting related parties and split payments. Until a reviewed policy engine enforces thresholds/delays, use conservative **5-of-7 signing for all developer disbursements** and disclose which review rules are operating policy rather than cryptographic enforcement. No founder recovery bypass.

Publish signer rotation, recusals and recovery rules. Founder nonresponse cannot freeze appointments: after a published 30-day window, an independent process fills interim vacancies. Address unavailable independent signers too. Community treasury has separate disclosed independent custody, without a founder blocking signature.

Anyone may propose protocol changes. Publish specifications, tests, review and activation criteria. Independent node operators choose adopted rules; miners supply work within those rules. Council votes, token balances and staking locks do not automatically enact upgrades or override validity. Maintain independent maintainers, reproducible builds and mirrors.

## 9. No-new-cash live-internet testnet

Use disposable **tSAMV only**, with no redemption, mainnet entitlement, airdrop, listing or cash-value promise. This document authorizes no hardware purchase, paid subscription, token sale, public exposure, router change or production launch.

Begin locally on existing hardware at low difficulty. Then recruit at least **four genuinely independent volunteer mining/node operators**, expanding toward seven or more for diversity. Four processes on one founder computer are one operator. Stakers are not additional miners, and phone users are not independent full nodes merely because they use an app. PoW has no fixed two-thirds validator quorum or “four nodes tolerate one failure” security rule.

For live internet, use existing public IPv4 with approved port forwarding or working IPv6/firewall rules, verified from an unrelated network. Publish distinct P2P ports and network magic. Aim for at least two independently operated reachable peers; no mandatory founder relay. If CGNAT prevents this and volunteers lack connectivity, remain an invited overlay devnet and disclose its dependence instead of claiming an open $0 public mesh.

Bind admin RPC locally/private. Expose only allowlisted, rate-limited test gateways with faucet/sponsor budgets; keep signing, mining-control, key material and management RPC off the public internet. Use a separate public-service full node where possible. Any free tunnel is optional for a restricted web gateway, not native P2P security or guaranteed hosting; check its terms/limits before use.

Publish source, versions, reproducible builds, genesis/allocation checksums, peers, mining and staking guides, mobile trust assumptions and reset notices. Static hosting can serve docs/frontend, not persistent miners or a faucet backend. Keep independent mirrors.

### Testnet launch checks

1. **Local rules:** real PoW blocks; deterministic initial allocations; cumulative-work selection; invalid difficulty/reward rejection; no stake-based block authority.
2. **Economics:** verify 60/30/10 splits, accelerated test halvings, cap, empty-stake epochs, rounding, maturity, vesting and exhaustion. Label accelerated schedules simulations.
3. **Staking:** boundary deposits/exits, minimum lock, ineligible allocations, duplicate claims, tiny positions, state limits, missed epochs, offline accrual, reorganizations and no double minting.
4. **Wallet and payments:** mobile restore and signing; sponsorship conflicts/depletion; safe remote miner pairing; no public admin endpoint.
5. **Internet and soak:** independent peers sync/mine/stake/transfer from unrelated connections; seven-day initial soak with restarts, partitions, miner changes, gateway failure and phone reinstall. Seven days is not mainnet qualification.

No-new-cash means no paid domains, cards, VPS, subscriptions or listing fees. Volunteers still contribute electricity, data, wear and time. Native store distribution/signing requirements may introduce future costs or account prerequisites; do not assume these fit $0. Use existing authorized accounts or a safe permitted test distribution path; if unavailable, keep a web/local demo and defer store launch. Never silently pay to bypass a blocker.

## 10. Delivery phases and funding gates

No fixed completion date is promised. Adding consensus-level staking and mobile signing expands scope materially beyond the prior mining-only plan. Estimate work only after choosing the codebase, algorithm, staking-state design and mobile stack.

| Phase | Work | Required evidence |
|---|---|---|
| 1 — Design and local PoW | Pin codebase/license, algorithm, difficulty, identifiers and full reward specification | Independent rebuild; correct allocations and cap; invalid blocks rejected |
| 2 — Staking and custody | Implement locks, reward pool/claims, exit, vesting and council controls | Boundary/reorg/oversupply tests; no early principal spend or double claim; no founder veto |
| 3 — Mobile and sponsorship | Noncustodial wallet, lock/claim/withdraw, remote mining pairing, bounded sponsorship | Recovery and signing tests; offline accrual; revoked pairing fails; zero fee shown only if funded |
| 4 — Volunteer internet devnet | Independent operators and safe reachable peers on existing resources | Measured hashpower/resources; cross-network sync; initial seven-day soak; explicit reset policy |
| 5 — Public adversarial testnet | Expand provider/region diversity, attack testing and mobile pilots | At least 90 days public testing, final 30 meeting predeclared stability targets; no valuable assets |
| 6 — Production decision | Independent security/legal review and sustainable operations | No unresolved critical/high blockers; published incident response; at least 12 months funded operating/security capacity |

Maintain the ambition of at least 50 independent full-node/mining operators across four regions before production unless review justifies another target. This is a diversity goal, not a security certificate. Publish compatible outside attack hashpower, pool/template control, founder affiliations, propagation/orphan rates, confirmation policy, disk/state growth, reward/lock concentration and deep-reorg procedures. Analyze reduced miner incentives under the new staking split. Test inherited and custom code, fuzz validation and verify reproducible releases.

**Budget:** local prototype and volunteer devnet target $0 additional project cash using existing resources. Production, audits, mobile store release and adequate mining security are **not priced or approved**. Earlier illustrative node-hosting figures are not a quote or a complete cost for this expanded system. Keep native-token budgets separate from actual cash expenses. Optional future software/services revenue, donations and treasury support are possibilities, not signed funding. No token price, listing, profit or yield is promised.

Without qualified staking enforcement, sufficient independent hashpower, safe mobile custody and funded incident response, remain experimental. Warnings cannot prevent outsiders from assigning value to a permissionless asset, but supported pilots must not solicit real-money use.

## 11. Decisions before freezing a valuable genesis

The following are **proposed defaults for this updated plan**, not irreversible approvals: 60/30/10 subsidy split; two-minute block target; four-year-equivalent halvings; one-day-equivalent staking epochs; 1 SAMV minimum lock; seven active epochs plus seven non-rewarding exit epochs; vested/unrestricted coins only. Choose the actual PoW algorithm and qualify implementation before a public freeze.

**Next action:** qualify the codebase and write executable supply, reward-split and staking-state tests; then build a local tSAMV mining-and-staking demo with a mobile wallet prototype. No paid mining, cloud rental, token sale or mainnet launch is authorized by this plan. Historical plans remain background only; this revision supersedes conflicting mining-only and no-staking statements.

### Testnet preparation status

The companion directory `samanvay-testnet-preparation/` contains arithmetic/timing reference tests, a fail-closed planning manifest, a readiness matrix and a volunteer/operator runbook. **It contains no Samanvay full node, wallet implementation or running network.** The supplied NOVA archive remains an incompatible in-memory prototype with unverified transaction authorization; it must not be exposed as this chain. PoW client/algorithm/difficulty qualification, consensus staking/vesting/claims and reorg code, mobile signing, safe sponsorship, independent operators and approved reachable peers remain blockers. All public identifiers, release commits and peers remain unset rather than fabricated. Preparation is not public-launch authorization, and mainnet remains out of scope.

The executable model checks supply arithmetic and proposed epoch boundaries only, not consensus security or decentralized operation. See the package's rounding erratum and acceptance matrix for exact coverage and required evidence. A preserved pre-correction copy is included for traceability. No new cash, endpoint, router change, token sale, valuable asset, or deployment is authorized or performed by this preparation.

## Mobile platform policy references

- [Apple App Review Guidelines, section 3.1.5](https://developer.apple.com/app-store/review/guidelines/): cryptocurrency mining processing must occur off device; wallet apps must be offered by developers enrolled as an organization. Section 3.2.1(viii) also imposes requirements on investing/money-management services. Review the exact staking model and jurisdictions before submission; noncustodial design is not an automatic exemption or approval.
- [Google Play blockchain-based content policy](https://support.google.com/googleplay/android-developer/answer/13607354?hl=en): on-device cryptocurrency mining is prohibited; remote mining management is permitted. Tokenized-asset earning features require applicable declarations/disclosures and must not glamorize potential earnings. Do not confuse ordinary token locking with the separate NFT wagering/prize restrictions.
- [Google Play developer policy](https://support.google.com/googleplay/android-developer/answer/18258653?hl=en) includes Organization-account requirements for cryptocurrency software wallets and exchanges. [Financial Services policy](https://support.google.com/googleplay/android-developer/answer/9876821?hl=en) requires applicable financial-feature declarations, disclosures and jurisdictional compliance, with documentation potentially requested.

These policies support the proposed separation of mobile wallet/control functions from remote mining; they do not grant store acceptance, approve a staking product or resolve securities, custody, money-transmission or tax classification. Obtain jurisdiction-specific review before real-value distribution. Do not use download/referral/social-task token promotions in conflict with store rules. Store acceptance remains a release gate; if accounts, compliance or costs block it, retain a permitted disposable test distribution rather than promising immediate Android/iOS release.
