"""
report_generator.py
-------------------
Generates the AREOS Citation Transparency Report.
Builds a stunning, dark-mode HTML dashboard featuring 'Inter' font, 
negative space, and interactive source chips for complete citation transparency.
"""

import sqlite3
import pathlib
import json
from textwrap import dedent

# FIX (data-quality pass): PROJECT_ROOT used to be a hardcoded, machine-
# specific Windows dev path (D:\07 Transfer-...\AREOS_COMPLETE_WORKSPACE),
# with a matching sys.path.insert(0, ...) hack. Since this module is
# imported in production (areos/api/routers/reports.py imports
# assemble_markdown_report from here), that ran on every API import —
# harmlessly, since the inserted path never existed and every other
# import in this file already resolves fine via the normal package path,
# but it was fragile leftover-machine cruft. Replaced with the same
# repo-root computation and canonical DB path resolver used elsewhere
# (areos.db.connection.get_db_path()), and dropped the now-unnecessary
# sys.path hack.
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
from areos.db.connection import get_connection, get_db_path

def get_report_data(conn: sqlite3.Connection):
    """Fetches all phases, claims, and sources."""
    # 1. Get Audit Phases (if table exists)
    has_audit_phase = bool(
        conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='audit_phase'").fetchone()
    )
    phases = conn.execute("SELECT audit_phase_id, name, description FROM audit_phase ORDER BY phase_order").fetchall() if has_audit_phase else []
    
    report_data = []
    
    # 2. Get claims for each phase
    # (Since there isn't a direct fk from audit_phase to claim, we map them via the script logic.
    # Wait, earlier we didn't store the mapping of phase->claims in the DB, it was hardcoded.
    # Let me fetch claims and we will bucket them by phase if possible, or just list all active claims.)
    
    # Let's get all active/contested claims
    claims = conn.execute(
        "SELECT claim_id, statement, status, source_tier_value FROM claims WHERE status IN ('active', 'contested') ORDER BY claim_id"
    ).fetchall()
    
    # 3. Get sources for all claims in one query (SEC-19: Eliminate N+1)
    if claims:
        claim_ids = [c["claim_id"] for c in claims]
        placeholders = ",".join("?" * len(claim_ids))
        all_sources = conn.execute(
            f"""
            SELECT 
                ke.kid AS claim_id,
                ks.sid AS source_id,
                ks.sid,
                COALESCE(ks.title, ks.publisher, ks.url) AS name,
                ks.title,
                ks.publisher,
                ks.url,
                ks.authority AS trust_tier,
                ks.authority,
                ks.pub_date,
                ks.excerpt,
                ks.notes,
                CASE WHEN ke.weight = 'primary' THEN 1 ELSE 0 END AS primary_source,
                ke.note,
                ke.weight,
                ke.relationship
            FROM kb_evidence ke
            JOIN kb_sources ks ON ke.sid = ks.sid
            WHERE ke.kid IN ({placeholders})
            ORDER BY ks.authority ASC, primary_source DESC
            """, tuple(claim_ids)
        ).fetchall()
        
        sources_by_claim = {}
        for row in all_sources:
            d = dict(row)
            cid = d.pop("claim_id")
            sources_by_claim.setdefault(cid, []).append(d)
    else:
        sources_by_claim = {}

    claims_with_sources = []
    for c in claims:
        claim_dict = dict(c)
        claim_dict["sources"] = sources_by_claim.get(c["claim_id"], [])
        claims_with_sources.append(claim_dict)
        
    return claims_with_sources

