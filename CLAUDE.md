# Forge Stack Context — The Echo

CLAUDE.md — Context briefing for AI assistants working in this repository.

## What this repo is
Tier 1 Consumer. The introspective layer. Given a hypothetical claim,
it simulates what would happen if the claim were committed to the
substrate — without committing anything. Read-only.

## The Immutable Rule
Never rewrite a primitive. Add a layer. You consume P13 (Keystone
Gate), P12 (Rules), P14 (Leighton Engine), and P9 (Substrate read
only). You do not rewrite them.

## Read-only discipline
The Echo NEVER writes to `forge.db`. It opens the database with
`mode=ro`. If a future version wants to write, it must be a new
layer above this one.

## Introspective posture
The Echo answers three questions for any hypothetical claim:
1. Would the Keystone Gate reject it? (contradiction check)
2. What rules would fire? (P12 preview)
3. What shape of mind would result? (what UNKNOWNs it answers,
   what new UNKNOWNs it creates)

## Constraints
- Standard library only (except `pytest` for dev).
- British English (-ise, artefact).
- Header discipline on every file and function.
