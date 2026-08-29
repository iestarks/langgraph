# revoke-token-agent ⇄ LangGraph Integration

This guide is **self-contained**: it shows how the
[revoke-token-agent](https://github.com/iestarks/revoke-token-agent) uses this
LangGraph fork to discover **all Azure (Microsoft Entra ID) privileged
accounts** and list them to stdout — and how to run everything from scratch.

**What you get:** a compiled LangGraph `StateGraph` that authenticates against
Microsoft Graph, scans activated directory roles, filters for well-known
privileged roles (Global Administrator, Privileged Role Administrator,
Security Administrator, …), enumerates their members (users, groups, service
principals), and prints the accounts to stdout.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  revoke-token-agent (LangGraph StateGraph)                   │
│                                                              │
│  authenticate ─► discover_roles ─► filter_privileged_roles   │
│       │               │                     │                │
│       │ (error)       │ (error)             ▼                │
│       └───────┬───────┘            enumerate_members         │
│               ▼                           │                  │
│             report ◄──────────────────────┘                  │
└──────────────┬───────────────────────────────┬───────────────┘
               │ stdout                        │ Microsoft Graph
               ▼                               ▼
   privileged account list      GET /v1.0/directoryRoles?$expand=members
```

| Node | What it does |
| --- | --- |
| `authenticate` | Microsoft Graph token via `azure.identity.DefaultAzureCredential` |
| `discover_roles` | Lists activated directory roles with members expanded (paged) |
| `filter_privileged_roles` | Keeps roles whose `roleTemplateId` is a known privileged template |
| `enumerate_members` | Flattens members into assignment rows (user / group / servicePrincipal) |
| `report` | Renders the stdout report; errors short-circuit here |

## Prerequisites

- Python **3.10+**
- For a **live** scan: an Azure identity with admin-consented Microsoft Graph
  application permissions `RoleManagement.Read.Directory` and
  `Directory.Read.All` (not needed for the offline demo below)

## Step 1 — Install (uses this fork as the LangGraph source)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # installs langgraph from iestarks/langgraph
```

`requirements.txt` pins LangGraph to this fork:

```
langgraph @ git+https://github.com/iestarks/langgraph.git@main#subdirectory=libs/langgraph
```

## Step 2 — Run the standalone demo (offline, no Azure credentials)

`revoke_token_agent_demo.py` rebuilds the agent's graph against fixture data,
so the full node pipeline can be smoke-tested without a tenant:

```bash
python revoke_token_agent_demo.py
```

You will see the discovered privileged accounts (Global Administrator,
Privileged Role Administrator, Security Administrator members) printed to
stdout, followed by a `TOTAL:` summary line.

## Step 3 — Run the full agent against a real tenant

The production agent lives in the companion repo:

```bash
git clone https://github.com/iestarks/revoke-token-agent.git
cd revoke-token-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .

az login                      # or configure AZURE_CLIENT_ID/... (see .env.example)
revoke-token-agent            # table to stdout
revoke-token-agent --json     # JSON to stdout
revoke-token-agent --demo     # offline fixture run
```

Exit code is `0` on success, `1` on authentication/Graph failures (the error
is rendered by the `report` node instead of a traceback).

## Repo map

- This repo (`langgraph` fork): `integrations/revoke-token-agent/` — this
  README, the runnable offline demo (`revoke_token_agent_demo.py`),
  `.env.example`, `requirements.txt`.
- Companion repo
  ([`iestarks/revoke-token-agent`](https://github.com/iestarks/revoke-token-agent)):
  the installable agent package (`src/revoke_token_agent/`), CLI, and tests.

## References

- [revoke-token-agent](https://github.com/iestarks/revoke-token-agent)
- [LangGraph docs](https://docs.langchain.com/oss/python/langgraph/overview)
- [Microsoft Graph directoryRole API](https://learn.microsoft.com/graph/api/resources/directoryrole)
- [Microsoft Entra privileged roles reference](https://learn.microsoft.com/entra/identity/role-based-access-control/permissions-reference)