def build_html_report(claims_data, out_path):
    html = dedent("""\
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AREOS Citation Transparency Report</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg: #050505;
                --surface: #111111;
                --surface-hover: #1a1a1a;
                --text-main: #f5f5f5;
                --text-muted: #a0a0a0;
                --accent: #ffffff;
                
                --t1-bg: rgba(56, 189, 248, 0.1);
                --t1-text: #38bdf8;
                --t1-border: rgba(56, 189, 248, 0.3);
                
                --t2-bg: rgba(167, 139, 250, 0.1);
                --t2-text: #a78bfa;
                --t2-border: rgba(167, 139, 250, 0.3);
                
                --t3-bg: rgba(148, 163, 184, 0.1);
                --t3-text: #94a3b8;
                --t3-border: rgba(148, 163, 184, 0.3);
            }
            
            body {
                background-color: var(--bg);
                color: var(--text-main);
                font-family: 'Inter', sans-serif;
                margin: 0;
                padding: 0;
                line-height: 1.6;
                -webkit-font-smoothing: antialiased;
            }
            
            .container {
                max-width: 1000px;
                margin: 0 auto;
                padding: 80px 40px;
            }
            
            header {
                margin-bottom: 80px;
                border-bottom: 1px solid #222;
                padding-bottom: 40px;
            }
            
            h1 {
                font-size: 3rem;
                font-weight: 600;
                letter-spacing: -0.03em;
                margin: 0 0 16px 0;
            }
            
            .subtitle {
                color: var(--text-muted);
                font-size: 1.25rem;
                font-weight: 300;
                max-width: 600px;
            }
            
            .claim-card {
                background: var(--surface);
                border: 1px solid #222;
                border-radius: 12px;
                padding: 32px;
                margin-bottom: 24px;
                transition: transform 0.2s ease, border-color 0.2s ease;
            }
            
            .claim-card:hover {
                border-color: #333;
                transform: translateY(-2px);
            }
            
            .claim-header {
                display: flex;
                align-items: baseline;
                gap: 16px;
                margin-bottom: 16px;
            }
            
            .claim-id {
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.85rem;
                color: var(--text-muted);
                background: #1a1a1a;
                padding: 4px 8px;
                border-radius: 4px;
            }
            
            .claim-status {
                font-size: 0.75rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                font-weight: 600;
            }
            
            .status-active { color: #4ade80; }
            .status-contested { color: #facc15; }
            .status-deprecated { color: #f87171; }
            
            .statement {
                font-size: 1.1rem;
                font-weight: 400;
                margin: 0 0 24px 0;
                color: #e5e5e5;
            }
            
            .sources-list {
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
            }
            
            .chip {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 6px 12px;
                border-radius: 999px;
                font-size: 0.85rem;
                font-weight: 500;
                text-decoration: none;
                transition: all 0.2s ease;
                position: relative;
                cursor: help;
            }
            
            .chip.tier-T1 {
                background: var(--t1-bg);
                color: var(--t1-text);
                border: 1px solid var(--t1-border);
            }
            
            .chip.tier-T2 {
                background: var(--t2-bg);
                color: var(--t2-text);
                border: 1px solid var(--t2-border);
            }
            
            .chip.tier-T3, .chip.tier-T4, .chip.tier-T5, .chip.tier-T6, .chip.tier-T7 {
                background: var(--t3-bg);
                color: var(--t3-text);
                border: 1px solid var(--t3-border);
            }
            
            .chip:hover {
                filter: brightness(1.2);
            }
            
            /* Custom Tooltip */
            .tooltip {
                visibility: hidden;
                width: 300px;
                background-color: #222;
                color: #fff;
                text-align: left;
                border-radius: 8px;
                padding: 12px;
                position: absolute;
                z-index: 10;
                bottom: 125%;
                left: 50%;
                margin-left: -150px;
                opacity: 0;
                transition: opacity 0.2s;
                font-weight: 400;
                font-size: 0.8rem;
                line-height: 1.4;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
                border: 1px solid #333;
            }
            
            .tooltip::after {
                content: "";
                position: absolute;
                top: 100%;
                left: 50%;
                margin-left: -5px;
                border-width: 5px;
                border-style: solid;
                border-color: #333 transparent transparent transparent;
            }
            
            .chip:hover .tooltip {
                visibility: visible;
                opacity: 1;
            }
            
            .tooltip-title {
                font-weight: 600;
                margin-bottom: 4px;
                display: block;
                color: #fff;
            }
            
            .tooltip-note {
                color: #a0a0a0;
                display: block;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Citation Transparency Report</h1>
                <p class="subtitle">AREOS Database Decisions & Source Linkage</p>
            </header>
            
            <main>
    """)
    
    for claim in claims_data:
        status_class = f"status-{claim['status']}"
        html += f"""
                <div class="claim-card">
                    <div class="claim-header">
                        <span class="claim-id">{claim['claim_id']}</span>
                        <span class="claim-status {status_class}">{claim['status']}</span>
                    </div>
                    <p class="statement">{claim['statement']}</p>
                    <div class="sources-list">
        """
        
        for src in claim.get("sources", []):
            tier = src.get("trust_tier", "T3")
            tier_class = f"tier-{tier}"
            note = src.get("note") or "General source linkage."
            primary_badge = "★ " if src.get("primary_source") else ""
            
            html += f"""
                        <div class="chip {tier_class}">
                            {primary_badge}{src['source_id']}: {src['name']}
                            <span class="tooltip">
                                <span class="tooltip-title">{src['name']} ({tier})</span>
                                <span class="tooltip-note">{note}</span>
                            </span>
                        </div>
            """
            
        if not claim.get("sources"):
            html += """<span class="chip" style="background:#222;color:#666;border:1px solid #333;">Unlinked</span>"""
            
        html += """
                    </div>
                </div>
        """
        
    html += dedent("""\
            </main>
        </div>
    </body>
    </html>
    """)
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return html

