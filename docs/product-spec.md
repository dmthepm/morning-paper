# Product Spec

## Goal

Generate a daily Morning Brief that is:

- correct enough to print without embarrassment
- useful enough to replace first-thing screen spelunking
- stable enough to be maintained by an Engineer agent

## Primary Deliverables

1. Review markdown
2. Review PDF
3. QA report
4. Page screenshots
5. Telegram digest
6. Print-ready approved artifact
7. Optional processed visual asset plus metadata when a story warrants it

## Core User Story

Devon wakes up, makes coffee, picks up a printed brief, reads and marks it up, and understands:

- what matters externally
- what matters internally
- what requires action
- whether the system is healthy

without opening a laptop first.

## Modes

### Review mode

- generate markdown
- run QA
- render PDF
- generate screenshots
- send digest and review path
- do not print automatically

### Print mode

- only print an approved artifact
- never print a freshly assembled artifact without QA

## Optional Visual Lane

The brief may include one `Visual of the Day` when it materially improves comprehension on paper.

That visual must be:

- tied to a real story in the brief
- processed for monochrome print
- reviewed in page screenshots before promotion to print-ready

## Non-Goals

- making cron prompts the primary implementation surface
- storing private daily content in the future open-source repo
- letting style decisions live only in chats or sessions
