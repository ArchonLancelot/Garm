---
description: Draft a Garm failure dossier for something that just went wrong, via the assisted interview, then validate it.
---

# Garm autopsy

Something failed (or nearly did). Write the autopsy while it's fresh — the
analysis is yours; the tool enforces structure.

## 1. Answer the interview

`garm autopsy` asks the closing-ceremony questions. You did the work, so
answer them yourself: write an answers JSON file, then draft:

```bash
python3 -m garm autopsy --answers /tmp/garm-autopsy-answers.json \
  --dir "${GARM_DIR:-dossiers}"
```

Answer keys (`what_was_tried` and `premises` take a string or a list of
strings; everything else is a string):

`task`, `agent`, `failure_class`, `outcome`, `what_was_tried`,
`root_cause`, `failure_signature`, `blocking_constraint`,
`challengeable_premises`, `what_retrieval_would_have_changed`,
`open_questions`, `tokens`, `premises`, `confidence`

Answer honestly, in your own words — the draft goes into the sections
verbatim, and nothing is invented for you:

- **task** — one line: what you were trying to do.
- **agent** — `claude-code`.
- **failure_class** — pick honestly: would handing the agent a textbook
  page have fixed it (`knowledge-gap`)? Facts there but reasoning wrong
  (`reasoning-error`)? Knew better but fumbled (`execution-slip`)? Wrong
  tool (`tool-misuse`)? Solved the wrong problem (`misread-task`)?
- **outcome** — `failed`, or `recovered` if it came back.
- **what_was_tried** — each attempt in order, approaches not every turn.
- **root_cause** — the actual reason, not the surface error.
- **failure_signature** — name the reusable pattern like a bug class, plus
  a plain-words match rule: "if you see X in the first few turns, stop and
  retrieve this dossier." This is the retrieval key — write it to be
  matched on.
- **blocking_constraint** — the fact about the repo, environment, or task
  that made the approaches fail, one to three sentences. Write it
  precisely: its inversion is often the next idea.
- **challengeable_premises** — the load-bearing assumptions the attempts
  rested on, each phrased so a future reader can ask "what if this is
  false?" Negating one is often the next idea. (optional)
- **what_retrieval_would_have_changed** — concretely: which early turn a
  second run would skip, and what it would do instead.
- **open_questions** — precise questions this failure left open for a
  future run to aim at. (optional)
- **tokens** — what took the longest, roughly how many tokens the failed
  approaches burned. (optional)
- **premises** — premise ids from `garm premise list`, if the approach
  rested on any. (optional)
- **confidence** — how confident you are in this autopsy, and what would
  change your mind.

No invented details. A question left blank leaves its section as guidance
text — and a draft with empty *required* sections still gets written, but
fails `validate` by design, naming what needs writing. That's the deal:
the interview removes the blank page, not the judgment.

## 2. Finish, validate, index

If the draft validated on the first pass, `garm autopsy` already indexed
it — you're done. If it needs work, fill in the named sections, then:

```bash
python3 -m garm validate <the draft file>
python3 -m garm index --dir "${GARM_DIR:-dossiers}"
```

## 3. Close the loop on earlier dossiers

If a *retrieved* dossier shaped this run, confirm it so the bank learns:

```bash
# it prevented a repeat / fixed a verifiable failure:
python3 -m garm confirm <earlier-dossier-id> --dir "${GARM_DIR:-dossiers}"
# its analysis generated a new approach (open-ended work, no verifiable fix):
python3 -m garm confirm <earlier-dossier-id> --insight --dir "${GARM_DIR:-dossiers}"
```

The index rebuilds automatically after confirm. Don't confirm on vibes —
the counters are the dossier bank's track record.
