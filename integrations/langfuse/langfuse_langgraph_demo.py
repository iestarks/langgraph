#!/usr/bin/env python3
"""LangGraph + Langfuse tracing demo.

Builds a two-node LangGraph state graph ("agent" -> "formatter") and sends
every step of the execution to Langfuse via the official Langfuse LangChain
CallbackHandler.

Modes
-----
--mode config        Attach the handler per-invocation via `config={"callbacks": [...]}`
--mode with_config   Attach the handler to the compiled graph via `.with_config()`
--dry-run            Use a fake LLM and skip Langfuse flushing so the demo runs
                     end-to-end with NO API keys and NO Langfuse server.

Usage
-----
    python langfuse_langgraph_demo.py --dry-run
    python langfuse_langgraph_demo.py --mode with_config

Requires LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY (and, for self-hosted,
LANGFUSE_HOST) unless --dry-run is used. See README.md in this directory.
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from typing import Annotated, Optional

from typing_extensions import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langfuse.langchain import CallbackHandler


class State(TypedDict):
    messages: Annotated[list, add_messages]
    answer: Optional[str]


def _build_llm(dry_run: bool):
    """Return a chat model. FakeListChatModel is used for offline dry runs."""
    if dry_run:
        from langchain_core.language_models.fake_chat_models import FakeListChatModel

        return FakeListChatModel(
            responses=[
                "LangGraph is a low-level orchestration framework for building "
                "stateful, multi-actor agents.",
                "Here is a polished summary: LangGraph lets you build stateful "
                "agents that are fully observable in Langfuse.",
            ]
        )

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )


def build_graph(dry_run: bool = False):
    """Compile a two-node graph: agent (LLM call) -> formatter (LLM call)."""
    llm = _build_llm(dry_run)

    def agent(state: State) -> dict:
        """First node: answer the user's question."""
        reply = llm.invoke(
            [
                SystemMessage(content="You are a concise technical assistant."),
                *state["messages"],
            ]
        )
        return {"messages": [reply], "answer": reply.content}

    def formatter(state: State) -> dict:
        """Second node: polish the previous answer (creates a nested span in Langfuse)."""
        polished = llm.invoke(
            [
                SystemMessage(
                    content="Rewrite the following answer as a single polished sentence."
                ),
                HumanMessage(content=str(state["answer"])),
            ]
        )
        return {"messages": [polished], "answer": polished.content}

    builder = StateGraph(State)
    builder.add_node("agent", agent)
    builder.add_node("formatter", formatter)
    builder.add_edge(START, "agent")
    builder.add_edge("agent", "formatter")
    builder.add_edge("formatter", END)
    return builder.compile()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=["config", "with_config"],
        default="config",
        help="How to attach the Langfuse CallbackHandler.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run with a fake LLM and disabled Langfuse client (no keys needed).",
    )
    args = parser.parse_args()

    handler = CallbackHandler()
    graph = build_graph(dry_run=args.dry_run)

    run_config = {
        "run_name": "langfuse-langgraph-demo",
        "metadata": {
            "langfuse_user_id": "demo-user",
            "langfuse_session_id": f"demosession-{uuid.uuid4().hex[:8]}",
            "langfuse_tags": ["langgraph", "demo", "dry-run" if args.dry_run else "live"],
        },
    }

    if args.mode == "with_config":
        graph = graph.with_config({"callbacks": [handler], **run_config})
        config = None
    else:
        config = {"callbacks": [handler], **run_config}

    if args.dry_run:
        print("[dry-run] Langfuse client is disabled; no traces will be exported.")

    result = graph.invoke(
        {
            "messages": [
                HumanMessage(content="What is LangGraph in one sentence?")
            ],
            "answer": None,
        },
        config=config,
    )

    print("\n--- Final answer ---")
    print(result["answer"])

    if not args.dry_run:
        from langfuse import get_client

        get_client().flush()  # ensure all spans are exported before exit
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        print(f"\n✅ Trace exported. View it in the Langfuse UI at {host}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
