---
name: c-suite-list-builder
description: Build a clean C-level executive email list for a chosen set of chief roles (CEO, CFO, CDO, CPO, CLO, CCO, CISO, CIO, CSO, CAIO and more) from LinkedIn Sales Navigator with Evaboot - one search per role with the exact title in quotes and look-alike titles excluded, a small export per role, then a cleaning pass (current title, Evaboot filter re-check, safe email, one row per person). Use when the user asks for a C-suite or C-level list, chief officer emails, or a list of a specific chief role such as Chief Data Officers or Chief Legal Officers.
---

# C-suite list builder

This skill runs inside a clone of https://github.com/evaboot-labs/c-suite-list-builder. If `roles.json` is not in the working directory, clone the repo and work from there.

## Rules

- Never search a bare acronym. CPO, CCO, CDO, CSO, CIO, CLO, CRO and CMO each mean several jobs (`roles.json`, `confused_with`). Only `ciso` and `caio` accept the acronym.
- Confirm before every export: roles x leads per role = credits. Start with 10 leads per role.
- Print every Sales Navigator URL as a Markdown link with the URL in angle brackets: `[Open in Sales Navigator](<url>)`.
- Never invent a count or a rate. Report the numbers from `summary.json`.

## Step 0: check Evaboot

Call `get_daily_export_quota` (Evaboot MCP), or run `python3 scripts/csuite.py export --roles ciso --out /tmp/x` without `--yes`: it prints the quota and stops. If `has_valid_salesnav` is false, ask the user to sign in to Evaboot in Chrome, open any Sales Navigator search and click **Export with Evaboot** once. If the key or connector is missing, follow `docs/connect-your-agent.md`.

## Step 1: the roles

Ask which chief roles they want, in their words. Map each one to keys with `python3 scripts/csuite.py roles`. When a word is ambiguous ("CPO", "CCO", "CDO", "CSO", "CIO", "CLO", "CRO", "CMO"), show the meanings from `confused_with` with their counts and ask which one. Suggest the neighbours worth adding: `cpo-people` next to `chro`, `cdo-data` with its "Chief Data and Analytics Officer" variant, a General Counsel search next to `clo-legal`.

## Step 2: the base search

Ask for the company filters: geography, headcount, industry. Either the user builds a Sales Navigator lead search with those filters and no job title and pastes its URL, or you call `build_sn_search_from_prompt` with people only (geography and a seniority or function, no industry and no company size, which would start a company-first search) and add `COMPANY_HEADCOUNT` and `INDUSTRY` to the URL yourself. Remove any job title filter.

## Step 3: one search per role

Run `python3 scripts/csuite.py urls --roles <keys> --base-url "<url>"`. Show each role's search as a link and ask the user to open one and check the people and the count.

## Step 4: export

On a yes, run `python3 scripts/csuite.py export --roles <keys> --base-url "<url>" --max 10 --out data/<name> --yes`. It starts one Evaboot export per role, waits for each and saves it to `data/<name>/raw/<role>.json`.

Without a key in `.env`, do the same with the Evaboot MCP: `export_sn_search_or_list` per role URL with `max_results`, poll `get_export` until `EXECUTED`, and save each result's `prospects` as `{"prospects": [...]}` in `data/<name>/raw/<role>.json`.

## Step 5: clean

Run `python3 scripts/csuite.py clean data/<name>` (add `--keep-riskier` only if the user asks). It writes:

- `c-suite-list.csv`: the leads to use, with a `role` column; one row per person, roles joined with `+`.
- `review.csv`: every lead set aside, with the reason (other meaning of the acronym, LinkedIn matched another position, Evaboot re-check, email not safe).
- `summary.json`: per role, exported, right title, matches filters, email found, safe, kept.

Show the summary table. Point out the role with the lowest kept rate and tell the user how many leads to export for their target, from that rate.

## Step 6: scale

For the full list, run step 4 again with a higher `--max` (LinkedIn caps one search at 2,500 leads). To refresh it every week, call `create_recurring_export` on each role's export.
