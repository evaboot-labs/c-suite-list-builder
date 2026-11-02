# Agent instructions

This repo builds a clean C-level email list for the chief roles the user picks (CDO, CPO, CLO, CCO, CISO and 31 more). It runs one LinkedIn Sales Navigator search per role, with the role's exact titles in quotes and the look-alike titles excluded, exports each search with Evaboot (verified emails), then keeps only the leads whose current title is the role, who pass Evaboot's filter re-check, and who have a safe email.

1. Follow the skill in `skills/c-suite-list-builder/SKILL.md` step by step.
2. The roles, their title phrases and the acronyms they share live in `roles.json`. `python3 scripts/csuite.py roles` lists them.
3. `scripts/csuite.py` builds the searches (`urls`), exports them (`export`) and cleans the result (`clean`). Standard library only.
4. If the Evaboot connector or key is missing, follow `docs/connect-your-agent.md`.
5. If the user wants n8n instead, follow `docs/n8n.md` with them one step at a time.

Confirm with the user before every call that spends credits (1 Evaboot credit per lead): show the roles, the leads per role and the total. Never ask for or handle an API key: the user writes it into `.env` or connects Evaboot in their AI Agent. Never commit `.env` or `data/`: they hold secrets and real people's data. Never send an email.
