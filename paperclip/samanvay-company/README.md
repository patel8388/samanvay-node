# Paperclip coordination package for Samanvay

This folder is a portable, human-driven Paperclip company package. It contains one project and an unassigned backlog; it contains no agents, credentials, routines, schedules, or machine-specific paths. Importing it organizes work only. Paperclip does not build, validate, or run the Samanvay blockchain.

## Import into a local Paperclip instance

Use a current Paperclip installation with Node.js 24 or later. Keep the instance loopback-only and do not configure an AI provider or agent heartbeat for this coordination-only use:

```bash
PAPERCLIP_TELEMETRY_DISABLED=1 npx --yes paperclipai onboard --yes --bind loopback --no-install-service
paperclipai company import ./paperclip/samanvay-company --target new --dry-run
```

Review the preview. If it contains only the Samanvay company, project, and expected unassigned tasks, apply it with:

```bash
paperclipai company import ./paperclip/samanvay-company --target new --yes
```

The Paperclip server is a local coordination tool, not a public deployment. Do not select a LAN, tailnet, or public bind for this project. The package deliberately has no agent adapters, provider API keys, recurring routines, or automated execution settings.

## Work sequencing

The `keystore-review` item tracks the encrypted local tSAMV wallet foundation. Qualified-base selection and independent consensus/difficulty design are prerequisites to internet-facing P2P work. A private testnet remains gated on independent review, bounded networking, volunteer operators, and separate explicit approval. The mobile work item preserves the requirement for wallet staking and mining support while requiring platform-policy and key-custody review before any mobile release.
