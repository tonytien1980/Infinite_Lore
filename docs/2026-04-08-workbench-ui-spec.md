# Workbench UI Specification

**Status:** Draft v1 approved for implementation baseline  
**Date:** 2026-04-08  
**Project:** Infinite Lore

## 1. Purpose

This specification defines the first `External Workbench UI` for `Infinite Lore`.

The Workbench exists to provide a usable operational interface for all workflow steps that are not naturally handled inside Obsidian.

It is not a replacement for Obsidian. It is the operational surface that sits beside the vault.

## 2. Product Role

The Workbench is:

- an external work interface
- an operational control surface
- the main place for import, compile inspection, system status, and grounded ask behavior

The Workbench is not:

- a general note-taking app
- a replacement vault browser
- a random chat shell without source grounding
- a second knowledge store

Its first version should make the existing backend pipeline actually usable in daily work.

## 3. Relationship With Obsidian

The Workbench and Obsidian share the same vault.

This means:

- Obsidian opens the vault directly
- Workbench reads and writes the same vault directly
- the filesystem remains the integration layer
- the vault remains the single source of truth

Obsidian is primarily for:

- reading notes
- browsing links and backlinks
- exploring domains
- manually editing notes
- writing personal reflections

Workbench is primarily for:

- importing sources
- monitoring bundle state
- viewing compile results
- asking grounded questions
- checking health and operations
- controlling model and provider settings

## 4. Approved Runtime Architecture

The first Workbench implementation should use:

`Local web app + Python backend`

### 4.1 Backend responsibilities

- interact with the vault
- run import
- run compile
- run health checks
- serve Workbench data
- later support grounded ask behavior

### 4.2 Frontend responsibilities

- present a usable UI/UX
- expose operational status
- provide source intake controls
- provide ask controls
- surface traceability clearly
- manage model and provider configuration

### 4.3 Source of truth rule

The first version should not introduce a separate canonical database for knowledge content.

The vault remains canonical.

## 5. Core UX Direction

The Workbench should feel like:

- a personal knowledge operations desk
- ask-first, but status-aware
- practical and calm, not noisy
- trustworthy and traceable

It should not feel like:

- a generic admin dashboard
- a chaotic tool launcher
- a pure chat app

The approved homepage interaction style is:

`Hybrid`

Meaning:

- Ask is visually primary
- system state is visible immediately below

## 6. Core Pages

The first Workbench version should include six core pages.

### 6.1 `Home`

The default landing page.

It should contain:

- a large Ask input area
- recent imports
- recent compile outputs
- warnings and health summary
- system snapshot cards

### 6.2 `Inbox`

This replaces a traditional import form page.

It should act as the raw intake monitor and controller.

It should contain:

- raw intake queue
- bundle states
- import failures
- review-needed bundles
- a secondary URL intake field
- manual control actions such as:
  - `Scan now`
  - `Retry failed`
  - `Recompile selected`

The primary intake model is still raw-folder-first.

The URL field is a secondary intake mode for web article capture.

### 6.3 `Knowledge`

This page shows compile output.

It should contain:

- recent synthesis notes
- recent new or updated smaller notes
- domain filters
- lineage visibility from bundle to notes
- indicators for created vs merged smaller notes

### 6.4 `Ask`

This is the full grounded question-answer workspace.

It should contain:

- question input
- answer pane
- grounding pane
- source trace pane
- answer mode controls

### 6.5 `System`

This page is for operational status.

It should contain:

- health check output
- warnings
- failures
- recent activity log
- path information
- environment and version information

### 6.6 `Settings`

This page includes model control and local configuration.

It should contain:

- vault path connection
- provider configuration
- API key entry
- model definitions
- user-assigned model roles
- feature-to-role routing
- connection tests

## 7. Final Navigation Order

The preferred first-version sidebar order is:

1. `Home`
2. `Inbox`
3. `Knowledge`
4. `Ask`
5. `System`
6. `Settings`

This order reflects the actual working flow:

`status -> intake -> compile results -> ask -> system -> model control`

## 8. Home Page Structure

The `Home` page should have three sections.

### 8.1 Ask primary area

This is the top section and the most visually prominent element.

It should include:

- a large prompt box
- suggested prompts
- quick access to grounded answer mode

### 8.2 Recent activity

This section should show:

- recent raw imports
- recent synthesis creation
- recent smaller-note updates

### 8.3 System snapshot

This section should show:

- import success and failure counts
- warning counts
- health status summary
- recent domain activity

## 9. Inbox Behavior

The `Inbox` page is not meant to be a heavy manual metadata form.

### 9.1 Intake philosophy

The user should be able to send sources into the system with minimal friction.

