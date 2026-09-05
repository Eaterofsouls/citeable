# API Reference & Integration

This document outlines the Citeable (AREOS) REST API, detailing endpoints, authentication, and integration patterns for interacting with the audit engine and knowledge governance system.

## 1. API Overview

The Citeable API is a FastAPI application serving JSON REST endpoints mounted under `/api/v1/`. The API surface is divided into two security domains:
- **Public Endpoints**: Read-only data access and audit execution (which relies on Bring-Your-Own-Key for cost control).
- **Admin Endpoints**: Privileged operations for knowledge governance, manual reviews, and system configuration.

Key features include:
- Rate limiting on compute-intensive endpoints (e.g., orchestration, synthesis).
- Idempotency support for write operations to safely handle retries.
- Structured error responses with correlation IDs to facilitate debugging without leaking internal stack traces.

## 2. Authentication

Admin endpoints require authentication via a Bearer token. 

- **Header Format**: `Authorization: Bearer {token}`
- **Server Configuration**: The valid token is defined by the `AREOS_API_TOKEN` environment variable on the server. If this variable is missing at startup, the server fails to start, preventing unauthenticated access by default.
- **Timing Attack Prevention**: Token validation uses `hmac.compare_digest()` for constant-time comparison, mitigating timing attacks.
- **Analyst Attribution**: For admin operations, an optional `X-Analyst-Id` header can be provided to attribute changes to a specific analyst in the audit log.

## 3. Complete Endpoint Inventory

> *By calling audit endpoints, you represent that you own the target domain or have obtained authorization from the domain owner. See [Legal](legal.md) for the full Acceptable Use Policy.*

### Audit Execution
| Method | Path | Auth | Rate Limit | Purpose |
|--------|------|------|------------|---------|
| `POST` | `/api/v1/audit/orchestrate` | Public | 3/min/IP | Trigger a full automated audit orchestration |
| `POST` | `/api/v1/audit/runs` | Public | - | Initialize a new audit run manually |
| `GET`  | `/api/v1/audit/authority/{target_domain}` | Public | 3/min/IP | Execute or retrieve domain authority checks |
| `POST` | `/api/v1/audit/runs/{run_id}/synthesize` | Public | 3/min/IP | Trigger final synthesis of audit findings |

### Audit Results & Reports
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET`  | `/api/v1/audit/runs` | Public | List historical audit runs |
| `GET`  | `/api/v1/audit/runs/{run_id}` | Public | Get metadata for a specific audit run |
| `GET`  | `/api/v1/audit/runs/{run_id}/full` | Public | Rehydrate the full audit state and results |
| `GET`  | `/api/v1/audit/runs/{run_id}/full-report` | Public | Retrieve a unified view of the run |
| `GET`  | `/api/v1/audit/runs/{run_id}/report` | Public | Get the final scored report for the run |
| `GET`  | `/api/v1/audit/runs/{run_id}/remediation` | Public | Retrieve the generated remediation plan |

### Manual Review
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/api/v1/audit/runs/{run_id}/observations` | Admin | Submit a manual observation to the audit |
| `POST` | `/api/v1/audit/runs/{run_id}/verdicts` | Admin | Submit a manual verdict on an automated finding |
| `GET`  | `/api/v1/approvals` | Admin | Get list of pending manual approvals |
| `POST` | `/api/v1/approvals/{run_id}/{candidate_id}` | Admin | Process a specific pending approval |

### Knowledge Base
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET`  | `/api/v1/knowledge` | Public | List stored knowledge base entities |
| `GET`  | `/api/v1/knowledge/stats` | Public | Retrieve high-level statistics for the knowledge base |
| `GET`  | `/api/v1/knowledge/{kid}` | Public | Get details for a specific Knowledge ID |
| `GET`  | `/api/v1/knowledge/{kid}/evidence` | Public | Retrieve the evidence chain for a specific knowledge entry |
| `GET`  | `/api/v1/knowledge/check-code/{check_code}` | Public | Query knowledge base by specific check code |
| `GET`  | `/api/v1/claims` | Public | Retrieve verified claims |

### Knowledge Governance
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/api/v1/claims/ingest` | Admin | Ingest a new claim into the knowledge base |

