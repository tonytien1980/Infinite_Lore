# Image OCR And Screenshot Understanding Specification

**Status:** Delivered v1
**Date:** 2026-04-10
**Project:** Infinite Lore

## 1. Purpose

This specification describes the delivered image OCR and screenshot understanding phase after multimodal ingestion.

The goal is to deepen image usefulness inside `Infinite Lore` without creating a second ingest system or pretending that full model-based vision understanding already exists.

This phase makes imported screenshots, scans, diagrams, and text-heavy images materially more usable by:

- using Apple Vision as the primary local OCR path on macOS
- upgrading `content.md` from a bounded image summary into a bounded OCR-aware image note
- adding lightweight screenshot-oriented structure signals that help later compile and Ask use the imported image more accurately

## 2. Why This Is The Next Phase

`Infinite Lore` already supports:

- first-pass image raw import for:
  - `png`
  - `jpg`
  - `jpeg`
  - `webp`
- preserved original image files
- conservative image metadata, structural summary, and review posture

But the current delivered image path still has one major limitation:

- OCR only works when the local Swift Vision helper can run successfully on macOS

On this machine:

- `swift` is available
- `Pillow` is available
- `tesseract` is not required for the shipped image path

That makes local Apple Vision OCR the shipped OCR path.

This phase should deepen the same image bundle flow, not jump to a provider-heavy image reasoning stack too early.

## 3. Approved Direction

The approved next direction is:

`Phase 10 = Local Vision OCR plus bounded screenshot understanding on top of the existing image bundle contract`

Meaning:

- keep the current image importer entrypoint
- keep the current raw bundle contract
- add an on-device OCR helper for macOS
- improve image normalization output using OCR-aware sections and bounded screenshot signals
- stay honest about uncertainty and review requirements
- reuse `Graphify` only where real code exists and fits this phase

## 4. Core Principle

This phase is not “full multimodal intelligence.”

It is:

- stronger on-device visible-text extraction
- better structure for screenshot-like knowledge
- clearer metadata for downstream compile and Ask

The system should improve utility while preserving trust.

If extraction is partial, weak, or uncertain, the bundle should say so explicitly instead of faking confidence.

## 5. Current Baseline

The delivered Phase 9 image path currently provides:

- preserved original image file in the bundle
- image metadata:
  - filename
  - format
  - dimensions
  - color mode
  - transparency note
- bounded structural summary
- optional visible text extraction only when `tesseract` exists
- conservative `low` confidence
- `review_required: true`

The current path does not yet provide:

- dependable OCR on this Mac by default
- OCR block ordering that is usable for screenshot reading
- bounded screenshot-aware interpretation
- explicit OCR engine metadata

## 6. Delivered Behavior

This phase includes:

- local macOS Vision OCR for supported image bundle imports
- replacement of best-effort `tesseract` probing as the primary OCR path
- OCR-aware image Markdown normalization
- bounded screenshot understanding signals derived from local extraction and image structure
- image metadata extensions that record:
  - OCR engine
  - OCR attempt state
  - OCR status
  - OCR text presence
  - screenshot interpretation posture
- fallback to the existing bounded image summary path when Vision OCR is unavailable or fails

Supported inputs remain:

- `png`
- `jpg`
- `jpeg`
- `webp`

## 7. Out Of Scope

This phase should not include:

- provider-backed VLM image reasoning as the default path
- full semantic diagram interpretation
- chart-specific data extraction
- handwriting recognition promises
- screenshot understanding inside live `Ask` requests
- graph UI or graph exports
- video ingestion
- audio ingestion

Those remain later expansion targets.

## 8. Runtime Baseline And Platform Assumption

This phase is intentionally optimized for the current machine profile:

- macOS
- local `swift` available
- no guaranteed `tesseract`

The first implementation should therefore prefer:

- a small local Swift helper using Apple Vision

over:

- asking the user to install a third-party OCR binary first

This keeps the path local, private, and aligned with the actual runtime we already verified.

## 9. Relationship To Apple Vision

Apple’s official Vision text-recognition API centers on `VNRecognizeTextRequest`, which recognizes text on-device and supports tuning around:

- recognition speed versus accuracy
- language handling
- minimum text height
- structured result observations

That makes it a good fit for this phase because `Infinite Lore` needs:

- local OCR without cloud dependency
- repeatable text extraction from screenshots and scans
- bounded structure signals that can be derived from recognized text observations

This phase uses Vision for OCR, not VisionKit UI overlays.

The goal is import-time extraction, not interactive text selection.

Sources:

