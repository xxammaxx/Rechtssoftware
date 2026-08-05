# Jobs-to-be-Done — PrivateLegalNavigator v1.0.0rc2

**Date:** 2026-07-31

## Core Jobs

### JTBD 1: "When I receive an official letter, I want to capture its deadline so I don't miss it."

- **Current:** User creates case → uploads PDF → checks detected dates → confirms/corrects
- **Works well:** Date detection, confirmation flow, history tracking
- **Gap:** No notification/reminder system (out of scope for local app)

### JTBD 2: "When I'm preparing a response, I want to know which laws apply."

- **Current:** User searches legal sources → finds norms → links to case
- **Works:** Search and norm linking infrastructure exists
- **Gap:** No guided discovery — user must know to look for this feature

### JTBD 3: "When I meet with a lawyer, I want to show them a structured overview of my case."

- **Current:** Evidence pack exports case state as structured page
- **Works:** Comprehensive sections (facts, events, norms, metadata)
- **Gap:** Only viewable in browser — no PDF/print export yet

### JTBD 4: "When I'm tracking a legal process, I want to see what happened when."

- **Current:** Legal timeline with event types (document received, objection filed, etc.)
- **Works:** Rich event creation form
- **Gap:** Timeline only lists events — no visual timeline/chart

### JTBD 5: "When I use legal software, I need to be sure my data stays private."

- **Current:** Local-only, no cloud, no telemetry, visible privacy badges
- **Works:** Trust signals consistently present across all pages
- **Gap:** None identified — privacy model is solid

## Secondary Jobs

### JTBD 6: "When I open the app after weeks away, I want to quickly resume where I left off."

- **Gap:** No dashboard, no recent activity summary, no case status overview

### JTBD 7: "When a deadline changes, I want to update it and see what changed."

- **Works:** Correction and revocation with full history ✓
- **Gap:** No diff/comparison view between old and new values
