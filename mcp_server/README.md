# Garm MCP server

The universal adapter: exposes the Garm loop — recall, init, autopsy,
validate, confirm, list, premise add/kill/list — as MCP tools (9 total),
so **any** MCP-capable agent (Claude Desktop, Cursor, Windsurf, Codex CLI,
…) can use a dossier bank directly. No Claude Code hook required.

This is the one non-stdlib part of the repo: it needs the official MCP
Python SDK. The core (`garm/`) stays stdlib-only.

## Install

```bash
pip install mcp          # or: pip install -r mcp_server/requirements.txt
```

## Run

From the repo root (so both `garm` and `mcp_server` import):

```bash
python -m mcp_server --dir /path/to/dossiers
```

Bank resolution per call: explicit `dir` argument → `GARM_DIR` env var →
`--dir` flag → `./dossiers`.

## Connect

**Claude Desktop** — `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "garm": {
      "command": "python3",
      "args": ["-m", "mcp_server", "--dir", "/path/to/dossiers"],
      "cwd": "/path/to/Garm"
    }
  }
}
```

**Cursor** — `~/.cursor/mcp.json` takes the same `mcpServers` block.

**Codex CLI** — `~/.codex/config.toml` (stdio servers; needs the repo root
on `PYTHONPATH` so both packages import):

```toml
[mcp_servers.garm]
command = "python3"
args = ["-m", "mcp_server", "--dir", "/path/to/dossiers"]

[mcp_servers.garm.env]
PYTHONPATH = "/path/to/Garm"
```

## Tools

| Tool | What it does |
|---|---|
| `garm_recall(task, top=3, failure_class?, include_dead=false, dir?)` | Rank dossiers for a task description. Lexical scoring: signature matches ×2, task matches ×1, confirmed dossiers +up to 5. v0.2.6 hybrid: math symbols canonicalized to words, query terms expand through a curated synonym map — paraphrases match, still no embeddings. Dead routes (premise killed) excluded unless `include_dead` is true — then marked `premise_dead`. |
| `garm_init(task, agent, failure_class, outcome="failed", dir?)` | Scaffold a dossier, returns its path. Fill the sections, then validate. |
| `garm_autopsy(task, agent, failure_class, outcome="failed", answers?, dir?)` | Assisted drafting: turn interview answers into a dossier draft. `answers` maps answer keys to text (lists allowed for `what_was_tried`/`premises`). Unanswered sections stay as guidance; partial drafts are written but reported invalid with the missing sections named. Nothing is invented. |
| `garm_validate(path)` | Validate a dossier. Rejects missing sections and untouched placeholder text. |
| `garm_confirm(id, insight=false, dir?)` | Bump confirmed_fixes (or confirmed_insights) and rebuild the index. |
| `garm_list(dir?)` | List all valid dossiers: id, task, class, confirms, origin, outcome. |
| `garm_premise_add(statement, depends_on?, dir?)` | Register a load-bearing premise; returns its id. |
| `garm_premise_kill(id, by, dir?)` | Close the big route: the premise and everything under it dies transitively; index rebuilt. |
| `garm_premise_list(dir?)` | List premises: id, statement, deps, status, killer, dead flag. |

## Tests

```bash
python -m unittest discover -s mcp_server/tests -t .
```

Skipped automatically when the `mcp` package isn't installed.
