# AREOS Remediation Sequence — Agent Execution Protocol

Every finding in this document was verified directly against the codebase in
`AREOS_COMPLETE_WORKSPACE.zip` and, where relevant, against actual SQLite
runtime behavior reproduced in a sandbox — not against the (partially stale)
`internal.md`/`external.md` docs. Do not reintroduce anything this document
says was already fixed; do not skip a test because a task "looks small."

---

## Agent Protocol (read this before Task 0)

1. **One task at a time, in order.** Do not start task N+1 until task N's
   checkpoint has passed.
2. **Every task has a "Before" step and an "After" step.** Run the "Before"
   command first and record its output — this proves the bug/gap actually
   exists in the state you're starting from, and gives you something to diff
   against. If "Before" doesn't reproduce what the task describes, **stop and
   report back** — do not guess and proceed; the codebase may have moved.
3. **Every task has a Checkpoint.** A checkpoint is a concrete command
   (usually `pytest`) that must exit 0. If it doesn't:
   - Do not proceed to the next task.
   - Do not weaken the test to make it pass.
   - Fix the implementation, rerun, and only proceed once it's green.
4. **Never edit a file outside the "Files" list for a given task.** If you
   believe a fix requires touching something outside that list, stop and
   report why instead of expanding scope silently.
5. **After every task, run the Full Regression Gate** (defined once, below,
   reused at every checkpoint) in addition to the task-specific test — a
   task-specific test passing doesn't mean you didn't break something else.
6. **Commit after each passing checkpoint**, one commit per task, with the
   task number in the commit message (e.g. `T04: fix citation sampler engine
   loop`). This is what makes rollback of a single task possible if a later
   task reveals a problem.
7. **If a task's checkpoint cannot pass after two honest attempts, stop and
   report the exact failure output.** Do not move to the next task "to keep
   going" — later tasks assume earlier ones are actually fixed, not just
   attempted.

### Full Regression Gate (run at every checkpoint, no exceptions)

```bash
pytest tests/ -q
```

If this is slow, at minimum run:

```bash
pytest tests/ -q -k "ssrf or scoring or kb or claims or citation or verdict or schema"
```

...but the full suite must be run before the final task is marked done, even
if you used the filtered version at intermediate checkpoints.

---

## Phase 0 — Infrastructure decision (do this before any code task; it changes what "fixed" means)

### Task 0 — Confirm and correct the Render deployment plan

**Why first:** `render.yaml` already specifies `plan: starter` with a mounted
disk, with a comment warning that free-tier services have no persistent
disk. If the live deployment is actually on free tier, every task below that
touches `audit_runs`, `manual_verdicts`, `changelog`, or the KB tables is
being verified against a database that gets wiped on the next cold start —
you cannot trust any "it works" observation made against that environment.

**Before:** Check the actual Render dashboard (not the repo) for the live
service's plan. Report back: is it `starter` (with disk) or `free`?

**Action, if free tier is confirmed:**
Confirmed (2026-09-27): intentionally running on free tier / ephemeral SQLite as a cost decision. Revisit when moving to a paid plan. Do not treat this as an open gap in any future audit of this repo.
- Do not implement any Postgres migration, connection-pool changes, or dual-backend abstraction as part of this or any later task in the sequence.
- All local/CI verification in Tasks 1–13 below is unaffected either way, since it runs against a throwaway local SQLite file, not the Render disk.

**Checkpoint:** Resolved (2026-09-27): explicit user confirmation of free tier / ephemeral SQLite cost decision.

---

## Phase 1 — Fix the SSRF test-detection branch (everything downstream depends on trusting this path)

### Task 1 — Remove `is_mocked` branch in `areos/util/ssrf.py::safe_get()`

**Files:** `areos/util/ssrf.py`

**Before:**
```bash
grep -n "is_mocked" areos/util/ssrf.py
```
Confirm this prints the branch. If it doesn't, stop — this task is already done, report that instead of editing.

**Action:**
Remove:
```python
is_mocked = getattr(requests.get, "_mock_return_value", None) is not None or "Mock" in requests.get.__class__.__name__
if is_mocked:
    resp = requests.get(ip_url, ...)
else:
    resp = session.get(ip_url, ...)
```
Replace with a single unconditional call through `session.get(...)` (the
object carrying the `TargetIPAdapter` that pins the connection to the
validated IP). Do not delete `session`'s construction or the adapter
mounting — only the branch and the fallback to `requests.get`.

