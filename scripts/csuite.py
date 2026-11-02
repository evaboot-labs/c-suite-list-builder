#!/usr/bin/env python3
"""Build a clean C-suite list from Sales Navigator with Evaboot, one search per chief role.

  python3 scripts/csuite.py roles                                  # the role keys and their title phrases
  python3 scripts/csuite.py urls  --roles cdo-data,ciso [--base-url URL]
  python3 scripts/csuite.py export --roles cdo-data,ciso [--base-url URL] --max 10 --out data/run1 --yes
  python3 scripts/csuite.py fetch data/run1                         # resume waiting for a run's exports
  python3 scripts/csuite.py clean data/run1 [--keep-riskier]

`export` spends Evaboot credits (1 per lead, email included) and needs EVABOOT_API_KEY in .env.
`clean` reads data/<run>/raw/*.json (one Evaboot export per role) and writes c-suite-list.csv,
review.csv (the leads it set aside, with the reason) and summary.json. Standard library only.
"""
import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parent.parent
CATALOG = json.loads((ROOT / "roles.json").read_text())
ROLES, EXCLUDE = CATALOG["roles"], CATALOG["exclude"]
MCP_URL = "https://mcp.evaboot.com/mcp"
SEARCH = "https://www.linkedin.com/sales/search/people?query="


def norm(s):
    s = (s or "").lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def pick(keys):
    keys = [k.strip() for k in keys.split(",") if k.strip()]
    bad = [k for k in keys if k not in ROLES]
    if bad:
        sys.exit(f"Unknown role(s): {', '.join(bad)}. Run: python3 scripts/csuite.py roles")
    return keys


def title_filter(role):
    phrases = list(ROLES[role]["include"])
    if ROLES[role].get("acronym_ok"):
        phrases.append(ROLES[role]["acronym"])
    vals = [f"(text:{quote(chr(34) + p + chr(34))},selectionType:INCLUDED)" for p in phrases]
    vals += [f"(text:{quote(chr(34) + p + chr(34))},selectionType:EXCLUDED)" for p in EXCLUDE]
    return f"(type:CURRENT_TITLE,values:List({','.join(vals)}))"


def role_url(role, base_url=None):
    """One people search per role: the base search's filters plus this role's title filter."""
    if not base_url:
        return f"{SEARCH}(filters:List({title_filter(role)}))"
    if "query=" not in base_url:
        sys.exit("The base URL is not a Sales Navigator people search (no query=). Copy it again from the address bar.")
    query = unquote(unquote(base_url.split("query=", 1)[1].split("&")[0]))
    if "type:CURRENT_TITLE" in query:
        sys.exit("The base search already has a Current job title filter. Remove it in Sales Navigator, copy the URL again.")
    if "filters:List(" not in query:
        sys.exit("The base URL has no filters. Copy the URL of a Sales Navigator people search with your filters.")
    # Re-encode the free-text values LinkedIn decoded (spaces, quotes); keep the structure characters.
    query = re.sub(r"text:([^,)]*)", lambda m: "text:" + quote(m.group(1), safe="%"), query)
    query = re.sub(r"recentSearchParam:\(id:\d+,doLogHistory:true\),?", "", query)
    return SEARCH + query.replace("filters:List(", f"filters:List({title_filter(role)},", 1)


def mcp(tool, args):
    key = os.environ.get("EVABOOT_API_KEY") or dotenv().get("EVABOOT_API_KEY")
    if not key:
        sys.exit("EVABOOT_API_KEY is missing: copy .env.example to .env and paste your key from https://dash.evaboot.com/dash/api/")
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": tool, "arguments": args}}).encode()
    req = urllib.request.Request(MCP_URL, body, {
        "Authorization": f"Bearer {key}", "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream", "User-Agent": "c-suite-list-builder"})
    try:
        raw = urllib.request.urlopen(req, timeout=180).read().decode()
    except urllib.error.HTTPError as e:
        sys.exit(f"Evaboot {tool} failed: HTTP {e.code} {e.read().decode()[:300]}")
    data = json.loads(raw.split("data: ", 1)[1] if raw.startswith("event:") else raw)
    res = data.get("result") or {}
    if res.get("isError") or "error" in data:
        sys.exit(f"Evaboot {tool} failed: {json.dumps(data)[:400]}")
    return res["structuredContent"]["result"]