- [VNRecognizeTextRequest](https://developer.apple.com/documentation/vision/vnrecognizetextrequest)
- [Recognizing Text in Images](https://developer.apple.com/documentation/vision/recognizing-text-in-images)

## 10. Relationship To Graphify

This phase should continue the same selective-reuse rule:

- reuse real `Graphify` code where it genuinely helps
- do not pretend `Graphify` already ships a drop-in OCR engine if it does not

What `Graphify` can still help with here:

- file-type discipline from `graphify/detect.py`
- local-versus-remote ingest separation from `graphify/ingest.py`
- the broader posture that images are meaningful knowledge inputs, not only OCR text
- the principle that screenshot-like inputs deserve semantic structure, not only raw blobs

What `Graphify` does not currently give us as direct drop-in code for this phase:

- a local macOS OCR helper
- a reusable Python screenshot-understanding module
- a bundle writer compatible with `Infinite Lore`

So the reuse boundary for this phase is:

- keep borrowing detection and stage-separation ideas
- build the OCR helper locally for `Infinite Lore`

## 11. Image Bundle Contract

This phase must preserve the existing bundle shape:

```text
20_Raw/inbox/<bundle>/
├── source.png | source.jpg | source.webp | ...
├── content.md
├── metadata.md
└── assets/
```

Rules:

- keep the original image file
- do not invent a second image bundle type
- keep downstream compile compatible with existing raw bundles

## 12. Content Normalization Changes

The current image `content.md` is too shallow for screenshot-heavy knowledge work.

After this phase, the normalized image note should include bounded sections like:

- source summary
- OCR summary
- OCR text
- screenshot signals
- extraction notes

### 12.1 OCR summary

This section should capture bounded facts such as:

- OCR engine used
- whether OCR succeeded fully, partially, or not at all
- approximate count of recognized lines or regions
- whether the image appears text-heavy or text-light

### 12.2 OCR text

This section should provide normalized visible text in reading order, bounded to a safe length.

The goal is:

- useful downstream retrieval
- useful compile input

not:

- pixel-perfect transcript guarantees

### 12.3 Screenshot signals

This section should remain deliberately lightweight.

It should record bounded interpretation such as:

- likely screenshot versus likely scan versus generic image
- whether the image appears UI-like, document-like, or mixed
- whether visible text dominates the image
- whether exact visual meaning still requires manual review

These are support signals, not authoritative semantic claims.

## 13. Metadata Additions

`metadata.md` includes explicit image-extraction fields for this phase:

- `ocr_engine`
- `ocr_attempted`
- `ocr_status`
- `ocr_text_present`
- `image_interpretation_mode`
- `image_kind_guess`

The system should also preserve:

- `extraction_confidence`
- `review_required`
- warnings list

## 14. Confidence And Review Rules

This phase must stay conservative.

Current shipped defaults:

- image extraction remains `low`
- screenshot interpretation remains bounded and does not raise confidence above `low`
- images with weak OCR, mixed layouts, or uncertain type guesses remain `low`
- `review_required: true` should remain the default for image bundles in this phase

The system should prefer:

- visible uncertainty
- explicit fallback notes
- conservative metadata

over:

- bold semantic claims about screenshots or diagrams

## 15. Fallback Behavior

If the local Vision helper is unavailable or fails, the importer does not break the whole image lane.

Instead it:

- preserve the original image
- keep the current bounded structural summary path while preserving OCR-aware sections with warning-state content
- record that Vision OCR was unavailable or failed
- keep `low` confidence
- preserve `review_required: true`

This keeps image ingest usable even on machines that do not satisfy the ideal runtime.

## 16. Why This Helps Ask Later

This phase does not change live `Ask` into a screenshot-reasoning engine.

It still improves future Ask quality because:

- compiled notes will have more real visible text from images
- screenshot-heavy source bundles become less opaque to compile
- downstream retrieval has more text and clearer warnings to work with

The improvement should come from better source normalization, not from hiding uncertainty.

## 17. Definition Of Done

This phase is done when:

- supported image imports use Apple Vision OCR on this Mac
- `content.md` is upgraded from shallow summary to OCR-aware image normalization
- fallback behavior remains safe when OCR is unavailable or weak
- metadata records OCR engine, OCR attempt state, OCR status, OCR text presence, and image interpretation posture explicitly
- existing compile and Ask flows continue working on top of the same raw bundle contract
- docs reflect the delivered behavior in the same task

## 18. What This Phase Still Does Not Promise

Even after this phase, `Infinite Lore` should still not claim:

- full diagram comprehension
- chart understanding
- screenshot meaning reconstruction equivalent to a multimodal LLM
- perfect OCR across every language, layout, or image quality condition

This is a sharper and more useful image lane, not the final state of multimodal understanding.
