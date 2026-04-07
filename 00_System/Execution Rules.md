# Execution Rules

## Purpose

This file records the standing execution rules for working on `Infinite Lore`.

These are not optional preferences. They are the default operating rules for future work unless the user explicitly overrides them.

## Core Rules

- Documentation and implementation must stay aligned.
- If code behavior or architecture changes, the relevant docs must be updated in the same phase.
- If docs establish a rule or workflow, implementation should follow it instead of drifting.
- If a relevant skill exists, it should be used rather than approximated manually.
- Local git state and GitHub state should stay synchronized after verified milestones.
- Process rules should be written into the repo rather than relying on repeated user reminders.

## Documentation Alignment Rule

When a meaningful implementation change is made, update the relevant project documents in the same working phase.

This usually includes one or more of:

- system spec
- subsystem spec
- implementation plan
- execution roadmap
- workflow guide
- templates or operating rules

Do not leave docs knowingly stale after code changes that affect behavior, workflow, structure, or scope.

## Skill Usage Rule

When a relevant Codex skill exists for the current task, use it.

Do not substitute an ad hoc workflow when a skill already defines:

- how to design
- how to plan
- how to test
- how to verify
- how to publish

If a skill was considered but not used, there should be a concrete reason.

## Git And GitHub Sync Rule

`Infinite Lore` now has a GitHub remote:

- `git@github.com:tonytien1980/Infinite_Lore.git`

Default expectations:

- keep the local repo committed at meaningful milestones
- after verification, push the active branch to GitHub
- do not leave GitHub significantly behind local progress without a clear reason
- when a phase is considered baseline-complete, make sure GitHub reflects that baseline

If a branch is intentionally not pushed yet, that should be stated explicitly.

## Verification Rule

Before claiming a phase is complete:

- run the relevant tests
- run the relevant health checks
- inspect the actual output
- confirm git status is clean or explain why it is not

Do not claim completion from code inspection alone.

## Roadmap Rule

Before starting a new phase:

1. Read `docs/2026-04-08-execution-roadmap.md`
2. Read the relevant spec
3. Read the relevant implementation plan
4. Then begin implementation

Do not invent a new execution order when the roadmap already defines the next phase, unless the user explicitly changes priorities.

## Reminder Rule

If the user has to repeat a workflow expectation more than once, capture that expectation in repo documentation so future work stays consistent.
