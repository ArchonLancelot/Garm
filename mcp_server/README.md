# Garm MCP server

The universal adapter: exposes the Garm loop — recall, init, validate,
confirm, list — as MCP tools, so **any** MCP-capable agent (Claude Desktop,
Cursor, Windsurf, …) can use a dossier bank directly. No Claude Code hook
required.

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

## Tools

| Tool | What it does |
|---|---|
| `garm_recall(task, top=3, failure_class?, dir?)` | Rank dossiers for a task description. Lexical scoring: signature matches ×2, task matches ×1, confirmed dossiers +up to 5. |
| `garm_init(task, agent, failure_class, outcome="failed", dir?)` | Scaffold a dossier, returns its path. Fill the sections, then validate. |
| `garm_validate(path)` | Validate a dossier. Rejects missing sections and untouched placeholder text. |
| `garm_confirm(id, insight=false, dir?)` | Bump confirmed_fixes (or confirmed_insights) and rebuild the index. |
| `garm_list(dir?)` | List all valid dossiers: id, task, class, confirms, origin, outcome. |

## Tests

```bash
python -m unittest discover -s mcp_server/tests -t .
```

Skipped automatically when the `mcp` package isn't installed.
