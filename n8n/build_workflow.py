"""Builds n8n/c-suite-list-builder.json from roles.json. Run: python3 n8n/build_workflow.py

Click to run: one Sales Navigator search per chief role (your filters + the role's exact titles),
one small Evaboot export each, then the same cleaning as scripts/csuite.py: right current title,
Evaboot's filter re-check, safe email, one row per person. Output: a CSV file to download.
"""
import json
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATALOG = json.loads((HERE.parent / "roles.json").read_text())
EVABOOT_MCP = "https://mcp.evaboot.com/mcp"
EVABOOT_CRED = {"httpBearerAuth": {"id": "", "name": "Evaboot MCP (Bearer)"}}

nodes, connections = [], {}


def node(name, type_, version, params, pos, creds=None, **extra):
    n = {"parameters": params, "id": str(uuid.uuid4()), "name": name, "type": type_,
         "typeVersion": version, "position": pos, **extra}
    if creds:
        n["credentials"] = creds
    nodes.append(n)


def link(a, b, out=0):
    connections.setdefault(a, {}).setdefault("main", [])
    while len(connections[a]["main"]) <= out:
        connections[a]["main"].append([])
    connections[a]["main"][out].append({"node": b, "type": "main", "index": 0})


def mcp_call(name, tool, json_expr, pos):
    node(name, "@n8n/n8n-nodes-langchain.mcpClient", 1.1, {
        "endpointUrl": EVABOOT_MCP, "authentication": "bearerAuth",
        "tool": {"__rl": True, "mode": "list", "value": tool, "cachedResultName": tool},
        "inputMode": "json", "jsonInput": json_expr, "options": {"timeout": 120000},
    }, pos, EVABOOT_CRED)


def code(name, js, pos, **extra):
    node(name, "n8n-nodes-base.code", 2, {"jsCode": js}, pos, **extra)


ROLES_JS = "const CATALOG = " + json.dumps({"exclude": CATALOG["exclude"], "roles": {
    k: {f: v[f] for f in ("acronym", "include", "confused_with", "acronym_ok") if f in v}
    for k, v in CATALOG["roles"].items()}}) + ";\n"

SEARCHES_JS = ROLES_JS + r"""
// One Sales Navigator people search per role: your base search's filters + the role's exact titles.
const s = $('Your settings').first().json;
const q = t => encodeURIComponent('"' + t + '"');
const titleFilter = r => {
  const p = [...CATALOG.roles[r].include, ...(CATALOG.roles[r].acronym_ok ? [CATALOG.roles[r].acronym] : [])];
  const v = p.map(t => `(text:${q(t)},selectionType:INCLUDED)`)
    .concat(CATALOG.exclude.map(t => `(text:${q(t)},selectionType:EXCLUDED)`));
  return `(type:CURRENT_TITLE,values:List(${v.join(',')}))`;
};
const SEARCH = 'https://www.linkedin.com/sales/search/people?query=';
let base = null;
if (s.base_search_url) {
  base = decodeURIComponent(decodeURIComponent(s.base_search_url.split('query=')[1].split('&')[0]));
  if (base.includes('type:CURRENT_TITLE')) throw new Error('Remove the job title filter from your base search.');
  base = base.replace(/text:([^,)]*)/g, (m, t) => 'text:' + encodeURIComponent(t))
             .replace(/recentSearchParam:\(id:\d+,doLogHistory:true\),?/, '');
}
const roles = String(s.roles).split(',').map(r => r.trim()).filter(Boolean);
const bad = roles.filter(r => !CATALOG.roles[r]);
if (bad.length) throw new Error('Unknown role: ' + bad.join(', '));
return roles.map(role => ({ json: {
  role,
  name: `${s.list_name} - ${role}`,
  search_url: base ? SEARCH + base.replace('filters:List(', `filters:List(${titleFilter(role)},`)
                   : `${SEARCH}(filters:List(${titleFilter(role)}))`,
} }));
"""

IDS_JS = r"""
// Keep each role next to its export id.
const roles = $('Role searches').all();
return $input.all().map((it, i) => ({ json: {
  role: roles[i].json.role,
  extraction_id: it.json.structuredContent?.result?.extraction_id,
} }));
"""

FINISHED_JS = r"""
// Done when every export is finished. The leads stay on "Get the leads".
const all = $input.all().map(i => i.json.structuredContent?.result || {});
const running = all.filter(r => !['EXECUTED', 'FAILED'].includes(r.status));
return [{ json: { done: running.length === 0, running: running.map(r => r.search_name) } }];
"""

AGAIN_JS = "return $('Export ids').all();\n"

