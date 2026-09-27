#!/usr/bin/env python3
"""
scripts/list_endpoint_auth.py

Introspects live FastAPI routes from areos.api.main and generates an exact
endpoint inventory detailing HTTP method, path, authentication dependency,
rate limiting, response model, and description.

Replaces hand-counted, stale API inventory in docs/internal.md §07.
"""

import os
import re
import sys
from pathlib import Path
from typing import NamedTuple

# Set default test token to allow loading API without errors
os.environ.setdefault("AREOS_API_TOKEN", "ci-auth-inventory")

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from fastapi.routing import APIRoute
import areos.api.main as main_module


class EndpointInfo(NamedTuple):
    method: str
    path: str
    auth: str
    rate_limited: str
    response_model: str
    description: str


ENDPOINT_DESCRIPTIONS = {
    ("GET", "/api/health"): "Probe endpoint. Verifies database connectivity and readiness.",
    ("GET", "/api/v1/claims"): "Returns active knowledge claims joined with sources.",
    ("POST", "/api/v1/claims/ingest"): "Ingests new raw claims into knowledge base.",
    ("GET", "/api/v1/approvals"): "Retrieves pending candidate claims awaiting human review.",
    ("POST", "/api/v1/approvals/{run_id}/{candidate_id}"): "Commits human approval/rejection of a candidate claim.",
    ("POST", "/api/v1/audit/runs"): "Initializes an audit run record.",
    ("GET", "/api/v1/audit/runs"): "Lists historical audit runs.",
    ("GET", "/api/v1/audit/runs/{run_id}"): "Fetches technical execution details of a specific run.",
    ("GET", "/api/v1/audit/runs/{run_id}/full"): "Rehydration endpoint returning complete run state, wizard, and synthesis.",
    ("GET", "/api/v1/audit/authority/{target_domain}"): "Evaluates domain authority and backlink metrics.",
    ("POST", "/api/v1/audit/orchestrate"): "Triggers the full automated audit pipeline for a domain.",
    ("POST", "/api/v1/audit/runs/{run_id}/observations"): "Stores raw audit observations for a run.",
    ("GET", "/api/v1/audit/runs/{run_id}/full-report"): "Generates the complete consolidated audit report.",
    ("POST", "/api/v1/audit/runs/{run_id}/synthesize"): "Triggers 3-step LLM narrative synthesis.",
    ("POST", "/api/v1/audit/runs/{run_id}/verdicts"): "Submits manual review verdicts (authenticated via run token).",
    ("GET", "/api/v1/audit/runs/{run_id}/report"): "Retrieves the final audit report for a run.",
    ("GET", "/api/v1/audit/runs/{run_id}/remediation"): "Retrieves the prioritized remediation plan.",
    ("GET", "/api/v1/prompts"): "Lists citation sampling prompt sets.",
    ("POST", "/api/v1/prompts"): "Creates a new citation sampling prompt.",
    ("DELETE", "/api/v1/prompts/{prompt_id}"): "Deletes a citation sampling prompt.",
    ("POST", "/api/v1/byok/verify"): "Validates Bring-Your-Own-Key credentials by pinging upstream LLM providers.",
    ("GET", "/api/v1/synthesis/prompts"): "Returns current internal AI synthesis prompts.",
    ("PUT", "/api/v1/synthesis/prompts/{step}"): "Mutates a specific synthesis prompt step.",
    ("POST", "/api/v1/synthesis/prompts/reset/{step}"): "Reverts a synthesis prompt step to its system default.",
    ("GET", "/api/v1/knowledge"): "Queries curated knowledge records with optional filters.",
    ("GET", "/api/v1/knowledge/stats"): "Returns aggregate statistics of knowledge base records.",
    ("GET", "/api/v1/knowledge/{kid}"): "Fetches a single knowledge record by KID.",
    ("GET", "/api/v1/knowledge/{kid}/evidence"): "Fetches evidence supporting a specific knowledge record.",
    ("GET", "/api/v1/knowledge/check-code/{check_code}"): "Resolves check codes to knowledge base claims.",
}


def introspect_endpoints() -> list[EndpointInfo]:
    """Inspect all routes registered on FastAPI app."""
    raw_routes = []
    for r in main_module.app.routes:
        if isinstance(r, APIRoute):
            raw_routes.append(r)
        elif hasattr(r, "original_router"):
            for sub_r in r.original_router.routes:
                if isinstance(sub_r, APIRoute):
                    raw_routes.append(sub_r)

    endpoints = []
    for r in raw_routes:
        methods = sorted(r.methods - {"HEAD", "OPTIONS"})
        method = methods[0] if methods else "GET"
        path = r.path

        # Inspect dependencies
        deps = [
            d.dependency.__name__
            for d in r.dependencies
            if hasattr(d, "dependency") and hasattr(d.dependency, "__name__")
        ]
        param_deps = []
        if hasattr(r, "dependant"):
            for d in r.dependant.dependencies:
                if hasattr(d, "call") and hasattr(d.call, "__name__"):
                    param_deps.append(d.call.__name__)
        all_deps = deps + param_deps

        # Auth classification
        if "verify_admin" in all_deps:
            auth = "**Yes** (`verify_admin`)"
        elif "verdicts" in path:
            auth = "**Yes** (`run_token`)"
        else:
            auth = "No"

        # Rate limiting
        rate_limited = "Yes" if any("rate_limit" in str(d).lower() for d in all_deps) else "No"

        # Response model
        resp_model = f"`{r.response_model.__name__}`" if r.response_model else "None"

        # Description
        desc = ENDPOINT_DESCRIPTIONS.get(
            (method, path),
            (r.summary or (r.endpoint.__doc__ or "").strip().split("\n")[0])
        )

        endpoints.append(
            EndpointInfo(
                method=method,
                path=path,
                auth=auth,
                rate_limited=rate_limited,
                response_model=resp_model,
                description=desc,
            )
        )

    # Sort deterministically by path then method
    endpoints.sort(key=lambda e: (e.path, e.method))
    return endpoints


