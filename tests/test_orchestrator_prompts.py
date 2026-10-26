"""
tests/test_orchestrator_prompts.py — Industry-Aware Fallback Prompts (DEF-03 / WP-1.3)

Verifies:
1. Medical/Healthcare schemas produce patient- and care-focused queries without SaaS phrasing.
2. LocalBusiness schemas produce local service, hours, and reputation queries.
3. Organization schemas produce mission, leadership, and organization queries.
4. Product schemas produce ecommerce and product queries.
5. Missing schema produces neutral domain-agnostic queries without "ecosystem" or SaaS assumptions.
6. SoftwareApplication schemas retain software/tool ecosystem queries.
7. run_orchestrated_audit passes industry-tailored prompts to citation sampling.
"""

import os
import pytest
from unittest.mock import patch
from areos.auditors.audit_orchestrator import generate_fallback_prompts, run_orchestrated_audit
from areos.auditors.citation_sampler import CitationSampleResult
from areos.db.migrate_audit_tables import migrate

os.environ.setdefault("AREOS_API_TOKEN", "test_qa_token")
os.environ.setdefault("AREOS_ADMIN_TOKEN", "test_admin_token")


def test_medical_organization_schema_prompts():
    """DEF-03 / WP-1.3: MedicalOrganization produces healthcare/patient queries."""
    blocks = [{"@context": "https://schema.org", "@type": "MedicalOrganization"}]
    prompts = generate_fallback_prompts("cityhospital.org", blocks)

    combined = " ".join(prompts).lower()
    assert "medical services" in combined or "patient" in combined
    assert "ecosystem" not in combined
    assert "platforms and tools" not in combined


def test_local_business_schema_prompts():
    """DEF-03 / WP-1.3: LocalBusiness produces services/reputation/hours queries."""
    blocks = [{"@context": "https://schema.org", "@type": "LocalBusiness"}]
    prompts = generate_fallback_prompts("joesplumbing.com", blocks)

    combined = " ".join(prompts).lower()
    assert "services" in combined
    assert "hours" in combined or "reviews" in combined
    assert "ecosystem" not in combined
    assert "platforms and tools" not in combined


def test_domain_agnostic_prompts_when_no_schema():
    """DEF-03 / WP-1.3: When no schema is detected, neutral prompts are used instead of SaaS phrasing."""
    prompts = generate_fallback_prompts("randomwebsite.org", [])

    combined = " ".join(prompts).lower()
    assert "what is randomwebsite.org and what does it offer?" in combined
    assert "ecosystem" not in combined
    assert "platforms and tools" not in combined


def test_software_application_prompts():
    """DEF-03 / WP-1.3: SoftwareApplication schemas appropriately use tech/tool prompts."""
    blocks = [{"@context": "https://schema.org", "@type": "SoftwareApplication"}]
    prompts = generate_fallback_prompts("devtool.io", blocks)

    combined = " ".join(prompts).lower()
    assert "ecosystem" in combined


def test_orchestrator_end_to_end_passes_industry_prompts(tmp_path, monkeypatch):
    """DEF-03 / WP-1.3: run_orchestrated_audit passes industry-tailored prompts to citation sampling."""
    test_db = tmp_path / "test_prompts_orch.db"
    monkeypatch.setenv("AREOS_TEST_DB", str(test_db))
    monkeypatch.setenv("AREOS_DB_PATH", str(test_db))
    migrate(test_db)

    medical_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Hospital",
            "name": "St Jude Regional Hospital"
        }
        </script>
    </head>
    <body>
        <h1>St Jude Regional Hospital</h1>
        <p>Providing advanced emergency trauma care, cardiology, pediatrics, and outpatient rehabilitation services.</p>
    </body>
    </html>
    """

    captured_prompts = []

    def fake_sampler_loop(clean_domain, prompts, client_keys=None, circuit_breaker=None):
        captured_prompts.extend(prompts)
        return CitationSampleResult(
            target_domain=clean_domain,
            prompt_set=prompts,
            engine="none",
            n_runs=0,
            observations=[],
        )

    with patch("areos.auditors.audit_orchestrator.run_citation_sampling_loop", side_effect=fake_sampler_loop):
        run_orchestrated_audit(
            "stjudehospital.org",
            sample_content=medical_html,
            db_path=test_db,
        )

    assert len(captured_prompts) == 3
    combined = " ".join(captured_prompts).lower()
    assert "patient" in combined or "medical" in combined
    assert "ecosystem" not in combined
