# The roles and their title rules

`roles.json` holds 36 chief roles. Each one has:

- `include`: the exact titles put in quotes in the Sales Navigator **Current job title** filter. A kept lead's current title must contain one of them.
- `confused_with`: the roles that share its acronym. A lead whose title names one of them is set aside with the reason.
- `acronym_ok`: only for `ciso` and `caio`, whose acronym has one meaning. The acronym is searched and accepted too.
- `count`: people with that title on LinkedIn, worldwide (Sales Navigator, 2026-11-02). For two-phrase roles it is the sum of both.
- `article`: the evaboot.com guide for the classic roles.

The top-level `exclude` list is added to every search as excluded titles, and checked again on every lead: "Chief of Staff", "Office of the", "Assistant to", "Deputy", "Fractional", "Virtual", "vCISO", "Advisor to".

## The acronyms that mislead

| Acronym | Meanings (people on LinkedIn) |
|---|---|
| CPO | Product 24,177 · People 16,178 · Procurement 3,980 · Privacy 1,450 |
| CCO | Commercial 37,328 · Compliance 19,273 · Creative 15,075 · Customer 5,155 · Communications 4,856 |
| CDO | Digital 6,018 · Data 5,034 (+785 Data and Analytics) · Diversity 547 |
| CSO | Strategy 25,760 · Sales 13,536 · Science 12,415 · Security 8,988 · Sustainability 1,949 |
| CIO | Information 43,779 · Investment 21,769 |
| CLO | Legal 11,680 · Learning 2,336 |
| CRO | Revenue 22,321 · Risk 12,171 |
| CMO | Marketing 76,102 · Medical 23,711 |

## Add a role

Add an entry to `roles.json` with its `acronym`, `include` and, when the acronym is shared, `confused_with` on both sides. Then rebuild the n8n workflow: `python3 n8n/build_workflow.py`.

Back to the [README](../README.md).