**Then:** `safe_get()` is called from 9 live locations — `research_service.py`
(x2), `cloaking_detector.py`, `authority_auditor.py`, `multipage_auditor.py`,
`audit_orchestrator.py` (x3), `sitemap_auditor.py` (x2), `competitor_analyzer.py`.
Grep each test file for `patch("requests.get"` or `mock.patch.object(requests`
and change the patch target to `requests.Session.get` (or
`areos.util.ssrf.session.get` if the session object is module-level) so the
tests exercise the real code path instead of the one you just deleted.

```bash
grep -rln 'patch("requests.get"\|patch(.requests\.get' tests/
```

Update every file that grep returns.

**Checkpoint:**
```bash
pytest tests/test_qa2_phase_r1.py tests/test_ssrf_byok_llm_endpoints.py -q
pytest tests/ -q
```
Both must be green. If any test that used to pass now fails, that test was
never actually exercising the SSRF-hardened path — fix the test's mock
target, do not restore the `is_mocked` branch.

---

### Task 2 — Add missing SSRF edge-case tests (now that the tests exercise the real path)

**Files:** `tests/test_qa2_phase_r1.py`

**Before:**
```bash
grep -n "0177\|0x7f\|::1\|ffff:127" tests/test_qa2_phase_r1.py
```
Confirm this returns nothing (the edge cases are genuinely absent).

**Action:** Add test cases to `TestR1SSRFAndSecurity` (or a new test class in
the same file) asserting `ValueError` is raised for:
- Octal-encoded loopback: `0177.0.0.1`
- Hex-encoded loopback: `0x7f.0.0.1` and `0x7f000001`
- IPv6 loopback: `::1`
- IPv6-mapped IPv4 private address: `::ffff:127.0.0.1`
- A redirect chain: first hop resolves to a public IP, second hop (via
  mocked `Location` header) resolves to a private IP — assert `safe_get()`
  raises before following the second hop, not after.

If any of these fail against the current `_validate_ip()`/
`resolve_and_validate()` logic, **fix that logic** (Python's `ipaddress`
module does not normalize octal/hex octets the way some HTTP stacks do — you
may need explicit string normalization before passing to `ipaddress`). Do
not weaken the new tests to match current behavior; the whole point of this
task is to make the validator actually reject these.

**Checkpoint:**
```bash
pytest tests/test_qa2_phase_r1.py -q -v
pytest tests/ -q
```

---

## Phase 2 — Fix the two live, user-facing correctness bugs

### Task 3 — Fix the citation sampler's silent Perplexity-only collapse

**Files:** `areos/auditors/audit_orchestrator.py`, `areos/auditors/citation_sampler.py`

**Before:**
```bash
sed -n '580,600p' areos/auditors/audit_orchestrator.py
grep -n "engine" areos/auditors/audit_orchestrator.py
```
Confirm: the call to `sample_citations(...)` passes `prompt_set=prompts[:2],
n_runs=1` and no `engine=` argument (so it defaults to `"perplexity"` only),
and confirm there is no other call site in this file that ever passes
`engine="gemini"`.

**Action:**
1. At the top of `audit_orchestrator.py`, add named constants:
   ```python
   CITATION_SAMPLE_PROMPT_COUNT = 2
   CITATION_SAMPLE_ENGINES = ["perplexity", "gemini"]
   ```
2. Replace the single `sample_citations(...)` call with a loop over
   `CITATION_SAMPLE_ENGINES`, calling `sample_citations()` once per engine
   **only if that engine's key is present** in `client_keys` (check exactly
   how `client_keys` is populated upstream — likely
   `client_keys.get("perplexity")` / `client_keys.get("google")` — match
   whatever key names `sample_citations()` already expects internally for
   each engine; do not invent new key names).
3. Merge the resulting `CitationSampleResult` objects (combine `observations`
   lists; the merged object's engine list should reflect only engines that
   were actually queried).
4. In `citation_sampler.py`, make `TOS_CAVEAT` a function of which engines
   were actually run in that specific call, not a static string listing both
   providers unconditionally. Every caller of `TOS_CAVEAT` needs to be
   updated to pass the actual engine list used.
5. Use `CITATION_SAMPLE_PROMPT_COUNT` instead of the bare `[:2]` slice.

**Checkpoint:**
Add/update a test asserting: (a) when both provider keys are present in
`client_keys`, both engines are queried (mock both HTTP calls, assert both
were invoked); (b) when only one key is present, only that engine is
queried and the caveat text names only that engine; (c) when neither key is
present, the function returns a result whose caveat clearly states no live
sampling occurred (do not let it silently return an empty-but-unlabeled
result).

