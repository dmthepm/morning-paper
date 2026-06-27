# Changelog

All notable changes to Morning Paper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [0.8.12] - 2026-06-27

### Changed
- Removed remaining public default-source configuration examples and
  issue-backlog prompts so setup starts from reader-owned sources and private
  collectors.
- Renamed the old CLI test module and cleaned recurrence prompts so public
  docs describe agents composing and producing editions, not an old
  deterministic product path.
- Archived pre-foundation release history under `docs/archive/` to keep the
  root changelog focused on the current operating model.

## [0.8.11] - 2026-06-27

### Added
- Added `morning-paper stage-social` for complete social source records with
  full post text, author/date, metrics, source status, thread context, and
  optional print-approved media.
- Added print-native social cards so an edition can show actual posts and
  threads instead of generic social summaries.
- Added delivery proof placeholders to edition workspaces so unattended runs
  have a clear slot for delivery evidence.

### Changed
- Renamed the social completion lane to `needs_source_record`, replacing
  process language with newsroom-facing source-record language.
- Expanded render output with an explicit `rendered` status and broadened
  visual QA page selection for longer papers.
- Tightened edition, collector, role, and review language so reader-facing
  papers avoid developer terms and production filler.

### Fixed
- Prevented incomplete social snippets from printing as if they were complete
  posts.
- Reduced stale setup/readiness language in public docs and scaffolded newsroom
  contracts.


Historical release notes before the current foundation cleanup live in `docs/archive/CHANGELOG-pre-foundation.md`.