### Configuration
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET`  | `/api/v1/prompts` | Admin | List active prompt templates |
| `POST` | `/api/v1/prompts` | Admin | Create or update a prompt template |
| `DELETE`| `/api/v1/prompts/{prompt_id}` | Admin | Delete a specific prompt template |
| `GET`  | `/api/v1/synthesis/prompts` | Admin | Retrieve the current synthesis prompts |
| `PUT`  | `/api/v1/synthesis/prompts/{step}` | Admin | Update a specific synthesis prompt step |
| `POST` | `/api/v1/synthesis/prompts/reset/{step}` | Admin | Reset a synthesis prompt step to default |

### System
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/api/v1/byok/verify` | Public | Verify validity of a Bring-Your-Own-Key token |

## 4. Key Request/Response Examples

### Example 1: Trigger an Audit

```http
POST /api/v1/audit/orchestrate
Content-Type: application/json
x-api-key-google: {your_gemini_key}

{
  "target_domain": "example.com"
}
```

**Response** (truncated):
```json
{
  "run_id": "run_8f92bd3a",
  "overall_score": 78,
  "automated_findings": [...],
  "manual_review_wizard": {...},
  "scorecard": {...}
}
```

### Example 2: Rehydrate Full Audit State

```http
GET /api/v1/audit/runs/{run_id}/full
```

**Response**:
```json
{
  "run_metadata": {...},
  "completeness": 100,
  "wizard_cards": [...],
  "remediation_plan": {...},
  "synthesis_narrative": "..."
}
```

### Example 3: Submit Manual Observation

```http
POST /api/v1/audit/runs/{run_id}/observations
Content-Type: application/json
Authorization: Bearer {token}

{
  "question_id": "B2_CONTENT_ANSWERABILITY",
  "structured_data": {...},
  "severity": "warning",
  "diagnosis_text": "Lead paragraph uses vague hedging..."
}
```

### Example 4: Trigger Synthesis

```http
POST /api/v1/audit/runs/{run_id}/synthesize
x-api-key-google: {your_gemini_key}
```

**Response**:
```json
{
  "narrative": "...",
  "draft": "...",
  "flags": [...],
  "provider_log": [...]
}
```

### Example 5: Verify a BYOK Key

```http
POST /api/v1/byok/verify
x-api-key-google: {key_to_test}
```

**Response**:
```json
{
  "google": {
    "valid": true,
    "latency_ms": 142
  }
}
```

## 5. Rate Limiting

To maintain system stability and prevent abuse, compute-intensive endpoints implement a sliding window per-IP bucket rate limiting strategy. A memory-bounded eviction policy prevents DDoS memory exhaustion attacks that attempt to flood the rate limiter.

Current limits:
- `POST /api/v1/audit/orchestrate`: 3/min per IP
- `POST /api/v1/audit/runs/{run_id}/synthesize`: 3/min per IP  
- `GET /api/v1/audit/authority/{domain}`: 3/min per IP
- `POST /api/v1/byok/verify`: 15/min per IP

## 6. Idempotency

Write endpoints support idempotency to handle network instability and client retries gracefully.

- **Usage**: Clients should provide a unique UUID in the `Idempotency-Key` header.
- **Behavior**:
  - Duplicate requests with the same key will return the cached response without re-executing the operation.
  - Concurrent identical requests (where the initial request is still processing) will receive an `HTTP 409 Conflict`.
  - Failed requests automatically clean up their sentinel records, allowing the client to safely retry using the same idempotency key.

## 7. Error Format

All API errors return a standard JSON structure containing a machine-readable code, a UUID for correlation, and a human-readable detail message. The correlation ID (`error_id`) allows developers to match the error against server logs without exposing internal stack traces to the client.

```json
{
  "error_code": "ERROR_TYPE",
  "error_id": "8f92bd3a-1234-4567-8901-abcdef123456",
  "detail": "Human-readable message describing the error condition"
}
```

**Common Error Codes**:
- `INTERNAL_ERROR`: Unhandled exception during processing.
- `VALIDATION_ERROR`: Missing or malformed payload/parameters.
- `NOT_FOUND`: Requested resource (e.g., run_id, kid) does not exist.
- `UNAUTHORIZED`: Missing or invalid Bearer token.
- `SSRF_BLOCKED`: The requested domain violates internal Server-Side Request Forgery protections.
- `DOMAIN_UNRESOLVABLE`: The target domain could not be resolved via DNS.