def dotenv():
    env = ROOT / ".env"
    if not env.exists():
        return {}
    pairs = (l.split("=", 1) for l in env.read_text().splitlines() if "=" in l and not l.startswith("#"))
    return {k.strip(): v.strip().strip('"') for k, v in pairs}


def cmd_roles(_):
    for key, r in ROLES.items():
        note = f"  confused with: {', '.join(r['confused_with'])}" if r.get("confused_with") else ""
        print(f"{key:20} {r['acronym']:5} {r['count']:>9,}  {' | '.join(r['include'])}{note}")


def cmd_urls(a):
    for role in pick(a.roles):
        print(f"{role}\t{role_url(role, a.base_url)}")


def cmd_export(a):
    roles = pick(a.roles)
    quota = mcp("get_daily_export_quota", {})["quota"]
    cost = a.max * len(roles)
    print(f"{len(roles)} searches x up to {a.max} leads = up to {cost} credits. "
          f"Credits: {quota['credits']}, daily quota left: {quota['remaining']}.")
    if not quota.get("has_valid_salesnav"):
        sys.exit("Sales Navigator is not connected in Evaboot: open a search in Chrome and click Export with Evaboot once.")
    if not a.yes:
        sys.exit("Nothing exported. Run again with --yes once the user agreed to the cost.")
    Path(a.out).mkdir(parents=True, exist_ok=True)
    jobs = {}
    for role in roles:
        r = mcp("export_sn_search_or_list", {"search_url": role_url(role, a.base_url),
                                             "name": f"{a.name} - {role}", "max_results": a.max})
        jobs[role] = r["extraction_id"]
        (Path(a.out) / "exports.json").write_text(json.dumps(jobs, indent=2) + "\n")
        print(f"{role}: export {r['extraction_id']} started")
    fetch(Path(a.out))


def fetch(run):
    """Wait for each export in <run>/exports.json and save it to <run>/raw/<role>.json."""
    jobs = json.loads((run / "exports.json").read_text(encoding="utf-8"))
    raw = run / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    for role, xid in jobs.items():
        if (raw / f"{role}.json").exists():
            continue
        deadline = time.time() + 30 * 60
        while True:
            r = mcp("get_export", {"extraction_id": xid})
            if r["status"] in ("EXECUTED", "FAILED"):
                break
            if time.time() > deadline:
                sys.exit(f"{role}: export {xid} is still {r['status']}. Run later: python3 scripts/csuite.py fetch {run}")
            time.sleep(20)
        (raw / f"{role}.json").write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{role}: {r['status']}, {len(r.get('prospects') or [])} leads")


def classify(role, p):
    """Why a lead does not belong in this role's list, or None when it does."""
    title = norm(p.get("Current Job"))
    if any(norm(x) and f" {norm(x)} " in f" {title} " for x in EXCLUDE):
        return "excluded title (chief of staff, deputy, fractional...)"
    r = ROLES[role]
    if any(norm(x) in title for x in r["include"]):
        return None
    for other in r.get("confused_with", []):
        if any(norm(x) in title for x in ROLES[other]["include"]):
            return f"other meaning of {r['acronym']}: {other}"
    if r.get("acronym_ok") and f" {norm(r['acronym'])} " in f" {title} ":
        return None
    if f" {norm(r['acronym'])} " in f" {title} ":
        return f"bare {r['acronym']}: ambiguous, check by hand"
    return "current title is not this role (LinkedIn matched another position)"