def build_markdown_report(claims_data, out_path):
    """Fallback Markdown version."""
    md = "# AREOS Citation Transparency Report\n\n"
    for claim in claims_data:
        md += f"### `{claim['claim_id']}` [{claim['status'].upper()}]\n"
        md += f"> {claim['statement']}\n\n"
        
        if claim.get("sources"):
            md += "**Sources:**\n"
            for src in claim["sources"]:
                p = "★ " if src.get("primary_source") else ""
                note = src.get("note") or ""
                md += f"- {p}**{src['source_id']} ({src['trust_tier']})**: {src['name']} — _{note}_\n"
        else:
            md += "_No sources linked._\n"
        md += "\n---\n\n"
        
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)
    return md

if __name__ == "__main__":
    print("Generating reports...")
    conn = get_connection(get_db_path())
    claims_data = get_report_data(conn)
    
    html_out = PROJECT_ROOT / "AREOS_Citation_Transparency_Report.html"
    build_html_report(claims_data, html_out)
    
    md_out = PROJECT_ROOT / "AREOS_Citation_Transparency_Report.md"
    build_markdown_report(claims_data, md_out)
    
    print(f"Generated HTML report: {html_out}")
    print(f"Generated MD report: {md_out}")

def assemble_markdown_report(base_report_md: str, verdicts_list: list[dict]) -> str:
    """
    MF-4: Extracted from main.py's get_final_report.
    Appends the human auditor verdicts section to the generated gap report.
    """
    verdict_section = "\n\n---\n\n## Human Auditor Verdicts\n\n"
    if verdicts_list:
        by_card = {}
        for v in verdicts_list:
            by_card.setdefault(v["card_id"], []).append(v)
        for card_id, entries in by_card.items():
            verdict_section += f"### {card_id}\n"
            for e in entries:
                icon = {"pass": "OK", "warn": "WARN", "fail": "FAIL", "na": "N/A"}.get(
                    e["verdict"], e["verdict"].upper()
                )
                page_url = e.get("page_url") or "general"
                verdict_section += f"- **[{icon}]** {page_url}: {e['notes']}\n"
            verdict_section += "\n"
    else:
        verdict_section += "_No manual verdicts submitted yet._\n"
        
    return base_report_md + verdict_section