```bash
pytest tests/ -q -k citation
pytest tests/ -q
```

---

### Task 4 — Fix the silently-broken Citation Transparency feature (`claim_sources` → `kb_evidence`/`kb_sources`)

**Files:** `areos/services/report_generator.py`, `areos/services/sources.py`

**Before:**
```bash
grep -n "claim_sources" areos/services/report_generator.py areos/services/sources.py
grep -rn "INSERT INTO claim_sources" areos/ --include="*.py"
```
Confirm the first command finds read queries against `claim_sources` in both
files, and the second command returns **nothing** — proving this table is
read from but never written to, which is why this feature currently returns
empty source lists for every claim in every generated report. This is a live
bug independent of anything else in this document; it exists right now.

**Action:** Rewrite both queries to read from `kb_evidence` joined with
`kb_sources`, using the exact working pattern already implemented in
`areos/api/routers/knowledge.py` (lines ~194–240) as your reference:
```python
ev_rows = conn.execute("SELECT * FROM kb_evidence WHERE kid = ?", (kid,)).fetchall()
# then join sid values against kb_sources
```
Map the old output shape (`source_id, name, url, trust_tier, primary_source,
note`) onto the new columns (`sid, url, title, publisher, authority,
pub_date, excerpt, notes`) — check every downstream consumer of
`get_ranked_sources()` / the report generator's source list (grep both
function names) to confirm no caller depends on a column name that no longer
exists, and update those callers' field access if needed.

**Checkpoint:** Add a test that: seeds a `knowledge` row + a `kb_sources` row
+ a `kb_evidence` row linking them, calls the report generator (or the
`sources.py` function directly) for that claim, and asserts the returned
source list is **non-empty** and contains the seeded source's URL. This is
the regression test that would have caught this bug in the first place —
do not skip it even though it feels like "just a query rewrite."

```bash
pytest tests/ -q -k "source or report"
pytest tests/ -q
```

---

### Task 5 — Add authentication/ownership to the manual-verdicts endpoint

**Files:** `areos/api/routers/verdicts.py`, `areos/api/routers/audit.py` (only the run-creation function, to add a token), wherever `audit_runs` rows are created

**Before:**
```bash
grep -n "verify_admin\|rate_limit" areos/api/routers/verdicts.py
```
Confirm neither appears — this endpoint currently has zero protection.

