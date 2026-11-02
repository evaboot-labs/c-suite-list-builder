# Connect your AI Agent

The kit needs the Evaboot MCP server, or an Evaboot API key for `scripts/csuite.py`.

## 1. Accounts

- An [Evaboot account](https://dash.evaboot.com/accounts/signup/?last_click_origin=c-suite-list-builder-repo) with credits.
- A LinkedIn Sales Navigator seat, connected to Evaboot: open any search in Chrome and click **Export with Evaboot** once.

## 2. Get the repo

```bash
git clone https://github.com/evaboot-labs/c-suite-list-builder
cd c-suite-list-builder
cp .env.example .env
```

Write your key from [dash.evaboot.com/dash/api/](https://dash.evaboot.com/dash/api/) into `.env` as `EVABOOT_API_KEY`. The script and `.mcp.json` both read it.

## 3. Connect the MCP server

- **Claude Code:** start it from this folder. `.mcp.json` connects `https://mcp.evaboot.com/mcp` with your key.
- **Claude (web and desktop app):** *Settings > Connectors > Add custom connector*, name `Evaboot`, URL `https://mcp.evaboot.com/mcp`, then sign in to Evaboot.
- **Codex, Cursor:** add `https://mcp.evaboot.com/mcp` as an HTTP MCP server with the header `Authorization: Bearer <your key>`.

## 4. Check

Run `python3 scripts/csuite.py roles`, then ask your AI Agent: "Check my Evaboot quota and whether my Sales Navigator is connected." A quota and `has_valid_salesnav: true` mean you are ready.

Back to the [README](../README.md).
