# Run it in n8n

[`n8n/c-suite-list-builder.json`](../n8n/c-suite-list-builder.json) does the same as the script: click to run, get one CSV file.

## What runs

1. **Your settings** (Set): the role keys, your base Sales Navigator search, leads per role, a list name, and whether to keep riskier emails.
2. **Role searches** (Code): one people search per role, your filters plus the role's exact titles and the excluded titles.
3. **Start export** (Evaboot MCP): one export per role, capped at your leads per role.
4. **Wait**, **Get the leads** and **All finished?**: checks every minute until every export is done.
5. **Clean list** (Code): the same rules as `scripts/csuite.py clean`. Each row has `kept` (yes or no) and the `reason`.
6. **CSV file**: download it from the node's output.

## Set it up

1. **Import** the JSON: *Workflows > Import from file*.
2. **Add the credential:** a **Bearer Auth** credential named `Evaboot MCP (Bearer)`, with your key from [dash.evaboot.com/dash/api/](https://dash.evaboot.com/dash/api/). Select it on **Start export** and **Get the leads**.
3. **Fill in Your settings:**
   - `roles`: keys from [roles.md](roles.md), for example `cdo-data,clo-legal,ciso`.
   - `base_search_url`: a Sales Navigator lead search with your company filters and no job title. Empty means worldwide, every company.
   - `max_per_role`: start with 10. Each lead costs 1 Evaboot credit.
4. **Test:** click *Execute workflow*, then open **CSV file** and download the list.

## Good to know

- Exports from one Sales Navigator seat run one after the other, so several roles can take a few minutes.
- To add a role, edit `roles.json` and run `python3 n8n/build_workflow.py` to rebuild the JSON.

Back to the [README](../README.md).
