#!/usr/bin/env python3
"""Offline demo of the revoke-token-agent LangGraph pipeline.

Rebuilds the same node pipeline used by the companion repo
(https://github.com/iestarks/revoke-token-agent) against fixture data, so the
discovery flow can be smoke-tested end-to-end with NO Azure credentials and
NO network access.

Usage
-----
    pip install -r requirements.txt   # langgraph from the iestarks/langgraph fork
    python revoke_token_agent_demo.py
"""

from __future__ import annotations

import sys
from typing import Any, Optional

from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph

# --- Well-known privileged Entra ID role template IDs (subset of the agent's list) ---
PRIVILEGED_ROLE_TEMPLATES = {
    "62e90394-69f5-4237-9190-012177145e10": "Global Administrator",
    "e8611ab8-c189-46e8-94e1-60213ab1f814": "Privileged Role Administrator",
    "194ae4cb-b126-40b2-bd5e-6091b380977d": "Security Administrator",
}

# --- Fixture mirroring GET /v1.0/directoryRoles?$expand=members ---
DEMO_ROLES: list[dict[str, Any]] = [
    {
        "id": "role-0001",
        "displayName": "Global Administrator",
        "roleTemplateId": "62e90394-69f5-4237-9190-012177145e10",
        "members": [
            {
                "@odata.type": "#microsoft.graph.user",
                "id": "u-0001",
                "displayName": "Ada Lovelace",
                "userPrincipalName": "ada.lovelace@contoso.com",
            },
            {
                "@odata.type": "#microsoft.graph.servicePrincipal",
                "id": "sp-0001",
                "displayName": "terraform-prod-spn",
                "appId": "0e5d0a4e-1111-4000-8000-0000000000aa",
            },
        ],
    },
    {
        "id": "role-0002",
        "displayName": "Security Administrator",
        "roleTemplateId": "194ae4cb-b126-40b2-bd5e-6091b380977d",
        "members": [
            {
                "@odata.type": "#microsoft.graph.group",
                "id": "g-0001",
                "displayName": "sg-security-admins",
            },
        ],
    },
    {
        "id": "role-0003",
        "displayName": "Directory Readers",  # non-privileged — filtered out
        "roleTemplateId": "88d8e3e3-8f55-4a1e-953a-9b9898b8876b",
        "members": [],
    },
]


class DemoState(TypedDict, total=False):
    roles: list[dict[str, Any]]
    privileged_roles: list[dict[str, Any]]
    assignments: list[dict[str, Any]]
    report: str
    error: Optional[str]


def discover_roles(state: DemoState) -> dict[str, Any]:
    """Live agent: GET /v1.0/directoryRoles?$expand=members. Demo: fixtures."""
    return {"roles": DEMO_ROLES}


def filter_privileged_roles(state: DemoState) -> dict[str, Any]:
    privileged = [
        r
        for r in state.get("roles", [])
        if r.get("roleTemplateId") in PRIVILEGED_ROLE_TEMPLATES
    ]
    return {"privileged_roles": privileged}


def enumerate_members(state: DemoState) -> dict[str, Any]:
    assignments = []
    for role in state.get("privileged_roles", []):
        for member in role.get("members") or []:
            assignments.append(
                {
                    "role_name": role["displayName"],
                    "member_type": member.get("@odata.type", "").rsplit(".", 1)[-1],
                    "display_name": member.get("displayName", ""),
                    "principal_name": member.get("userPrincipalName")
                    or member.get("appId")
                    or "",
                    "member_id": member.get("id", ""),
                }
            )
    return {"assignments": assignments}


def build_report(state: DemoState) -> dict[str, Any]:
    lines = ["Azure Privileged Account Discovery — offline demo", ""]
    for a in state.get("assignments", []):
        lines.append(
            f"  [{a['role_name']}] {a['member_type']}: {a['display_name']} "
            f"<{a['principal_name'] or a['member_id']}>"
        )
    lines.append("")
    lines.append(f"TOTAL: {len(state.get('assignments', []))} privileged assignment(s)")
    return {"report": "\n".join(lines)}


def build_graph():
    builder = StateGraph(DemoState)
    builder.add_node("discover_roles", discover_roles)
    builder.add_node("filter_privileged_roles", filter_privileged_roles)
    builder.add_node("enumerate_members", enumerate_members)
    builder.add_node("report", build_report)
    builder.add_edge(START, "discover_roles")
    builder.add_edge("discover_roles", "filter_privileged_roles")
    builder.add_edge("filter_privileged_roles", "enumerate_members")
    builder.add_edge("enumerate_members", "report")
    builder.add_edge("report", END)
    return builder.compile()


def main() -> int:
    result = build_graph().invoke({"error": None})
    print(result["report"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