The system should:

- infer `primary_domain`
- infer `related_domains`
- compile automatically after import

The user should only intervene if the automatic classification or processing result is wrong.

### 9.2 Intake modes

Primary mode:

- monitor the raw intake folder

Secondary mode:

- paste a single web article URL

### 9.3 Manual actions

The Inbox page should support:

- `Scan now`
- `Retry failed`
- `Recompile selected`

These are operational overrides, not the primary daily mode.

## 10. Ask Interaction Model

Ask is the central usage mode for the personal LLM Wiki.

The user preference is not primarily to manually search and assemble answers. The user wants:

- a question-first interaction
- an answer already organized by the system
- a clear understanding of where the answer came from

### 10.1 Ask flow

The intended flow is:

`user question -> retrieve relevant wiki notes -> synthesize answer -> show source trace`

### 10.2 Ask output structure

Every answer should include:

- `Answer`
- `Grounding`
- `Trace to Source`

#### `Answer`

The direct answer in organized natural language.

#### `Grounding`

Shows which wiki notes shaped the answer.

This should reference:

- synthesis notes
- smaller notes such as concept, framework, and question notes

#### `Trace to Source`

Allows the user to trace the answer back to:

- raw bundles
- source files

### 10.3 Ask answer modes

The first version should support two answer styles:

- `Direct Answer`
- `Evidence-first`

These are answer presentation modes, not two separate systems.

### 10.4 Ask safety mode

Default Ask mode must be:

`strict grounded mode`

This means:

- answers must be based on existing wiki knowledge
- if evidence is insufficient, the system should say so
- silent invention is not allowed
- if the system makes an inference, it should be marked clearly as inference
- the answer should not silently blend in personal reflections as source-grounded facts

## 11. Query Role

`Query` remains useful, but it is a secondary mode compared to Ask.

`Query` is responsible for:

- locating relevant notes
- filtering by domain
- exploring what already exists

`Ask` is responsible for:

- answering using grounded knowledge

The first version does not need a fully separate heavy Query product surface if Ask already exposes:

- grounding
- linked notes
- source trace

## 12. Settings And Model Control

The Settings page must include a formal `Model Control` section.

### 12.1 Core principle

The system must not guess which user-configured model is cheap or high quality.

Instead:

- the user defines the model
- the user assigns the role
- the system routes by role

### 12.2 Required model role design

Supported roles should include:

- `cheap_fast`
- `balanced`
- `best_deep`

Additionally, some features should support:

- `no_model`

### 12.3 Feature routing

The user should be able to route by function, for example:

- `scan` -> `no_model`
- `import` -> `no_model`
- `compile` -> `balanced`
- `ask` -> `best_deep`
- `reflection` -> `balanced` or `best_deep`

### 12.4 Provider support

The first version should support multiple provider slots structurally.

OpenAI must be supported from the beginning.

The system should not assume only one provider exists.

### 12.5 API keys

API keys must not be stored in the vault.

API keys must not be stored in repo files.

They must live in a local Workbench configuration layer outside the vault.

### 12.6 Connection tests

The Settings page should include:

- provider connection test
- model availability test
- clear error display on failure

## 13. Security And Local Configuration

The core rule is:

`Knowledge belongs in the vault. Secrets do not.`

The Workbench must separate:

- vault content
- local runtime configuration
- API credentials

The first version should be local-only.

It should not yet introduce:

- multi-user accounts
- cloud secret syncing
- shared remote settings stores

## 14. Cost Control Principles

The user explicitly wants cost awareness.

The first version should preserve these operational rules:

- scanning the intake folder should not require LLM calls
- import normalization should avoid unnecessary model calls
- compile should remain lightweight
- Ask is the most justified LLM usage layer
- deeper refinement should happen later during actual use, not automatically on every source

The Workbench should make these boundaries visible so the user understands where model cost is being incurred.

## 15. First-Version Scope

The first Workbench implementation should cover:

- Home
- Inbox
- Knowledge
- Ask
- System
- Settings

It should provide:

- usable local UI/UX
- visibility into the current backend pipeline
- a way to import and inspect without terminal dependence
- grounded ask behavior design readiness

## 16. First-Version Non-Goals

The first Workbench version should not try to be:

- a full reflection management suite
- a full automation control center
- a full Obsidian replacement
- a team collaboration system
- a heavy evaluator dashboard

## 17. Summary

The Workbench is the external operational interface for Infinite Lore.

It shares the same vault as Obsidian, provides a proper UI for non-Obsidian workflows, makes Ask the primary interaction mode, keeps source grounding visible, and treats model configuration and cost control as first-class system concerns.
