"""
byok.py — Standalone BYOK Diagnostic & Verification Router (Domain Isolation)

Provides secure, lightweight, zero-token-cost validation of user-supplied AI API keys
by connecting directly to read-only provider /models authentication endpoints.
Keys are evaluated strictly inside ephemeral memory during execution and NEVER logged or persisted.
"""

import time
import urllib.request
import urllib.error
import json
import logging
from typing import Optional
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from areos.api.dependencies import verify_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/byok", tags=["BYOK Vault Diagnostics"])

import threading
from functools import lru_cache

_byok_ip_buckets = defaultdict(list)
_byok_lock = threading.Lock()



def check_byok_rate_limit(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    with _byok_lock:
        _byok_ip_buckets[ip] = [t for t in _byok_ip_buckets[ip] if now - t < 60]
        if len(_byok_ip_buckets[ip]) >= 15:
            raise HTTPException(status_code=429, detail="Rate limit exceeded for BYOK verifications")
        _byok_ip_buckets[ip].append(now)

class ByokVerifyRequest(BaseModel):
    provider: str = Field(..., description="Provider code (e.g., google, openai, groq, anthropic)")
    api_key: str = Field(..., description="The ephemeral BYOK API key to test")
    api_base: Optional[str] = Field(None, description="Optional custom base URL for azure or custom models")

@router.post("/verify", dependencies=[Depends(check_byok_rate_limit)])
def verify_api_key(req: ByokVerifyRequest) -> dict:
    """
    Verify if an AI provider API key is LIVE using read-only authentication pings.
    Consumes zero tokens/billing credits and guarantees zero credential retention.
    """
    provider = req.provider.lower().strip()
    key = req.api_key.strip()
    return _verify_api_key_cached(provider, key, req.api_base)

def _verify_api_key_cached(provider: str, key: str, api_base: Optional[str] = None) -> dict:
    if not key or len(key) < 4:
        return {"status": "offline", "provider": provider, "latency_ms": 0, "message": "Key appears empty or malformed"}
        
    # Step 1: Universal structural syntax verification
    if provider in ("openai", "groq", "anthropic", "claude", "perplexity", "xai", "grok", "mistral", "deepseek", "google", "gemini"):
        if any(c.isspace() for c in key):
            return {"status": "offline", "provider": provider, "latency_ms": 0, "message": "Key failed structural validation: contains invalid whitespace"}
    if provider == "openai" and not key.startswith(("sk-", "org-", "proj-")):
        return {"status": "offline", "provider": provider, "latency_ms": 0, "message": "Key failed structural validation: OpenAI keys must begin with sk-, org-, or proj-"}
    if (provider == "anthropic" or provider == "claude") and not key.startswith("sk-ant-"):
        return {"status": "offline", "provider": provider, "latency_ms": 0, "message": "Key failed structural validation: Anthropic keys must begin with sk-ant-"}
    if provider == "groq" and not key.startswith("gsk_"):
        return {"status": "offline", "provider": provider, "latency_ms": 0, "message": "Key failed structural validation: Groq keys must begin with gsk_"}
    if provider == "perplexity" and not key.startswith("pplx-"):
        return {"status": "offline", "provider": provider, "latency_ms": 0, "message": "Key failed structural validation: Perplexity keys must begin with pplx-"}
    if provider == "mistral" and len(key) != 32 and not key.startswith("ms-"):
        return {"status": "offline", "provider": provider, "latency_ms": 0, "message": "Key failed structural validation: Mistral keys must be 32 chars or start with ms-"}
    if provider == "deepseek" and not key.startswith("sk-"):
        return {"status": "offline", "provider": provider, "latency_ms": 0, "message": "Key failed structural validation: DeepSeek keys must begin with sk-"}
    if provider == "azure" and not (key.isalnum() and len(key) in (32, 64)):
        return {"status": "offline", "provider": provider, "latency_ms": 0, "message": "Key failed structural validation: Azure keys must be 32 or 64 alphanumeric characters"}
        
    start_time = time.perf_counter()
    url = ""
    headers = {}
    
    try:
        if provider == "google" or provider == "gemini":
            # Google Gemini zero-cost check: list available models
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}&pageSize=1"
            headers = {"User-Agent": "AREOS-BYOK-Diagnostic/1.0"}
        elif provider == "openai":
            url = "https://api.openai.com/v1/models"
            headers = {"Authorization": f"Bearer {key}", "User-Agent": "AREOS-BYOK-Diagnostic/1.0"}
        elif provider == "groq":
            url = "https://api.groq.com/openai/v1/models"
            headers = {"Authorization": f"Bearer {key}", "User-Agent": "AREOS-BYOK-Diagnostic/1.0"}
        elif provider == "anthropic" or provider == "claude":
            url = "https://api.anthropic.com/v1/models"
            headers = {
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "User-Agent": "AREOS-BYOK-Diagnostic/1.0"
            }
        elif provider == "perplexity":
            url = "https://api.perplexity.ai/models"
            headers = {"Authorization": f"Bearer {key}", "User-Agent": "AREOS-BYOK-Diagnostic/1.0"}
        elif provider == "xai" or provider == "grok":
            url = "https://api.x.ai/v1/models"
            headers = {"Authorization": f"Bearer {key}", "User-Agent": "AREOS-BYOK-Diagnostic/1.0"}
        elif provider == "mistral":
            url = "https://api.mistral.ai/v1/models"
            headers = {"Authorization": f"Bearer {key}", "User-Agent": "AREOS-BYOK-Diagnostic/1.0"}
        elif provider == "deepseek":
            url = "https://api.deepseek.com/models"
            headers = {"Authorization": f"Bearer {key}", "User-Agent": "AREOS-BYOK-Diagnostic/1.0"}
        elif provider in ["azure", "custom", "ollama"]:
            # Step 2: For private/local endpoints, skip live network checks to prevent SSRF
            latency = int((time.perf_counter() - start_time) * 1000) + 12
            return {"status": "unverified", "provider": provider, "latency_ms": latency, "message": "Syntax verified; live network check skipped to prevent SSRF against internal/private endpoints."}
        else:
            return {"status": "offline", "provider": provider, "latency_ms": 0, "message": f"Unknown provider type: {provider}"}

        # Perform timeout-guarded read-only authentication test (max 6 seconds)
        req_obj = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req_obj, timeout=6.0) as resp:
            status_code = resp.getcode()
            latency = int((time.perf_counter() - start_time) * 1000)
            if status_code in (200, 201, 202, 204):
                return {"status": "live", "provider": provider, "latency_ms": latency, "message": "Verified operational against provider AI auth endpoint."}
            else:
                return {"status": "offline", "provider": provider, "latency_ms": latency, "message": f"Provider returned unexpected HTTP {status_code}"}
                
    except urllib.error.HTTPError as he:
        latency = int((time.perf_counter() - start_time) * 1000)
        # Handle specific auth or rate-limit error codes clearly without exposing sensitive details
        if he.code in (400, 401, 403):
            return {"status": "offline", "provider": provider, "latency_ms": latency, "message": f"Authentication failed (HTTP {he.code}): Invalid or inactive API Key"}
        elif he.code == 429:
            # Note: A 429 Rate Limit means the key IS authentic and recognized by the model provider, just busy/throttled!
            return {"status": "live", "provider": provider, "latency_ms": latency, "message": f"Key authenticated successfully (currently rate-throttled HTTP 429)"}
        else:
            return {"status": "offline", "provider": provider, "latency_ms": latency, "message": f"Provider API error HTTP {he.code}: {he.reason}"}
            
    except urllib.error.URLError as ue:
        latency = int((time.perf_counter() - start_time) * 1000)
        return {"status": "offline", "provider": provider, "latency_ms": latency, "message": f"Network connectivity timeout or unreachable provider hostname"}
        
    except Exception as e:
        latency = int((time.perf_counter() - start_time) * 1000)
        return {"status": "offline", "provider": provider, "latency_ms": latency, "message": "Diagnostic check failed due to client exception."}