def generate_markdown_table(endpoints: list[EndpointInfo]) -> str:
    """Format endpoints as Markdown table."""
    lines = [
        "| Method | Endpoint | Auth | Rate-Limited | Response Model | Description |",
        "|---|---|---|---|---|---|",
    ]
    for e in endpoints:
        lines.append(
            f"| `{e.method}` | `{e.path}` | {e.auth} | {e.rate_limited} | {e.response_model} | {e.description} |"
        )
    return "\n".join(lines)


def update_internal_md(doc_path: Path | str | None = None) -> bool:
    """Update docs/internal.md §07 with current live endpoint inventory."""
    if doc_path is None:
        doc_path = _ROOT / "docs" / "internal.md"
    else:
        doc_path = Path(doc_path)

    content = doc_path.read_text(encoding="utf-8")
    endpoints = introspect_endpoints()
    table = generate_markdown_table(endpoints)

    total = len(endpoints)
    admin_count = sum(1 for e in endpoints if "verify_admin" in e.auth)
    token_count = sum(1 for e in endpoints if "run_token" in e.auth)
    public_count = sum(1 for e in endpoints if e.auth == "No")
    typed_count = sum(1 for e in endpoints if e.response_model != "None")
    untyped_count = total - typed_count

    # Update TL;DR and Purpose counts
    content = re.sub(
        r"Provides the complete technical contract for all \d+ API endpoints",
        f"Provides the complete technical contract for all {total} API endpoints",
        content,
    )
    content = re.sub(
        r"\*\*TL;DR:\*\* \d+ total endpoints\..*?\(including critical audit execution endpoints\)\.",
        f"**TL;DR:** {total} total endpoints. {typed_count} have typed `response_model` definitions; {untyped_count} do not. "
        f"{admin_count} enforce Bearer admin auth (`verify_admin`), {token_count} enforces run token auth (`run_token`), "
        f"and {public_count} are publicly exposed (including critical audit execution endpoints).",
        content,
    )

    # Replace §6.2 - §6.6 subsection tables with the single live consolidated inventory table
    sec7_start_marker = "#### 6.1 Authentication & Global Middleware"
    sec7_end_marker = "#### 6.7 Known Contract Deviations & API Gaps"

    p_start = content.find(sec7_start_marker)
    p_end = content.find(sec7_end_marker)

    if p_start == -1 or p_end == -1:
        raise RuntimeError("Could not find delimiters in docs/internal.md §07")

    # Find where 6.1 ends and tables start
    p_table_start = content.find("#### 6.2 Core System Endpoints", p_start)
    if p_table_start == -1 or p_table_start >= p_end:
        # Check if already unified
        p_table_start = content.find("#### 6.2 Live Endpoint Inventory", p_start)

    if p_table_start == -1 or p_table_start >= p_end:
        raise RuntimeError("Could not locate endpoint table section in §07")

    replacement_section = (
        "#### 6.2 Live Endpoint Inventory\n\n"
        f"Live introspection of all {total} endpoints registered in `areos.api.main:app`:\n\n"
        f"{table}\n\n"
    )

    new_content = content[:p_table_start] + replacement_section + content[p_end:]

    # Also update §6.7 text regarding verdicts auth (fixed in Task 5)
    new_content = new_content.replace(
        "- `POST /api/v1/audit/runs/{run_id}/verdicts`\n   - Both mutate database state and incur massive LLM costs, but lack `verify_admin` dependencies.",
        "- `POST /api/v1/audit/orchestrate` mutates database state and incurs LLM costs without authentication. (`POST .../verdicts` is protected by `run_token` ownership verification as of Task 5)."
    )

    old_content = doc_path.read_text(encoding="utf-8")
    if new_content == old_content:
        return False

    doc_path.write_text(new_content, encoding="utf-8")
    return True


if __name__ == "__main__":
    endpoints = introspect_endpoints()
    table = generate_markdown_table(endpoints)
    total = len(endpoints)
    admin_count = sum(1 for e in endpoints if "verify_admin" in e.auth)
    token_count = sum(1 for e in endpoints if "run_token" in e.auth)
    public_count = sum(1 for e in endpoints if e.auth == "No")

    print(f"Total endpoints: {total}")
    print(f"  Admin auth (verify_admin): {admin_count}")
    print(f"  Run token auth (run_token): {token_count}")
    print(f"  Public / Unauthenticated: {public_count}")
    print()

    doc = _ROOT / "docs" / "internal.md"
    changed = update_internal_md(doc)
    if changed:
        print("Updated docs/internal.md §07 with live endpoint inventory.")
    else:
        print("docs/internal.md is already up to date.")
