---
description: Scaffold a Garm failure dossier for something that just went wrong, then validate it.
---

# Garm autopsy

Something failed (or nearly did). Write the autopsy while it's fresh — the
analysis is yours; the tool enforces structure.

## 1. Scaffold

Run (defaults: dossier dir `$GARM_DIR`, else `./dossiers`):

```bash
python3 -m garm init --task "<one-line description of what failed>" \
  --agent claude-code --class <knowledge-gap|reasoning-error|execution-slip|tool-misuse|misread-task> \
  -o "${GARM_DIR:-dossiers}"
```

Pick `--class` honestly: would handing the agent a textbook page have fixed
it (`knowledge-gap`)? Did it have the facts and still go wrong
(`reasoning-error`)? Knew better but fumbled (`execution-slip`)? Wrong tool
(`tool-misuse`)? Solved the wrong problem (`misread-task`)?

## 2. Fill in every `##` section

- **What was tried** — attempts in order, approaches not every turn.
- **Root cause** — the actual reason, not the surface error.
- **Failure signature** — name the reusable pattern like a bug class, plus a
  plain-words match rule: "if you see X in the first few turns, stop and
  retrieve this dossier." This is the retrieval key — write it to be matched on.
- **Blocking constraint** — the fact about the repo, environment, or task
  that made the approaches fail, in one to three sentences. Write it
  precisely: its inversion is often the next idea.
- **What retrieval would have changed** — concretely: which early turn a
  second run would skip, and what it would do instead.
- **Confidence** — how confident you are, and what would change your mind.

No invented details. If a section can't be filled honestly, say what's
unknown instead.

## 3. Validate, index

```bash
python3 -m garm validate <the new file>
python3 -m garm index --dir "${GARM_DIR:-dossiers}"
```

## 4. Close the loop on earlier dossiers

If a *retrieved* dossier shaped this run, confirm it so the bank learns:

```bash
# it prevented a repeat / fixed a verifiable failure:
python3 -m garm confirm <earlier-dossier-id> --dir "${GARM_DIR:-dossiers}"
# its analysis generated a new approach (open-ended work, no verifiable fix):
python3 -m garm confirm <earlier-dossier-id> --insight --dir "${GARM_DIR:-dossiers}"
python3 -m garm index --dir "${GARM_DIR:-dossiers}"
```

Don't confirm on vibes — the counters are the dossier bank's track record.