def cmd_clean(a):
    run = Path(a.run)
    files = sorted((run / "raw").glob("*.json"))
    if not files:
        sys.exit(f"No exports in {run / 'raw'}.")
    ok_status = {"safe", "riskier"} if a.keep_riskier else {"safe"}
    kept, review, summary, seen = [], [], {}, {}
    for f in files:
        role = f.stem
        prospects = json.loads(f.read_text(encoding="utf-8")).get("prospects") or []
        s = summary[role] = {"exported": len(prospects), "right_title": 0, "matches_filters": 0,
                             "email_found": 0, "safe": 0, "riskier": 0, "invalid": 0, "kept": 0}
        for p in prospects:
            status = p.get("Email Status") or ""
            if p.get("Email"):
                s["email_found"] += 1
            if status in s:
                s[status] += 1
            why = classify(role, p)
            if why is None:
                s["right_title"] += 1
            if p.get("Matches Filters") == "YES":
                s["matches_filters"] += 1
            if why is None and p.get("Matches Filters") != "YES":
                why = f"Evaboot re-check: {p.get('No Match Reasons')}"
            if why is None and status not in ok_status:
                why = f"email {status or 'not found'}"
            row = {"role": role, "acronym": ROLES[role]["acronym"], "first_name": p.get("First Name"),
                   "last_name": p.get("Last Name"), "title": p.get("Current Job"),
                   "company": p.get("Company Name"), "company_domain": p.get("Company Domain"),
                   "employees": p.get("Company Employee Exact Count"), "email": p.get("Email"),
                   "email_status": status, "linkedin": p.get("Linkedin URL Public"),
                   "years_in_position": p.get("Years in Position"), "months_in_position": p.get("Months in Position")}
            pid = p.get("Linkedin URL Unique ID") or p.get("Linkedin URL Public")
            if why is None and pid in seen:
                seen[pid]["role"] += f"+{role}"  # one person, two chief titles: one row
                continue
            if why is None:
                s["kept"] += 1
                seen[pid] = row
                kept.append(row)
            else:
                review.append({**row, "reason": why})
    for name, rows in (("c-suite-list.csv", kept), ("review.csv", review)):
        with open(run / name, "w", newline="", encoding="utf-8") as fh:
            cols = list(rows[0].keys()) if rows else ["role"]
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
    total = {k: sum(s[k] for s in summary.values()) for k in next(iter(summary.values()))}
    summary["total"] = total
    (run / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"{'role':20} exported  title  match  found  safe  kept")
    for role, s in summary.items():
        print(f"{role:20} {s['exported']:8} {s['right_title']:6} {s['matches_filters']:6} "
              f"{s['email_found']:6} {s['safe']:5} {s['kept']:5}")
    print(f"\n{len(kept)} leads in {run / 'c-suite-list.csv'}, {len(review)} set aside in {run / 'review.csv'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("roles").set_defaults(fn=cmd_roles)
    for name, fn in (("urls", cmd_urls), ("export", cmd_export)):
        p = sub.add_parser(name)
        p.add_argument("--roles", required=True, help="comma-separated role keys, e.g. cdo-data,cpo-product")
        p.add_argument("--base-url", help="a Sales Navigator people search with your other filters, no job title")
        if name == "export":
            p.add_argument("--max", type=int, default=10, help="leads per role (1 credit each)")
            p.add_argument("--out", required=True)
            p.add_argument("--name", default="C-suite list")
            p.add_argument("--yes", action="store_true", help="the user agreed to the cost")
        p.set_defaults(fn=fn)
    p = sub.add_parser("fetch", help="wait for the exports of a run and save them")
    p.add_argument("run")
    p.set_defaults(fn=lambda a: fetch(Path(a.run)))
    p = sub.add_parser("clean")
    p.add_argument("run")
    p.add_argument("--keep-riskier", action="store_true", help="keep riskier emails too (catch-all domains)")
    p.set_defaults(fn=cmd_clean)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