CLEAN_JS = ROLES_JS + r"""
// Same rules as scripts/csuite.py clean: right current title, Evaboot re-check, safe email, one row per person.
const s = $('Your settings').first().json;
const okStatus = s.keep_riskier ? ['safe', 'riskier'] : ['safe'];
const norm = t => String(t || '').toLowerCase().replace(/&/g, ' and ').replace(/[^a-z0-9]+/g, ' ').trim();
const has = (title, phrase) => (' ' + title + ' ').includes(' ' + norm(phrase) + ' ');
function why(role, p) {
  const title = norm(p['Current Job']);
  const r = CATALOG.roles[role];
  if (CATALOG.exclude.some(x => has(title, x))) return 'excluded title (chief of staff, deputy, fractional...)';
  if (r.include.some(x => title.includes(norm(x)))) return null;
  for (const o of r.confused_with || [])
    if (CATALOG.roles[o].include.some(x => title.includes(norm(x)))) return `other meaning of ${r.acronym}: ${o}`;
  if (has(title, r.acronym)) return r.acronym_ok ? null : `bare ${r.acronym}: ambiguous, check by hand`;
  return 'current title is not this role (LinkedIn matched another position)';
}
const ids = $('Export ids').all().map(i => i.json);
const results = $('Get the leads').all().map(i => i.json.structuredContent?.result || {});
const seen = {}, out = [];
results.forEach((res, i) => {
  const role = ids[i].role;
  for (const p of res.prospects || []) {
    let reason = why(role, p);
    if (!reason && p['Matches Filters'] !== 'YES') reason = 'Evaboot re-check: ' + p['No Match Reasons'];
    if (!reason && !okStatus.includes(p['Email Status'])) reason = 'email ' + (p['Email Status'] || 'not found');
    const id = p['Linkedin URL Unique ID'] || p['Linkedin URL Public'];
    if (!reason && seen[id]) { seen[id].role += '+' + role; continue; }
    const row = {
      role, acronym: CATALOG.roles[role].acronym, first_name: p['First Name'], last_name: p['Last Name'],
      title: p['Current Job'], company: p['Company Name'], company_domain: p['Company Domain'],
      email: p['Email'], email_status: p['Email Status'], linkedin: p['Linkedin URL Public'],
      kept: reason ? 'no' : 'yes', reason: reason || '',
    };
    if (!reason) seen[id] = row;
    out.push(row);
  }
});
return out.map(json => ({ json }));
"""

node("Start", "n8n-nodes-base.manualTrigger", 1, {}, [0, 0])
node("Your settings", "n8n-nodes-base.set", 3.4, {"assignments": {"assignments": [
    {"id": str(uuid.uuid4()), "name": "roles", "type": "string", "value": "cdo-data,cpo-product,clo-legal"},
    {"id": str(uuid.uuid4()), "name": "base_search_url", "type": "string", "value": ""},
    {"id": str(uuid.uuid4()), "name": "max_per_role", "type": "number", "value": 10},
    {"id": str(uuid.uuid4()), "name": "list_name", "type": "string", "value": "C-suite list"},
    {"id": str(uuid.uuid4()), "name": "keep_riskier", "type": "boolean", "value": False},
]}, "options": {}}, [220, 0])
code("Role searches", SEARCHES_JS, [440, 0])
mcp_call("Start export", "export_sn_search_or_list",
         "={{ JSON.stringify({ search_url: $json.search_url, name: $json.name, "
         "max_results: $('Your settings').first().json.max_per_role }) }}", [660, 0])
code("Export ids", IDS_JS, [880, 0])
node("Wait", "n8n-nodes-base.wait", 1.1, {"amount": 60, "unit": "seconds"}, [1100, 0], webhookId=str(uuid.uuid4()))
mcp_call("Get the leads", "get_export", "={{ JSON.stringify({ extraction_id: $json.extraction_id }) }}", [1320, 0])
code("All finished?", FINISHED_JS, [1540, 0])
node("Finished", "n8n-nodes-base.if", 2.2, {"conditions": {
    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
    "conditions": [{"id": str(uuid.uuid4()), "leftValue": "={{ $json.done }}", "rightValue": True,
                    "operator": {"type": "boolean", "operation": "true", "singleValue": True}}],
    "combinator": "and"}, "options": {}}, [1760, 0])
code("Clean list", CLEAN_JS, [1980, -100])
node("CSV file", "n8n-nodes-base.convertToFile", 1.1, {"options": {"fileName": "c-suite-list.csv"}}, [2200, -100])
code("Check again", AGAIN_JS, [1980, 140])

for a, b in [("Start", "Your settings"), ("Your settings", "Role searches"), ("Role searches", "Start export"),
             ("Start export", "Export ids"), ("Export ids", "Wait"), ("Wait", "Get the leads"),
             ("Get the leads", "All finished?"), ("All finished?", "Finished"), ("Clean list", "CSV file"),
             ("Check again", "Wait")]:
    link(a, b)
link("Finished", "Clean list", 0)
link("Finished", "Check again", 1)

workflow = {"name": "C-suite list builder (Sales Navigator + Evaboot)", "nodes": nodes,
            "connections": connections, "settings": {"executionOrder": "v1"}, "pinData": {}}
out = HERE / "c-suite-list-builder.json"
out.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n")
print(out, len(nodes), "nodes")
