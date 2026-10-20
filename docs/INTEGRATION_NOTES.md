# What the end-to-end checks demonstrated

The final code passes seven integration tests in `tests/test_integration.py`, in addition to consensus, persistence and security regression tests. Earlier temporary missing CLI flags were corrected before final verification.

Real mined blocks synchronize over HTTP between two temporary SQLite nodes. A genuinely competing branch with another miner wins by greater valid cumulative work. Orphaned staking state is absent after branch adoption. Restart reconstructs a deliberately corrupted cached state from valid blocks, but rejects a corrupted stored block. Public peer addresses are rejected. The CLI creates a wallet, initializes a chain, mines enough blocks to mature funds, builds a signed transfer with network replay protection, includes it in a mined block, and reports the resulting height. The claim parser requires an explicit epoch.

Tests use real Ed25519 keys and addresses, integer protocol-unit amounts, and funds from matured mining outputs—not injected test balances. Each temporary HTTP server binds an OS-assigned loopback port and is shut down/joined after its test. Temporary keys and database files are deleted.

The separate `examples/local_demo.py` completes a 182-block two-staker lifecycle: ordinary funded transfer; next-epoch activation; one-usamv reward dust retained; mature claim; seven active epochs and seven unbond epochs; principal withdrawal; another earned claim after withdrawal; and a second node synchronized through multiple HTTP pages to the exact same tip and state. `demo-results.json` records actual output.

These are finite local behavioral checks, not independent internet operators, a long-running soak, a fuzz campaign, a mobile wallet release or an external security audit. Public and valuable-asset use remains blocked.
