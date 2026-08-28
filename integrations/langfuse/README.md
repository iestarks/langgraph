# Langfuse ⇄ LangGraph Integration

This guide is **self-contained**: it describes everything needed to set up
tracing from [LangGraph](https://github.com/langchain-ai/langgraph) agents into
[Langfuse](https://langfuse.com) — on a fresh machine, without any prior
knowledge of how this repo is organized or any AI coding assistant.

**What you get:** every LangGraph graph run appears in Langfuse as a trace,
with nested spans for each node, LLM call, token usage, latency, and
input/output payloads.

---

## Architecture

```
┌────────────────────────┐         ┌──────────────────────┐
│  LangGraph app (Py)    │  OTLP   │  Langfuse            │
│                        │ ──────► │  Server (self-hosted │
│  StateGraph + nodes    │ traces  │  or cloud)           │
│  + CallbackHandler     │         │  UI on port 3000     │
└────────────────────────┘         └──────────────────────┘
```

The integration uses the official
[`langfuse.langchain.CallbackHandler`](https://langfuse.com/docs/integrations/langgraph),
which hooks into LangChain's callback system that LangGraph is built on. No
code changes are required inside your graph nodes — you only attach the
handler at the invocation boundary.

---

## Prerequisites

- Python **3.10+**
- [Docker](https://docs.docker.com/get-docker/) (only if self-hosting Langfuse)
- An LLM provider API key (e.g. `OPENAI_API_KEY`) — *optional* if you only
  want to run the offline dry-run demo

## Step 1 — Start a Langfuse server (self-hosted)

Skip this step if you use Langfuse Cloud (`https://cloud.langfuse.com`).

```bash
git clone https://github.com/langfuse/langfuse.git
cd langfuse
docker compose up -d          # web UI on http://localhost:3000
```

Wait for all containers to become healthy, then open
<http://localhost:3000>, sign up, and create an **Organization** and a
**Project**.

## Step 2 — Create API keys

In the Langfuse UI: **Project Settings → API Keys → Create new API keys**.
You will get a **Public Key** (`pk-lf-...`) and a **Secret Key** (`sk-lf-...`).

## Step 3 — Configure environment

```bash
cp .env.example .env    # from this directory (or create the file yourself)
# edit .env and fill in LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY,
# LANGFUSE_HOST (http://localhost:3000 for local docker compose),
# and your LLM provider key
```

| Variable | Required | Example | Notes |
| --- | --- | --- | --- |
| `LANGFUSE_PUBLIC_KEY` | yes | `pk-lf-123...` | From Step 2 |
| `LANGFUSE_SECRET_KEY` | yes | `sk-lf-123...` | From Step 2 |
| `LANGFUSE_HOST` | only self-hosted | `http://localhost:3000` | Omit for Langfuse Cloud |
| `OPENAI_API_KEY` | for the demo | `sk-...` | Or any LangChain provider |

The Python SDK reads these environment variables automatically — nothing to
wire in code.

## Step 4 — Install dependencies

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Step 5 — Run the demo

```bash
# Full run (requires Langfuse + LLM keys):
python langfuse_langgraph_demo.py

# Attach the handler to the compiled graph instead of per-invocation:
python langfuse_langgraph_demo.py --mode with_config

# Offline smoke test — fake LLM, no keys, no server (verifies wiring only):
python langfuse_langgraph_demo.py --dry-run
```

On a successful live run you will see:

```
✅ Trace exported. View it in the Langfuse UI at http://localhost:3000
```

Open the UI, go to **Tracing → Traces** and click the
`langfuse-langgraph-demo` trace. You should see the graph run with the two
nodes (`agent`, `formatter`) as nested spans and token usage per LLM call.

## Using it in your own LangGraph app

The whole integration is two lines:

```python
from langfuse.langchain import CallbackHandler

langfuse_handler = CallbackHandler()
```

Then pick **one** of the following attach strategies:

**Option A — per invocation (fine-grained control):**

```python
result = graph.invoke(
    {"messages": [HumanMessage(content="hi")]},
    config={"callbacks": [langfuse_handler]},
)
```

**Option B — bake it into the compiled graph (recommended for apps/servers):**

```python
graph = builder.compile().with_config({"callbacks": [langfuse_handler]})
result = graph.invoke({"messages": [HumanMessage(content="hi")]})
```

**Enriching traces** — set these keys in the invocation `config["metadata"]`
and the handler maps them to Langfuse trace fields:

```python
config = {
    "callbacks": [langfuse_handler],
    "run_name": "my-agent-run",           # trace name
    "metadata": {
        "langfuse_user_id": "user-123",   # trace user
        "langfuse_session_id": "abc-456", # groups traces into a session
        "langfuse_tags": ["prod", "v2"],  # trace tags
    },
}
```

**Short-lived scripts** — flush before the process exits so buffered spans
are not lost:

```python
from langfuse import get_client
get_client().flush()
```

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `ModuleNotFoundError: Please install langchain...` | `pip install langchain` — the callback integration requires the `langchain` package, not only `langgraph`. |
| `Authentication error: ... Client will be disabled.` | `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` are not set in the environment of the *process running the graph*. |
| No traces appear in the UI | Confirm `LANGFUSE_HOST` points at the Langfuse **web** server (port `3000` in the default docker compose), and call `get_client().flush()` before exit in short-lived scripts. |
| Traces still missing after flush | Ensure the container is healthy: `docker compose ps`. The worker ingests asynchronously; give it a few seconds and refresh. |
| Connection refused on `localhost:3000` | The compose stack may still be starting. Run `docker compose up -d` again and check `docker compose logs langfuse-web`. |

## Repo map

- This repo (`langgraph` fork): `integrations/langfuse/` — this README, the runnable demo (`langfuse_langgraph_demo.py`), `.env.example`, `requirements.txt`.
- Companion repo (`langfuse` fork): `integrations/langgraph.md` — the same guide mirrored for Langfuse users.

## References

- [Langfuse × LangGraph docs](https://langfuse.com/docs/integrations/langgraph)
- [Langfuse Python SDK](https://github.com/langfuse/langfuse-python)
- [LangGraph docs](https://docs.langchain.com/oss/python/langgraph/overview)
- [Langfuse self-hosting](https://langfuse.com/docs/deployment/self-hosting)

