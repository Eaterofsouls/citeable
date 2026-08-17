# areos/services/adversarial_service.py
#
# Core logic for Task 2f: The Adversarial Check Step.
# Formalizes the critique pattern into a reusable script.
#
# CONTRACT:
#   - Uses complete_adversarial() to guarantee cognitive diversity.
#   - Returns markdown critique based on a fixed prompt-per-persona.

from __future__ import annotations
import logging
from areos.llm import providers

logger = logging.getLogger(__name__)

PERSONAS = {
    "archivist": """You are the Lead Archivist for the AREOS project.
Your primary mandate is STRICT ADHERENCE to canonical definitions, ontologies, and documentation structures (like the Technical Manifesto and standing rules).
You do not care about code functioning; you care about whether the artifact aligns with documented reality and terminology.
If the artifact introduces new terms silently, or contradicts the project scope, flag it as a VIOLATION.""",

    "factchecker": """You are the Senior Fact-Checker.
Your mandate is empirical truth and internal consistency.
If the artifact makes a claim about an external system (e.g. "Perplexity uses X"), you demand to see the source citation.
If the artifact makes a claim about the project's own state (e.g. "We have 10 sources"), you verify if that matches reality.
Flag any hallucinations, unsupported claims, or logical contradictions.""",

    "hostilereviewer": """You are a Red Team / Hostile Reviewer.
Your mandate is to tear down assumptions. You assume the author of the artifact is taking shortcuts, hiding complexity, or lying to themselves about what is actually built.
You look for "happy path" thinking. You demand proof of edge-case handling.
Your tone should be professional but relentlessly skeptical. You are not here to be nice; you are here to prevent catastrophic architecture mistakes.""",
}

def generate_critique(artifact_text: str, persona: str, client_keys: dict | None = None) -> str:
    """
    Generate an adversarial critique for the given artifact text using a specific persona.
    """
    if persona not in PERSONAS:
        raise ValueError(f"Unknown persona: {persona}. Available: {list(PERSONAS.keys())}")
        
    system_prompt = PERSONAS[persona]
    
    prompt = f"""Please review the following artifact and provide your critique based on your mandate.

=== ARTIFACT BEGIN ===
{artifact_text}
=== ARTIFACT END ===

Your critique:"""

    logger.info(f"Generating critique using persona '{persona}' via adversarial LLM cascade...")
    try:
        response = providers.complete_adversarial(prompt, system=system_prompt, client_keys=client_keys)
        return response
    except Exception as e:
        logger.error(f"Failed to generate critique: {e}")
        return f"[CRITIQUE FAILED] The adversarial model cascade could not generate a critique. Error: {e}"