**Action:** Check how the frontend/UI currently obtains and stores a
`run_id` after creating a run (grep the static JS under wherever the UI
lives, e.g. `search for "runs/" fetch calls` or similar, to see whether a
token is already returned and just unused). Then:
- Add a `run_token` column to `audit_runs` (via the schema task in Phase 3 —
  if Phase 3 hasn't run yet, add it here as a small additive migration and
  flag it for consolidation later, don't block this fix on schema cleanup).
- Generate a random token (e.g. `secrets.token_urlsafe(24)`) when a run is
  created, return it alongside `run_id` in the creation response.
- Require that same token (compared via `hmac.compare_digest`, not `==`) as
  a header or query parameter on `POST /audit/runs/{run_id}/verdicts` before
  accepting the verdict.
- If the frontend has no notion of a token today, this is a breaking API
  change for the UI — update the UI's verdict-submission call to send the
  token it received at run-creation time, in the same commit.

**Checkpoint:** Add a negative test: submitting a verdict with a missing or
wrong token returns 401/403 and does not write a row. Add a positive test:
submitting with the correct token succeeds.
```bash
pytest tests/ -q -k verdict
pytest tests/ -q
```

---

## Phase 3 — Consolidate to one knowledge base structure (do only after Phase 1 and 2 are green — this phase touches schema, and you want a trusted test suite underneath it)

### Task 6 — Prove the FK-rewrite side effect before touching schema.sql (grounding step, not a fix)

**Files:** none changed — this is a verification-only task, to make the next
task's "before" state undeniable rather than asserted.

**Action:** Run this exact script against a scratch copy of the repo's
`areos.db` (copy it first, don't touch the real file):
```bash
cp areos.db /tmp/areos_scratch.db
python3 -c "
import sqlite3
conn = sqlite3.connect('/tmp/areos_scratch.db')
for name in ['tool_landscape','policy_constraints','findings','claim_sources','check_code_mappings']:
    row = conn.execute(f\"SELECT sql FROM sqlite_master WHERE name='{name}'\").fetchone()
    print(name, '->', row[0] if row else 'NOT FOUND')
"
```
Report the output. This shows you, concretely, which of these five tables'
`REFERENCES` clauses currently point at `claims_legacy` instead of `claims`
in the actual shipped database — this is your ground truth for what Task 7
needs to fix, not a guess.

**Checkpoint:** None (informational task) — but do not proceed to Task 7
until you have actually run this and read the output.

---

### Task 7 — Remove the legacy `claims` table definition from `schema.sql`; drop the four dead FK-dependent tables

**Files:** `areos/db/schema.sql`

**Before:** Confirm via Task 6's output which tables currently exist with a
stale FK. Also confirm dead-write status one more time:
```bash
grep -rn "INSERT INTO findings\|INSERT INTO tool_landscape\|INSERT INTO policy_constraints\|INSERT INTO check_code_mappings" . --include="*.py"
```
Must return nothing. (`claim_sources` was already handled in Task 4 — after
that task, its reads point at `kb_evidence`/`kb_sources`, so it too is now
safe to remove here.)

**Action:**
1. Delete the `CREATE TABLE IF NOT EXISTS claims (...)` block from
   `schema.sql`, including its indexes and triggers.
2. Delete the `CREATE TABLE IF NOT EXISTS tool_landscape`,
   `policy_constraints`, `findings`, `claim_sources`, and
   `check_code_mappings` blocks entirely (confirmed dead in Task 6/above and
   in Task 4's grep). If any of these turns out to have a live reader you
   didn't find, **stop and report it** rather than deleting — re-run the
   grep from Task 6 with broader patterns first.
3. Leave `audit_runs`, `manual_verdicts`, `manual_observations`,
   `audit_synthesis`, `changelog`, `sources`, `jobs`, `idempotency_keys`,
   `prompt_sets`, `synthesis_prompts` untouched — these are real, live,
   written-to operational tables.
4. In `areos/db/migrate_audit_tables.py`, remove the entire `is_claims_view`
   detection block and the regex-stripping of `REFERENCES claims(...)` —
   there is no longer a competing table definition for it to collide with,
   so this defensive code is no longer needed. Confirm this by re-reading
   the function after your edit: it should just execute `schema.sql`
   directly with no special-casing.
5. Delete `areos/db/schema/artifacts.py` — confirmed dead code (nothing
   imports it; verify again with
   `grep -rln "schema.artifacts\|from areos.db.schema import artifacts" --include="*.py" .`
   before deleting).
6. In `migrate_audit_tables.py`'s header comment and `areos/db/lint.py`'s
   comment, remove references to `generate_schema.py` / `generate_ddl.py` /
   `mixins.py` — none of these exist. Replace with an honest comment: this
   file is hand-maintained; see Task 9 for the parity check that keeps it
   honest.

**Checkpoint:**
```bash
rm -f /tmp/fresh_test.db
python3 -c "
from areos.db.connection import get_connection
from areos.db.migrate_audit_tables import migrate
from areos.kb import build_kb
migrate('/tmp/fresh_test.db')
build_kb.build('/tmp/fresh_test.db')
print('fresh boot sequence completed without error')
"
pytest tests/ -q
```
Both must succeed. Additionally, run the exact reproduction from Task 6
again against `/tmp/fresh_test.db` — this time all five old FK targets
should report `NOT FOUND` (the tables no longer exist), and `claims` should
be a view, not a table.

---

### Task 8 — Decide the fate of the existing `claims_legacy` data, once, explicitly

**Files:** a one-off migration script under `scripts/` (name it
`archive_claims_legacy.py`), not `build_kb.py` itself

**Before:** Confirm the current production/shipped `areos.db` still has a
`claims_legacy` table with data (`SELECT COUNT(*) FROM claims_legacy`).

**Action:** Since `handle_claims_view()` will never again encounter a real
`claims` table to rename (Task 7 removed the only thing that created one),
this table will no longer be recreated or overwritten going forward — treat
whatever's in it right now as a permanent historical snapshot:
1. Rename it once, by hand, to `claims_v1_archive` (a name that doesn't
   imply it's still "the legacy path," just history).
2. Add a one-line comment/README entry stating what it is and the date this
   decision was made.
3. Remove the now-dead rename-on-detection branch in
   `handle_claims_view()` for the `row['type'] == 'table'` case (Task 7 means
   this branch can now never trigger) — keep only the `view` branch that
   drops and recreates the view. Leave a comment explaining why the table
   branch was removed, citing this task, so a future reader doesn't
   reintroduce it "just in case."

**Checkpoint:**
```bash
pytest tests/test_kb_build_schema_integrity.py tests/test_kb_parity.py tests/test_kb_parity_gate.py -q
pytest tests/ -q
```

---

### Task 9 — Add a schema-drift CI guard (prevents this whole situation from recurring)

**Files:** new file `tests/test_schema_matches_live_db.py`

**Action:** Write a test that:
1. Builds a fresh DB in a temp file via `migrate()` + `build_kb.build()`
   (same sequence as Task 7's checkpoint).
2. Dumps `SELECT name FROM sqlite_master WHERE type IN ('table','view')`
   from that fresh DB.
3. Asserts this set exactly matches an explicit, hand-maintained allowlist
   in the test file itself (list every table/view you expect: the
   operational tables from `schema.sql` plus `knowledge`, `kb_sources`,
   `kb_evidence`, `kb_check_code_map`, `kb_embeddings`, `kb_meta`,
   `kb_metrics`, `claims` view, `claims_v1_archive`).
4. If a future change adds/removes a table without updating this test, the
   test fails loudly instead of the drift being discovered by someone
   confused six months from now (as happened here).

**Checkpoint:**
```bash
pytest tests/test_schema_matches_live_db.py -q
pytest tests/ -q
```

---

## Phase 4 — Documentation and drift-prevention (small, independent, no code risk — do these in any order once Phase 3 is green)

### Task 10 — Regenerate `external.md`'s deduction table and access-gate table from live code

**Files:** new script `scripts/generate_scoring_docs.py`, `docs/external.md`

**Before:**
```bash
python3 -c "from areos.auditors.scoring import LAYER_DEDUCTIONS, ACCESS_GATE; print(len(LAYER_DEDUCTIONS), len(ACCESS_GATE))"
```
Compare this count against how many rows `external.md` §5.3/§5.4 currently
document by hand — confirm a mismatch before editing anything (this proves
the doc is stale, rather than assuming it).

**Action:** Write the generator script, run it, replace the hand-written
tables in `external.md` with its output, including the two access-gate
triggers currently undocumented there (`CLOAKING_DETECTED` → 35 cap,
`META_NOINDEX` → 15 cap).

**Checkpoint:** Re-run the generator a second time immediately after and
diff its output against what you just committed — it must be byte-identical
(proves the generator is deterministic and the doc actually reflects it, not
a one-time manual copy-paste that will drift again next week).

---

### Task 11 — Recount and correct the endpoint/auth inventory in `internal.md`

**Files:** script `scripts/list_endpoint_auth.py`, `docs/internal.md`

**Action:** Introspect `app.routes` (or grep every `@router.get/post/put/delete`
across `areos/api/routers/*.py` plus `main.py`) and list each endpoint with
whether `verify_admin` is in its dependencies. Replace the hand-counted
"24 endpoints, 14 unauthenticated" figure in `internal.md` §07 with this
script's live output.

**Checkpoint:** Script runs without error; row count in the regenerated
table matches `grep -c "@router\.\(get\|post\|put\|delete\)" areos/api/routers/*.py main.py`'s
total.

---

### Task 12 — Delete the self-contradicting QA-gate bypass claim in `internal.md`

**Files:** `docs/internal.md`

**Action:** Delete the §7.4 bullet claiming `qa_gate.py` L71–83 still
contains a C052–C090 bypass. Confirmed false: the only exemption in the live
file is `if rec.source == "manual"`, a legitimate, intentional design
decision, and the file's own comment states the pattern-based bypass was
already removed. §5.8 of the same document already correctly says this was
resolved — leave that sentence as-is.

**Checkpoint:** None (doc-only, no test to run) — but re-read `qa_gate.py`
one more time after editing to confirm you deleted the correct, false bullet
and not the correct one.

---

### Task 13 — Note the CORS design intent in `internal.md`

**Files:** `docs/internal.md`

**Action:** Add a short paragraph to §09 (Security) reproducing the reasoning
already present as a code comment above `CORSMiddleware` in `main.py`: the
allowlist is a local-dev convenience with no production security role, since
the UI is served same-origin.

**Checkpoint:** None (doc-only).

---

## Final Gate — run once, after every task above is committed

```bash
rm -f /tmp/final_fresh.db
python3 -c "
from areos.db.migrate_audit_tables import migrate
from areos.kb import build_kb
migrate('/tmp/final_fresh.db')
build_kb.build('/tmp/final_fresh.db')
print('OK: fresh-disk boot sequence works end to end')
"
pytest tests/ -q
```

Do not consider this remediation complete until both commands above succeed
against a **freshly created** database file, not the existing `areos.db` —
the whole point of this exercise was that fresh-disk behavior (which is what
Render's ephemeral filesystem produces on every restart) is the behavior
that actually matters.
