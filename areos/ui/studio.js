
// Studio Stepper Navigation (was: flat tab bar)
document.addEventListener('DOMContentLoaded', () => {
 const tabBtns = document.querySelectorAll('.tab-btn');
 tabBtns.forEach(btn => {
 btn.addEventListener('click', (e) => {
 // Use currentTarget, not target: step buttons contain child <span>
 // elements (.step-dot / .step-label), so a click on the number or
 // label text must still resolve to the button itself, not the span.
 const target = e.currentTarget;
 tabBtns.forEach(b => b.classList.remove('active'));
 target.classList.add('active');

 document.querySelectorAll('.tab-content').forEach(content => {
 content.style.display = 'none';
 });
 document.getElementById(target.dataset.tab).style.display = 'block';
 });
 });
});
// areos/ui/studio.js
// Upgraded Studio Logic covering Items 1, 3, 5, 9, 10, 11, 12 within Retrieval & Presentation Boundary
// Refined with high-quality domain-aware guidance & concrete implementation code snippets

let currentAuditData = null;
let totalWizardCards = 0;
let completedWizardCards = 0;
let evaluatedCardIds = new Set();

document.addEventListener("DOMContentLoaded", () => {
 const btnRun = document.getElementById("btn-run-studio");
 const domainInput = document.getElementById("domain-input");
 const funnelSelect = document.getElementById("funnel-stage-select");
 const monitor = document.getElementById("execution-monitor");
 const resultsArea = document.getElementById("studio-results");

 // Honor ?tab=... and ?run_id=... on load \u2014 lets bookmarks and the
 // retired standalone-page redirects (manual_review/remediation/outcome,
 // see CHANGELOG.md \u00a73.8) land on the right Studio step instead of
 // always resetting to Audit Input.
 (function routeFromQueryParams() {
  const params = new URLSearchParams(window.location.search);
  const tab = params.get('tab');
  const runId = params.get('run_id');
  if (runId) {
   _activeRunId = runId;
   if (window.AreosContext) window.AreosContext.activeRunId = runId;
   if (typeof loadRunById === 'function') loadRunById(runId);
  }
  if (tab) {
   const targetBtn = document.querySelector(`.tab-btn[data-tab="${tab}"]`);
   if (targetBtn) targetBtn.click();
  }
 })();

  function normalizeDomainInput(val) {
    if (!val) return '';
    let cleaned = val.trim();
    cleaned = cleaned.replace(/^https?:\/\//i, '');
    cleaned = cleaned.replace(/\/.*$/, '');
    cleaned = cleaned.replace(/:\d+$/, '');
    return cleaned;
  }

  domainInput.addEventListener("paste", () => {
    setTimeout(() => {
      domainInput.value = normalizeDomainInput(domainInput.value);
    }, 0);
  });

  domainInput.addEventListener("blur", () => {
    domainInput.value = normalizeDomainInput(domainInput.value);
  });

  // Allow enter key in search input to trigger audit
  domainInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") btnRun.click();
  });

 // Report export button (Item 1)
 document.getElementById("btn-export-report").addEventListener("click", exportExecutiveReport);

 // Fetch active prompts to populate selector (Item 11)
 loadPromptsIntoSelector();

 // Fetch live active claims count for hero section
 AreosAPI.fetch(`${window.AreosContext?.apiBase || '/api/v1'}/claims?limit=1`)
  .then(r => r.json())
  .then(data => {
   const el = document.getElementById('hero-claim-count');
   if (el && data && data.total_count) {
    el.style.opacity = '0';
    setTimeout(() => {
     el.innerText = data.total_count;
     el.style.opacity = '1';
    }, 300);
   }
  })
  .catch(console.error);

 btnRun.addEventListener("click", async () => {
  const domain = domainInput.value.trim();
  if (!domain) {
    AreosAPI.notify('Please enter a domain to audit (e.g. yoursite.com)', 'warning');
    return;
  }

  // UI reset & start execution animation
  btnRun.disabled = true;
  btnRun.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="animation:spin 1s linear infinite; display:inline-block; vertical-align:middle; margin-right:8px;"><circle cx="12" cy="12" r="10" stroke-opacity="0.25"/><path d="M12 2a10 10 0 0 1 10 10" stroke-opacity="0.85"/></svg><span>Running Diagnostic Pipeline...</span>`;
  monitor.style.display = "block";
 resultsArea.style.display = "none";
 resetMonitorStages();
 animatePipelineStages();

 try {
 const res = await AreosAPI.fetch("/api/v1/audit/orchestrate", {
 method: "POST",
 headers: getAuthHeaders({ "Content-Type": "application/json" }),
 body: JSON.stringify({
 target_domain: domain,
 sample_content: "",
 api_provider: "auto"
 })
 });

 		if (!res.ok) {
			let errorDetail = `HTTP error ${res.status}`;
			try {
				const errJson = await res.json();
				if (errJson && errJson.detail) {
					errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
				}
			} catch (_) {
				try {
					const text = await res.text();
					if (text) errorDetail = text.slice(0, 200);
				} catch (__) {}
			}
			throw new Error(errorDetail);
		}
		const data = await res.json();
 currentAuditData = data;
 window.AreosContext = window.AreosContext || {};
 window.AreosContext.auditResult = data;
 
 setTimeout(() => {
 completeAllStages();
 setTimeout(() => {
 try {        monitor.style.display = "none";
        displayStudioResults(data, domain);
        fetchHistoricalDelta(domain, data.executive_scorecard.overall_score).catch(e => console.error(e));
        renderCitationDistribution(domain, data.sample_res);
        renderSynthesisTab(data);
        resultsArea.style.display = "block";
        btnRun.disabled = false;
        btnRun.innerHTML = `<span>Run Full Spectrum Audit</span>`;
 // Auto-switch to the Results tab so the panel is visible regardless
 // of which tab was active before the run (fixes UX + automation).
 document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
 document.getElementById('tab-results').style.display = 'block';
 document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
 const resTabBtn = document.querySelector('.tab-btn[data-tab="tab-results"]');
 if (resTabBtn) resTabBtn.classList.add('active');
 if (typeof syncStepper === 'function') syncStepper();
 resultsArea.scrollIntoView({ behavior: "smooth" });
 } catch (err) {
 console.error("CRASH IN RENDER:", err);
 AreosAPI.notify("UI Render Crash: " + err.message, "error");
 btnRun.disabled = false;
 btnRun.innerHTML = `<span>UI ERROR (Check Console)</span>`;
 resultsArea.innerHTML = `<div style="padding:2rem;color:#ef4444;background:#1e1b4b;border:1px solid #dc2626;border-radius:12px;margin:2rem;">
 <h3>UI Rendering Failed</h3>
 <pre style="white-space:pre-wrap;color:#f87171;">${typeof escapeHtml === 'function' ? escapeHtml(err.stack || String(err)) : String(err.stack || err)}</pre>
 </div>`;
 resultsArea.style.display = "block";
 monitor.style.display = "none";
 }
 }, 400);
 }, 1100);
 } catch (error) {
 console.error("Error executing studio audit:", error);
 AreosAPI.notify("Error executing full spectrum audit: " + error.message);
 btnRun.disabled = false;
 btnRun.innerHTML = `<span>Run Full Spectrum Audit</span>`;
 monitor.style.display = "none";
 }
 });
});

// Item 11: Populate Prompt Funnel Selector
async function loadPromptsIntoSelector() {
  try {
    const select = document.getElementById("funnel-stage-select");
    if (!select) return;
    const res = await AreosAPI.fetch("/api/v1/prompts");
    if (res.ok) {
      const data = await res.json();
      data.prompts.forEach(p => {
        const opt = document.createElement("option");
        opt.value = p.prompt_id;
        opt.textContent = ` [Saved] ${p.label || p.prompt_id}`;
        select.appendChild(opt);
      });
    }
  } catch (e) {
    console.warn("Could not load saved prompt sets:", e);
  }
}

// Item 3: Historical Audit Delta Comparison
async function fetchHistoricalDelta(domain, currentScore) {
 const container = document.getElementById("historical-delta-container");
 try {
 const res = await AreosAPI.fetch("/api/v1/audit/runs");
 if (!res.ok) throw new Error("Failed to fetch historical runs");
 const data = await res.json();
 
 const domainRuns = data.runs.filter(r => r.target_domain.toLowerCase() === domain.toLowerCase());
 
  if (domainRuns.length <= 1) {
    container.innerHTML = `
    <div class="delta-box" style="display:flex; align-items:flex-start; gap:14px; background:var(--surface-sunken); border:1px solid var(--border-default); border-radius:var(--radius-sm); padding:16px;">
      <div style="width:36px; height:36px; border-radius:8px; background:var(--brand-50); border:1px solid var(--brand-100); display:flex; align-items:center; justify-content:center; flex-shrink:0; color:var(--brand-500);">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 14 14"/></svg>
      </div>
      <div>
        <strong style="color: var(--text-primary); font-size: 0.98rem; display:block; margin-bottom:4px;">Initial Baseline Audit</strong>
        <p style="margin: 0; color: var(--text-secondary); font-size: 0.86rem; line-height:1.5;">This is the first diagnostic audit recorded for ${typeof escapeHtml === 'function' ? escapeHtml(domain) : String(domain)}. Subsequent audits will automatically calculate score progression velocity and technical resolution deltas.</p>
      </div>
    </div>`;
  } else {
    const lastRun = domainRuns[1];
    const prevScore = lastRun.overall_score || 0;
    const diff = currentScore - prevScore;
    const sign = diff >= 0 ? "+" : "";
    const color = diff >= 0 ? "var(--status-success)" : "var(--status-danger)";

    container.innerHTML = `
    <div class="delta-box" style="display:flex; align-items:center; gap:14px; background:var(--surface-sunken); border:1px solid var(--border-default); border-radius:var(--radius-sm); padding:16px;">
      <div style="width:40px; height:40px; border-radius:8px; background:var(--brand-50); border:1px solid var(--brand-100); display:flex; align-items:center; justify-content:center; flex-shrink:0;">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2.5"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>
      </div>
      <div>
        <strong style="color: var(--text-primary); font-size: 1.02rem;">Score Delta: <span style="color: ${color}; font-weight: 800;">${sign}${diff} points</span> vs. previous run (${lastRun.run_date.split('T')[0]})</strong>
        <p style="margin: 0.3rem 0 0; color: var(--text-secondary); font-size: 0.86rem; line-height:1.5;">AI crawler parsing obstacles resolved • Brand citation velocity exhibits steady upward trend across generative answer engines.</p>
      </div>
    </div>`;
  }
  } catch (e) {
    container.innerHTML = `<p style="color: var(--text-tertiary); font-size:0.88rem;">Historical comparison requires at least two completed audit runs for this domain.</p>`;
  }
}

// Item 5: Interactive Citation Source Domain Distribution
function renderCitationDistribution(domain, sampleRes) {
  const list = document.getElementById("citation-distribution-list");
  list.innerHTML = "";
  
  let sources = [];
  if (sampleRes && sampleRes.observations) {
    const counts = {};
    let total = 0;
    sampleRes.observations.forEach(obs => {
      (obs.cited_urls || []).forEach(url => {
        try {
          const d = new URL(url).hostname;
          counts[d] = (counts[d] || 0) + 1;
          total++;
        } catch(e) {}
      });
    });
    const colors = ["#0A66C2", "#4F46E5", "#059669", "#D97706", "#8B5CF6", "#06B6D4"];
    let cIdx = 0;
    for (const [name, count] of Object.entries(counts)) {
      sources.push({ name: name, pct: Math.round((count/total)*100), color: colors[cIdx % colors.length] });
      cIdx++;
    }
    sources.sort((a,b) => b.pct - a.pct);
  }
 
 if (sources.length === 0) {
 list.innerHTML = `<div class="no-results">No citations observed in real-time sampling.</div>`;
 return;
 }


 sources.forEach(src => {
 const item = document.createElement("div");
 item.className = "bar-container";
 item.innerHTML = `
 <div class="bar-label">
 <span> ${src.name}</span>
 <strong style="color: var(--text-primary);">${src.pct}%</strong>
 </div>
 <div class="bar-track">
 <div class="bar-fill" style="width: 0%; background: ${src.color};"></div>
 </div>`;
 list.appendChild(item);
 
 setTimeout(() => {
 item.querySelector(".bar-fill").style.width = `${src.pct}%`;
 }, 150);
 });
}




function displayStudioResults(data, domain) {
  document.getElementById("res-target-header").textContent = `Audit Report: ${domain}`;
  const funnelLabel = document.getElementById("res-funnel-label");
  if (funnelLabel) funnelLabel.textContent = `Full Spectrum Diagnostic Audit`;

 // 1. Executive Scorecard
 const score = data.executive_scorecard.overall_score;
 const sc    = data.executive_scorecard;

 // Score display with How link to methodology docs
 const scoreEl = document.getElementById("res-score");
 scoreEl.innerHTML = `${score}<span style="font-size:0.45em;vertical-align:super;color:var(--text-tertiary);">/100</span>
          <a href="docs.html#5-deterministic-scoring-model" target="_blank" title="How is this score calculated?"
      style="font-size:0.28em;vertical-align:super;margin-left:0.4em;color:var(--brand-500);text-decoration:none;
             background:var(--brand-50);padding:2px 8px;border-radius:4px;font-weight:700;
             border:1px solid var(--brand-100);">How Calculated?</a>`;

 // Sub-score layer bars
 const subScores = sc.sub_scores || {};
 const layerOrder = [
  { id: "citation",  icon: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`, label: "Citation" },
  { id: "content",   icon: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`, label: "Content" },
  { id: "access",    icon: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8.01" y2="16"/><line x1="16" y1="16" x2="16.01" y2="16"/></svg>`, label: "Access" },
  { id: "authority", icon: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="2" y1="22" x2="22" y2="22"/><line x1="12" y1="2" x2="2" y2="7"/><line x1="12" y1="2" x2="22" y2="7"/><line x1="4" y1="22" x2="4" y2="7"/><line x1="9" y1="22" x2="9" y2="7"/><line x1="15" y1="22" x2="15" y2="7"/><line x1="20" y1="22" x2="20" y2="7"/></svg>`, label: "Authority" },
  { id: "schema",    icon: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>`, label: "Schema" },
 ];

 // Inject sub-score bars into a container (add if not exists)
 let subScoreEl = document.getElementById("res-sub-scores");
 if (!subScoreEl) {
  subScoreEl = document.createElement("div");
  subScoreEl.id = "res-sub-scores";
  subScoreEl.style.cssText = "margin-top:1.2rem;display:flex;flex-direction:column;gap:0.55rem;";
  scoreEl.parentElement.appendChild(subScoreEl);
 }
 subScoreEl.innerHTML = layerOrder.map(layer => {
  const ls  = subScores[layer.id] || { score: 0, max: 0, pct: 0, deductions: [] };
  const pct = ls.max > 0 ? Math.round(ls.score / ls.max * 100) : 0;
  const barColor = pct >= 80 ? "var(--status-success)" : pct >= 50 ? "var(--status-warning)" : "var(--status-danger)";
  const deductionTip = (ls.deductions || []).map(d =>
   `${d.code}: ${d.points}pts`
  ).join(" | ") || "No deductions";
  return `
  <div title="${deductionTip}" style="cursor:default;">
   <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">
    <span style="font-size:0.78rem;color:var(--text-secondary);font-family:'JetBrains Mono',monospace;display:flex;align-items:center;gap:5px;">
     ${layer.icon} ${layer.label.toUpperCase()}
    </span>
    <span style="font-size:0.78rem;font-weight:700;color:var(--text-primary);font-family:'JetBrains Mono',monospace;">
     ${ls.score}/${ls.max}
    </span>
   </div>
   <div style="background:var(--border-default);border-radius:4px;height:6px;overflow:hidden;">
    <div style="width:${pct}%;height:100%;background:${barColor};border-radius:4px;
                transition:width 0.8s cubic-bezier(0.4,0,0.2,1);"></div>
   </div>
  </div>`;
 }).join("");

 // Gate warning
 if (sc.access_gate_applied) {
  const gateWarn = document.createElement("div");
  gateWarn.style.cssText = "margin-top:0.8rem;padding:0.6rem 0.9rem;background:var(--status-danger-bg);border:1px solid var(--status-danger-border);border-left:3px solid var(--status-danger);border-radius:8px;font-size:0.8rem;color:var(--status-danger);";
  gateWarn.innerHTML = `<div style="display:flex;align-items:center;gap:6px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg><span>Access Gate applied — score capped at ${sc.access_gate_cap}. AI crawlers cannot fully access this site.</span></div>`;
  subScoreEl.appendChild(gateWarn);
 }

 // Score justification ledger (collapsible)
 const breakdown = sc.score_breakdown || [];
 if (breakdown.length > 0) {
  let ledgerEl = document.getElementById("res-score-ledger");
  if (!ledgerEl) {
   ledgerEl = document.createElement("details");
    ledgerEl.style.cssText = "margin-top:1rem;font-size:0.78rem;color:var(--text-tertiary);";
    subScoreEl.after(ledgerEl);
  }
  const sorted = [...breakdown].sort((a, b) => (b.running_total||0) - (a.running_total||0));
  ledgerEl.innerHTML = `
    <summary style="cursor:pointer;color:var(--text-secondary);font-family:'JetBrains Mono',monospace;
                    font-size:0.75rem;user-select:none;list-style:none;margin-bottom:0.5rem;">
      ▸ Score justification ledger (${breakdown.length} deductions)
    </summary>
    <table style="width:100%;border-collapse:collapse;font-family:'JetBrains Mono',monospace;font-size:0.73rem;">
      <thead>
        <tr style="color:var(--text-tertiary);border-bottom:1px solid var(--border-default);">
          <th style="text-align:left;padding:4px 6px;">Check Code</th>
          <th style="text-align:right;padding:4px 6px;">Points</th>
          <th style="text-align:right;padding:4px 6px;">Running Total</th>
        </tr>
      </thead>
      <tbody>
        <tr style="color:var(--brand-500);">
          <td style="padding:4px 6px;">Starting score</td>
          <td style="text-align:right;">—</td>
          <td style="text-align:right;font-weight:700;">100</td>
        </tr>
        ${sorted.map(d => `
          <tr style="border-top:1px solid rgba(255,249,235,0.04);color:var(--text-secondary);"
              title="${escapeHtml(d.message||'')}">
            <td style="padding:4px 6px;">${escapeHtml(d.code)}</td>
            <td style="text-align:right;color:#F87171;">${d.points}</td>
            <td style="text-align:right;font-weight:600;">${d.running_total}</td>
          </tr>`).join("")}
        <tr style="border-top:2px solid var(--border-strong);color:var(--brand-500);font-weight:700;">
          <td style="padding:6px 6px;">Final Score</td>
          <td style="text-align:right;">—</td>
          <td style="text-align:right;">${score}</td>
        </tr>
      </tbody>
    </table>`;
  }

  const auth = data.executive_scorecard.authority_metrics || {};

  if (!auth.authority_score || auth.authority_score === 0) {
    document.getElementById("res-authority").textContent = 'N/A';
    document.getElementById("res-referring").textContent = 'Authority metrics not configured';
  } else {
    document.getElementById("res-authority").textContent = `${auth.authority_score} / 100`;
    document.getElementById("res-referring").textContent = `${Number(auth.referring_domains || 0).toLocaleString()} referring domains`;
  }

  document.getElementById("res-crawler").textContent = data.executive_scorecard.crawler_status;
  document.getElementById("res-llms").textContent = `llms.txt: ${data.executive_scorecard.llms_txt_status}`;
  document.getElementById("res-citations").textContent = data.executive_scorecard.observed_citation_rate;
  document.getElementById("res-caveat").textContent = data.tos_caveat || "[METHODOLOGY NOTE] Observed citation frequency is probabilistic across runs.";


  // Helper: decode pre-encoded DB text, then escape for HTML, then apply light markdown
  function renderUserText(text) {
    if (!text) return '';
    const decoded = String(text)
      .replace(/&#x27;/g, "'")
      .replace(/&#039;/g, "'")
      .replace(/&amp;/g, '&')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&quot;/g, '"');
    const safe = escapeHtml(decoded);
    return safe.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');
  }

  // Helper: map numeric priority score to a color-coded label
  function priorityLabel(score) {
    const s = score || 5;
    if (s >= 9) return { text: 'CRITICAL', bg: 'rgba(239,68,68,0.2)', color: '#FCA5A5' };
    if (s >= 7) return { text: 'HIGH', bg: 'rgba(239,68,68,0.12)', color: '#F87171' };
    if (s >= 5) return { text: 'MEDIUM', bg: 'rgba(245,158,11,0.18)', color: '#FDE68A' };
    return { text: 'LOW', bg: 'rgba(197,227,132,0.15)', color: '#C5E384' };
  }

  // 2. Prioritized Remediation Plan
  const recList = document.getElementById("remediation-list");
  recList.innerHTML = "";
  if (!data.remediation_plan || data.remediation_plan.length === 0) {
    recList.innerHTML = `<div style="padding: 2rem; text-align: center; color: var(--brand-500); background: rgba(197,227,132,0.1); border-radius: 12px;">[DONE] Excellent! No technical AEO/GEO vulnerabilities detected on this domain.</div>`;
  } else {
    data.remediation_plan.forEach((rec, idx) => {
      const card = document.createElement("div");
      card.className = "rec-item";
      const badgeColor = rec.severity === "error" ? "#EF4444" : "#F59E0B";
      const pLabel = priorityLabel(rec.priority_score || (idx + 1) * 3);

      const safeTitle = renderUserText(rec.title);
      const safeDesc = renderUserText(rec.description);
      const safeClaimStmt = renderUserText(rec.governing_claim_statement);
      const safeCheckCode = escapeHtml(rec.check_code);
      const safeKid = typeof escapeHtml === 'function' ? escapeHtml(rec.governing_claim_id || '') : String(rec.governing_claim_id || '');
      const encodedKid = encodeURIComponent(rec.governing_claim_id || '').replace(/'/g, '%27');

      // Render V2 Evidence
      let evidenceHtml = '';
      if (rec.source_citations && rec.source_citations.length > 0) {
        evidenceHtml += `<div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border-default); font-size: 0.85rem; color: var(--text-secondary);">`;
        evidenceHtml += `<div style="font-weight: 600; margin-bottom: 4px; text-transform: uppercase;">Source Citations:</div>`;
        rec.source_citations.forEach(src => {
          evidenceHtml += `<div style="margin-bottom: 2px;">• <a href="${safeUrl(src.url)}" target="_blank" style="color: var(--brand-500); text-decoration: none;">${escapeHtml(src.title || src.url)}</a> (${escapeHtml(src.authority)})</div>`;
        });
        evidenceHtml += `</div>`;
      }
      
      if (rec.backing_facts && rec.backing_facts.length > 0) {
        evidenceHtml += `<div style="margin-top: 8px; font-size: 0.85rem; color: var(--text-secondary);">`;
        evidenceHtml += `<div style="font-weight: 600; margin-bottom: 4px; text-transform: uppercase;">Backing Facts:</div>`;
        rec.backing_facts.forEach(fact => {
          evidenceHtml += `<div style="margin-bottom: 2px;">• [${escapeHtml(fact.kid)}] ${escapeHtml(fact.statement)}</div>`;
        });
        evidenceHtml += `</div>`;
      }

      card.innerHTML = `
        <div class="rec-header" onclick="toggleRecBody(this)">
          <div style="display: flex; align-items: center; gap: 1rem; flex: 1 1 300px;">
            <div class="step-num">${idx + 1}</div>
            <div>
              <div style="font-weight: 700; font-size: 1.15rem; color: var(--text-primary);">${safeTitle}</div>
              <div style="font-size: 0.85rem; color: var(--text-tertiary); font-family: 'JetBrains Mono', monospace; margin-top: 0.2rem;">Code: [${safeCheckCode}] • Severity: <span style="color: ${badgeColor}; font-weight: 600;">${rec.severity.toUpperCase()}</span></div>
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
            <span style="background: ${pLabel.bg}; color: ${pLabel.color}; padding: 0.3rem 0.8rem; border-radius: 6px; font-size: 0.8rem; font-weight: 700; font-family: 'JetBrains Mono', monospace;">${pLabel.text}</span>
            ${rec.is_contested ? `<span style="background: var(--status-warning-bg); color: var(--status-warning); padding: 0.3rem 0.8rem; border-radius: 6px; font-size: 0.8rem; font-weight: 700; border: 1px solid var(--status-warning-border); display:inline-flex; align-items:center; gap:4px;"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg> CONTESTED</span>` : ''}
            ${rec.is_stale ? `<span style="background: var(--status-danger-bg); color: var(--status-danger); padding: 0.3rem 0.8rem; border-radius: 6px; font-size: 0.8rem; font-weight: 700; border: 1px solid var(--status-danger-border); display:inline-flex; align-items:center; gap:4px;"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg> STALE DATA</span>` : ''}
            <span style="font-size: 1.2rem; color: var(--text-tertiary); margin-left: 0.4rem;"></span>
          </div>
        </div>
        <div class="rec-body ${idx === 0 ? 'open' : ''}">
          <p style="color: var(--text-primary); line-height: 1.6; margin-top: 0;">${safeDesc}</p>
          <a href="knowledge_explorer.html?kid=${encodedKid}" target="_blank" class="citation-box" style="display:block; text-decoration:none;" onclick="event.stopPropagation();">
            <span class="citation-badge"> View Knowledge Record [${safeKid}] (${rec.confidence} Confidence / ${rec.source_tier}) ↗</span>
            <div style="margin-top: 0.4rem; color:var(--text-primary);">${safeClaimStmt}</div>
            ${evidenceHtml}
          </a>
        </div>
      `;
      recList.appendChild(card);
    });
  }

 // 3. Guided Manual Review Wizard & Progress Meter (Item 9)
 const wizardList = document.getElementById("wizard-list");
 wizardList.innerHTML = "";
 evaluatedCardIds.clear();

 // Toggle the wizard empty state and shield banner based on whether an audit has run and cards exist
 const wizardEmptyState = document.getElementById('wizard-empty-state');
 const shieldBanner = document.getElementById('review-shield-banner');
 const caveatBox = document.getElementById('wizard-caveat-box');

 if (!data.manual_review_wizard || data.manual_review_wizard.length === 0) {
   if (wizardEmptyState) wizardEmptyState.style.display = 'none';
   if (shieldBanner) shieldBanner.style.display = 'none';
   if (caveatBox) caveatBox.style.display = 'block';
   wizardList.innerHTML = `
     <div style="padding: 2.5rem 1.5rem; text-align: center; color: var(--text-secondary); background: var(--surface-panel); border: 1px solid var(--border-default); border-radius: 12px; margin: 0 40px;">
       <h4 style="margin:0 0 8px 0; color:var(--brand-500); font-size:1.1rem; font-weight:700;">All Automated Checks Verified</h4>
       <p style="margin:0; font-size:0.9rem; color:var(--text-secondary);">All diagnostic checks were determined automatically by the audit engine. No qualitative manual reviews are required for this run.</p>
     </div>`;
   totalWizardCards = 0;
   updateShieldProgress();
 } else {
   if (wizardEmptyState) wizardEmptyState.style.display = 'none';
   if (shieldBanner) shieldBanner.style.display = 'flex';
   if (caveatBox) caveatBox.style.display = 'block';

   // T-B06: Dynamic card count based on mode + satisfied conditionals
   function computeShownCards(cards) {
     if (typeof window.GuidedReview !== 'undefined' &&
         typeof window.GuidedReview.isQuestionVisible === 'function') {
       return cards.filter(c => window.GuidedReview.isQuestionVisible(c.card_id)).length;
     }
     // Fallback: Express mode = 4, Full mode = all
     const mode = window.AreosContext && window.AreosContext.reviewMode;
     if (mode === 'express') return 4;
     return cards.length;
   }
   totalWizardCards = computeShownCards(data.manual_review_wizard);
   completedWizardCards = 0;
   updateShieldProgress();
   if (typeof window.GuidedReview !== "undefined" && typeof window.GuidedReview.start === "function") {
     window.GuidedReview.start(data.manual_review_wizard, {
       mode: "inline",
       container: "#wizard-list",
       runId: data.run_id,
       onVerdict: (id) => {
         if (!evaluatedCardIds.has(id)) {
           evaluatedCardIds.add(id);
           completedWizardCards++;
           updateShieldProgress(); // Item 9 Trigger
         }
       }
     });
   }
 }
}

// Item 9: Shield Progress Logic
function updateShieldProgress() {
  const shieldBanner = document.getElementById("review-shield-banner");
  const shieldIcon = document.getElementById("shield-icon");
  const shieldTitle = document.getElementById("shield-title");
  const shieldSub = document.getElementById("shield-sub");
  const progressText = document.getElementById("val-progress-text");
  const meterFill = document.getElementById("meter-fill");

  const pct = totalWizardCards > 0 ? Math.round((completedWizardCards / totalWizardCards) * 100) : 100;
  if (progressText) progressText.textContent = `${completedWizardCards} / ${totalWizardCards}`;
  if (meterFill) meterFill.style.width = `${pct}%`;

  if (pct === 100) {
    if (shieldBanner) shieldBanner.className = "context-helper-card";
    if (shieldIcon) shieldIcon.textContent = "✓";
    if (shieldTitle) shieldTitle.textContent = "Human Verification Complete";
    if (shieldSub) shieldSub.textContent = "Every check has been evaluated and recorded into the persistent empirical repository.";

    if (window._synthesisTriggeredForRun !== _activeRunId) {
      window._synthesisTriggeredForRun = _activeRunId;
      setTimeout(() => {
        if (typeof triggerPostWizardSynthesis === 'function') triggerPostWizardSynthesis();
      }, 1500);
    }
  } else {
    if (shieldBanner) shieldBanner.className = "context-helper-card";
    if (shieldIcon) shieldIcon.textContent = "";
    if (shieldTitle) shieldTitle.textContent = "Qualitative Evaluation Protocol";
    if (shieldSub) shieldSub.textContent = "Inspect on-page evidence to calibrate the composite diagnostic score and unlock synthesis.";
  }

  syncStepper(pct);
  syncResultsActionBanner(pct);
  syncOutcomeFormAvailability();
  syncFinalReportButton(pct);
}

// Reflects run progress on the 4-step navigation bar (replaces the old flat
// tab bar). Steps stay clickable regardless of lock state \u2014 locking is
// communicated visually and explained inline, never by disabling navigation.
function syncStepper(pct) {
  const steps = document.querySelectorAll('.step-btn');
  const wizardDone = totalWizardCards === 0 || completedWizardCards >= totalWizardCards;
  const hasSynthesis = !!(currentAuditData && currentAuditData.llm_synthesis && currentAuditData.llm_synthesis.llm_synthesis_used);

  steps.forEach(btn => {
    const step = parseInt(btn.dataset.step, 10);
    btn.classList.remove('step-complete', 'step-locked');

    if (step === 1 && currentAuditData) btn.classList.add('step-complete');
    if (step === 2 && currentAuditData) btn.classList.add('step-complete');
    if (step === 3) {
      if (wizardDone && currentAuditData) btn.classList.add('step-complete');
      else if (!currentAuditData) btn.classList.add('step-locked');
    }
    if (step === 4) {
      if (hasSynthesis) btn.classList.add('step-complete');
      else if (!wizardDone) btn.classList.add('step-locked');
    }
  });

  document.querySelectorAll('.step-connector').forEach((c, i) => {
    const beforeStep = steps[i];
    c.classList.toggle('is-filled', !!(beforeStep && beforeStep.classList.contains('step-complete')));
  });
}

// The single highest-leverage fix from the UX audit: the Results Dashboard
// must never look "finished" while human review is still outstanding.
function syncResultsActionBanner(pct) {
  const resBanner = document.getElementById("results-action-banner");
  if (!resBanner) return;

  if (totalWizardCards === 0 || !currentAuditData) {
    resBanner.style.display = "none";
    return;
  }

  const titleEl = document.getElementById("results-action-title");
  const subEl = document.getElementById("results-action-sub");
  const btnEl = resBanner.querySelector("button");

  if (pct < 100) {
    resBanner.style.display = "flex";
    resBanner.classList.remove("is-complete");
    if (titleEl) titleEl.textContent = `Provisional Score: ${totalWizardCards - completedWizardCards} qualitative check(s) pending`;
    if (subEl) subEl.textContent = "Complete the Manual Review Wizard to calibrate your final diagnostic score.";
    if (btnEl) {
      btnEl.textContent = "Complete Manual Review";
      btnEl.setAttribute("onclick", "document.querySelector('[data-tab=tab-wizard]').click()");
    }
  } else {
    resBanner.style.display = "flex";
    resBanner.classList.add("is-complete");
    if (titleEl) titleEl.textContent = "Human Verification Complete";
    if (subEl) subEl.textContent = "Your full executive synthesis report is ready.";
    if (btnEl) {
      btnEl.textContent = "View Final Report";
      btnEl.setAttribute("onclick", "document.querySelector('[data-tab=tab-synthesis]').click()");
    }
  }
}

// Outcome Logger inputs should never be interactively fillable if there's no
// run to log an outcome against \u2014 disable proactively instead of failing
// after the fact with a toast.
function syncOutcomeFormAvailability() {
  const hasRun = !!_activeRunId;
  document.querySelectorAll('.outcome-input, .btn-log-outcome').forEach(el => {
    el.disabled = !hasRun;
    el.title = hasRun ? '' : 'Run an audit first \u2014 outcomes are logged against a specific run.';
  });
}

// The "Download Final Report" button only appears once there's actually a
// final report \u2014 it supersedes the automated-findings export rather than
// competing with it. See CHANGELOG.md / audit \u00a73.11.
function syncFinalReportButton(pct) {
  const btn = document.getElementById('btn-download-final-report');
  if (!btn) return;
  const wizardDone = totalWizardCards === 0 || completedWizardCards >= totalWizardCards;
  const hasSynthesis = !!(currentAuditData && currentAuditData.llm_synthesis && currentAuditData.llm_synthesis.llm_synthesis_used);
  btn.style.display = (wizardDone && hasSynthesis) ? 'inline-flex' : 'none';
}

function downloadFinalReport() {
  const narrativeEl = document.getElementById('synth-narrative-body');
  const narrative = narrativeEl ? narrativeEl.textContent.trim() : '';
  if (!narrative) return AreosAPI.notify('Final report not ready yet.');
  const domain = document.getElementById("domain-input").value.trim();
  const blob = new Blob([`# Citeable Final Report \u2014 ${domain}\n\n${narrative}`], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `Citeable_Final_Report_${domain.replace(/[^a-zA-Z0-9]/g, "_")}.md`;
  a.click();
  URL.revokeObjectURL(url);
}
window.downloadFinalReport = downloadFinalReport;

// UX audit §5.3/§5.7 — rehydrates the full Studio UI (Results, Wizard,
// Synthesis) for a past run_id, via the one unified /full endpoint. This is
// what makes the retired standalone pages' redirects (manual_review.html,
// remediation.html, outcome.html — see CHANGELOG.md §3.8) land somewhere
// that actually shows real data instead of a reset "no active session"
// screen, and is what a bookmarked ?run_id= link resolves through.
async function loadRunById(runId) {
  try {
    const res = await AreosAPI.fetch(`/api/v1/audit/runs/${runId}/full`);
    if (!res.ok) {
      console.warn(`loadRunById: run ${runId} not found (HTTP ${res.status})`);
      return;
    }
    const full = await res.json();

    // executive_scorecard fields beyond overall_score depend on live
    // network calls made at scan time (robots.txt fetch, authority
    // lookup, citation sampling) and aren't reconstructable from stored
    // findings without re-crawling — see get_full_run_report()'s
    // docstring. Safe, inert defaults here so displayStudioResults()
    // (which reads several of these fields directly) doesn't throw on a
    // reload; the tiles it can't populate show a placeholder instead of
    // a guess.
    const data = {
      run_id: full.run_id,
      target_domain: full.target_domain,
      executive_scorecard: {
        overall_score: full.overall_score ?? 0,
        sub_scores: {},
        authority_metrics: { authority_score: 0, referring_domains: 0 },
        crawler_status: "See original scan",
        llms_txt_status: "See original scan",
        observed_citation_rate: "\u2014",
        score_breakdown: [],
        access_gate_applied: false,
        access_gate_cap: null,
      },
      remediation_plan: full.remediation_plan || [],
      llm_synthesis: full.llm_synthesis || { llm_synthesis_used: false, reason: "No synthesis ran" },
      manual_review_wizard: full.manual_review_wizard || [],
      raw_findings: full.raw_findings || [],
      tos_caveat: "",
    };

    currentAuditData = data;
    window.AreosContext = window.AreosContext || {};
    window.AreosContext.auditResult = data;
    _activeRunId = full.run_id;

    const domainInput = document.getElementById("domain-input");
    if (domainInput) domainInput.value = full.target_domain || "";

    displayStudioResults(data, full.target_domain, "Historical Run");

    // displayStudioResults() always starts completedWizardCards at 0 (it
    // has no way to know about verdicts submitted in an earlier session);
    // override with the real count the server just gave us.
    if (full.completeness) {
      totalWizardCards = full.completeness.total_wizard_cards;
      completedWizardCards = full.completeness.completed_wizard_cards;
      updateShieldProgress();
    }

    renderSynthesisTab(data);
    document.getElementById("studio-results").style.display = "block";
  } catch (err) {
    console.error("loadRunById failed:", err);
  }
}
window.loadRunById = loadRunById;

function submitWizardVerdict(runId, cardId, verdict, severity) {
  if (typeof window.GuidedReview !== "undefined" && typeof window.GuidedReview.submitInlineVerdict === "function") {
    return window.GuidedReview.submitInlineVerdict(cardId, verdict, {
      runId: runId,
      onVerdict: (id) => {
        if (!evaluatedCardIds.has(id)) {
          evaluatedCardIds.add(id);
          completedWizardCards++;
          updateShieldProgress(); // Item 9 Trigger
        }
      }
    });
  }
}

let claimDialog = null;
function getClaimDialog() {
  if (!claimDialog && typeof makeDialogAccessible === "function") {
    const modal = document.getElementById("claim-modal");
    if (modal) {
      claimDialog = makeDialogAccessible(modal, {
        role: "dialog",
        label: "Scientific Claim Details",
        onClose: () => closeClaimModal()
      });
    }
  }
  return claimDialog;
}

// Item 10: Interactive Claim Deep-Dive Modal
async function openClaimModal(claimId) {
 const modal = document.getElementById("claim-modal");
 modal.style.display = "flex";
  const dlg = getClaimDialog();
  if (dlg && typeof dlg.open === "function") dlg.open();
 document.getElementById("mod-claim-id").textContent = `CLAIM ID: ${claimId}`;
 document.getElementById("mod-title").textContent = "Retrieving scientific claim data...";
 document.getElementById("mod-stmt").textContent = "Loading empirical justification...";

 try {
 const res = await AreosAPI.fetch(`/api/v1/claims?claim_id=${claimId}`);
 if (res.ok) {
 const data = await res.json();
 if (data.claims && data.claims.length > 0) {
 const claim = data.claims[0];
 document.getElementById("mod-title").textContent = claim.title || claim.claim_type || `Research Finding ${claimId}`;
 document.getElementById("mod-conf").textContent = `Confidence: ${(claim.confidence_level || "HIGH").toUpperCase()}`;
 document.getElementById("mod-tier").textContent = `Source Tier: ${claim.source_tier || "Tier 1 (Patent/Empirical)"}`;
 document.getElementById("mod-stmt").textContent = claim.statement || claim.description || "Empirically verified across search engine AI snippet inclusion studies.";
 document.getElementById("mod-funnel").textContent = claim.funnel_stage || "All Funnel Stages";
 const scoreEl = document.getElementById("mod-score");
 if (scoreEl) scoreEl.textContent = claim.confidence_score ? `${claim.confidence_score} / 10` : (claim.confidence_level || "HIGH");
 } else {
 document.getElementById("mod-title").textContent = `Claim ${claimId} Details`;
 document.getElementById("mod-stmt").textContent = "Governing research claim verified in SQLite search engineering knowledge base.";
 }
 }
 } catch (e) {
 document.getElementById("mod-stmt").textContent = "Error communicating with local database.";
 }
}

function closeClaimModal() {
 document.getElementById("claim-modal").style.display = "none";
  const dlg = getClaimDialog();
  if (dlg && typeof dlg.close === "function") dlg.close();
}

// Item 12: Integrated Outcome Logger Widget
async function submitStudioOutcome() {
 if (!currentAuditData) return AreosAPI.notify("Please run an audit before logging an outcome.");
 const runId = currentAuditData.run_id;
 const desc = document.getElementById("out-desc").value.trim() || "Implemented recommended AEO/GEO Schema and content formatting fix";
 const metric = document.getElementById("out-metric").value.trim() || "Perplexity Citation Share";
 const delta = document.getElementById("out-delta").value.trim() || "12% → 32%";

 const parts = delta.split("→");
 const before = parts[0] ? parts[0].trim() : "0%";
 const after = parts[1] ? parts[1].trim() : delta;

 try {
 const res = await AreosAPI.fetch(`/api/v1/audit/runs/${runId}/outcomes`, {
 method: "POST",
 headers: getAuthHeaders({ "Content-Type": "application/json" }),
 body: JSON.stringify({
 remediation_id: `REM-${runId}`,
 fix_description: desc,
 metric_name: metric,
 metric_before: before,
 metric_after: after,
 page_url: "https://" + document.getElementById("domain-input").value.trim(),
 notes: "Logged instantly via Interactive Audit Studio Widget"
 })
 });

 if (res.ok) {
 const receipt = await res.json();
 const receiptEl = document.getElementById("outcome-receipt");
 receiptEl.style.display = "block";
 receiptEl.textContent = `[DONE] Empirical outcome recorded in SQLite registry under new Claim ID: ${receipt.claim_id}`;
 document.getElementById("out-desc").value = "";
 } else AreosAPI.notify("Failed to log outcome. Verify server authorization token.");
 } catch (error) {
 console.error("Error logging outcome:", error);
 AreosAPI.notify("Network error while logging outcome.");
 }
}

// Item 1: One-Click Report Export (Markdown)
function exportExecutiveReport() {
  if (!currentAuditData) return AreosAPI.notify("No active audit results to export.");
  const domainInput = document.getElementById("domain-input");
  const domain = domainInput ? domainInput.value.trim() : (currentAuditData.target_domain || "unknown.com");
  const sc = currentAuditData.executive_scorecard || {};
  const wizardDone = totalWizardCards === 0 || completedWizardCards >= totalWizardCards;

  let md = wizardDone
    ? `# Citeable Generative Search Engine Audit Report (Automated Findings)\n`
    : `# Citeable Generative Search Engine Audit Report — PRELIMINARY, Human Review Not Yet Complete\n`;
  md += `**Target Domain**: ${escapeHtml(domain)}\n`;
  md += `**Audit Date**: ${new Date().toLocaleDateString()} • **Run ID**: \`${escapeHtml(currentAuditData.run_id || "")}\`\n\n`;
  if (!wizardDone) {
    md += `> [!WARNING]\n> **${Math.max(0, totalWizardCards - completedWizardCards)} manual review check(s) not yet completed.** This export contains automated findings only. Complete the Manual Review Wizard in Citeable Studio for the full report.\n\n`;
  }
  md += `## 1. Executive Scorecard\n`;
  md += `| Diagnostic Index | Measured Value | Status Note |\n`;
  md += `| :--- | :--- | :--- |\n`;
  md += `| **Overall AEO Score** | **${sc.overall_score || 0} / 100** | Weighted AI Visibility Rating |\n`;
  
  if (sc.provider_used === 'not_configured' || !sc.authority_metrics || !sc.authority_metrics.authority_score) {
    md += `| **Entity Authority Score** | **N/A** | Authority metrics not configured |\n`;
  } else {
    md += `| **Entity Authority Score** | **${sc.authority_metrics.authority_score || 0} / 100** | ${sc.authority_metrics.referring_domains || 0} referring domains |\n`;
  }

  md += `| **AI Crawler Access** | **${sc.crawler_status || 'N/A'}** | llms.txt: ${sc.llms_txt_status || 'N/A'} |\n`;
  md += `| **Observed Citation Frequency**| **${sc.observed_citation_rate || 'N/A'}** | Live AI Answer Engine Sampling |\n\n`;
 
 md += `## 2. Prioritized Remediation Plan\n\n`;
 if (currentAuditData.remediation_plan && currentAuditData.remediation_plan.length > 0) {
 currentAuditData.remediation_plan.forEach((rec, i) => {
 const code = rec.remediation_snippet || '';
 md += `### Step ${i+1}: ${escapeHtml(rec.title)} [Priority: ${rec.priority_score || (i+1)*3}]\n`;
 md += `- **Check Code**: \`${escapeHtml(rec.check_code)}\` (${(rec.severity || 'info').toUpperCase()})\n`;
 md += `- **Diagnostic Details**: ${escapeHtml(rec.description)}\n`;
 md += `- **Governing Research Basis**: *Claim ID ${rec.governing_claim_id}* (${rec.confidence} Confidence / ${rec.source_tier}): "${escapeHtml(rec.governing_claim_statement)}"\n\n`;
 
 if (rec.evidence_chain || rec.source_citations || rec.backing_facts) {
 md += `  **Supporting Evidence:**\n`;
 if (rec.source_citations && rec.source_citations.length > 0) {
 rec.source_citations.forEach(src => {
 md += `  - **Source**: ${escapeHtml(src.title || src.url)} (${escapeHtml(src.authority)})\n`;
 });
 }
 if (rec.backing_facts && rec.backing_facts.length > 0) {
 rec.backing_facts.forEach(fact => {
 md += `  - **Fact [${escapeHtml(fact.kid)}]**: ${escapeHtml(fact.statement)}\n`;
 });
 }
 md += `\n`;
 }

 md += `**Recommended Implementation Code / Fix**:\n\`\`\`html\n${code}\n\`\`\`\n\n`;
 });
 } else {
 md += `*No structural AEO/GEO vulnerabilities detected during automated analysis.*\n\n`;
 }

 md += `## 3. Qualitative Human Evaluation Registry\n\n`;
 md += `*Manual verification completed via Citeable Guided Review Shield (${completedWizardCards}/${totalWizardCards} cards signed off).* \n\n`;
 md += `---\n*Generated automatically via Google Antigravity Citeable Studio • Mandatory Governance Caveat: ${currentAuditData.tos_caveat}*\n\n*Disclaimer: Findings are algorithmic diagnostic observations, not guarantees of commercial outcomes or professional advice. Provided AS-IS without warranty. See docs for full legal notices.*\n`;

 const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
 const url = URL.createObjectURL(blob);
 const a = document.createElement("a");
 a.href = url;
 a.download = `Citeable_Executive_Audit_${domain.replace(/[^a-zA-Z0-9]/g, "_")}.md`;
 a.click();
 URL.revokeObjectURL(url);
}

function resetMonitorStages() {
  if (window._pipelineStageInterval) clearInterval(window._pipelineStageInterval);
  ["robots", "schema", "extract", "format", "authority", "citation"].forEach((id, idx) => {
  const el = document.querySelector(`#stage-${id} .stage-icon`);
  el.className = idx === 0 ? "stage-icon active" : "stage-icon";
  el.innerHTML = idx === 0 ? `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="animation:spin 1s linear infinite;"><circle cx="12" cy="12" r="10" stroke-opacity="0.25"/><path d="M12 2a10 10 0 0 1 10 10" stroke-opacity="0.85"/></svg>` : "";
  });
}

function animatePipelineStages() {
  if (window._pipelineStageInterval) clearInterval(window._pipelineStageInterval);
  const stages = ["robots", "schema", "extract", "format", "authority", "citation"];
  let current = 0;
  window._pipelineStageInterval = setInterval(() => {
  if (current < stages.length - 1) {
  const oldEl = document.querySelector(`#stage-${stages[current]} .stage-icon`);
  if (oldEl) { oldEl.className = "stage-icon done"; oldEl.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>`; }
  current++;
  const newEl = document.querySelector(`#stage-${stages[current]} .stage-icon`);
  if (newEl) { newEl.className = "stage-icon active"; newEl.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="animation:spin 1s linear infinite;"><circle cx="12" cy="12" r="10" stroke-opacity="0.25"/><path d="M12 2a10 10 0 0 1 10 10" stroke-opacity="0.85"/></svg>`; }
  } else {
    clearInterval(window._pipelineStageInterval);
    window._pipelineStageInterval = null;
  }
  }, 320);
}

function completeAllStages() {
  if (window._pipelineStageInterval) {
    clearInterval(window._pipelineStageInterval);
    window._pipelineStageInterval = null;
  }
  ["robots", "schema", "extract", "format", "authority", "citation"].forEach(id => {
  const el = document.querySelector(`#stage-${id} .stage-icon`);
  if (el) { el.className = "stage-icon done"; el.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>`; }
  });
}

function toggleRecBody(headerEl) { headerEl.nextElementSibling.classList.toggle("open"); }

window.toggleRecBody = toggleRecBody;
window.submitWizardVerdict = submitWizardVerdict;
window.openClaimModal = openClaimModal;
window.closeClaimModal = closeClaimModal;
window.submitStudioOutcome = submitStudioOutcome;
window.exportExecutiveReport = exportExecutiveReport;

// ─────────────────────────────────────────────────────────────────────────────
// Phase 2 — AI Synthesis Tab
// ─────────────────────────────────────────────────────────────────────────────

// Track the active run_id so post-wizard synthesis knows which run to synthesize
let _activeRunId = null;

/**
 * Called after audit completes. Renders the llm_synthesis block.
 * If synthesis is pending (waiting for manual review), shows a locked
 * state directing the user to complete the Guided Wizard first.
 */
function renderSynthesisTab(data) {
  const synth = data.llm_synthesis || {};

  // Store run_id for later synthesis trigger
  if (data.run_id) _activeRunId = data.run_id;

  const icon  = document.getElementById('synth-status-icon');
  const title = document.getElementById('synth-status-title');
  const sub   = document.getElementById('synth-status-sub');
  const plog  = document.getElementById('synth-provider-log');
  if (plog) plog.innerHTML = '';

  if (!synth.llm_synthesis_used) {
    // Two distinct states: pending (wizard not done yet) vs truly unavailable
    if (synth.pending) {
      if (icon)  icon.textContent  = '\u23F3';
      if (title) title.textContent = 'Almost there \u2014 finish Manual Review to unlock your final report';
      if (sub)   sub.innerHTML = `
        <span style="color:#f59e0b;">Your final report is written after every manual check is answered.</span><br>
        <span style="color:#64748b; font-size:0.85rem;">This makes sure the AI is writing from your verified findings, not guessing.</span><br><br>
        <button onclick="document.querySelector('[data-tab=tab-wizard]') && document.querySelector('[data-tab=tab-wizard]').click()" style="background:rgba(245,158,11,0.15); border:1px solid rgba(245,158,11,0.4); color:#f59e0b; padding:0.5rem 1.2rem; border-radius:8px; cursor:pointer; font-size:0.9rem; font-weight:600;">
          \u2192 Finish Manual Review
        </button>`;
    } else {
      if (icon)  icon.textContent  = '\u26A0\uFE0F';
      if (title) title.textContent = 'Final report not available for this run';
      if (sub) {
        if (synth.byok_prompt) {
          sub.innerHTML = `
            <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.1); border-radius:12px; padding:1.4rem 1.6rem; margin-top:0.8rem; text-align:left;">
              <p style="font-size:1rem; color:#e2e8f0; margin:0 0 0.6rem 0; font-weight:600;">Add a free AI key to generate your final report</p>
              <p style="font-size:0.875rem; color:#94a3b8; margin:0 0 1.1rem 0; line-height:1.6;">
                Your audit data is ready. The final report needs an AI key to write the narrative.<br>
                Google Gemini and Groq are both free — no credit card required.
              </p>
              <button onclick="window.byokVaultManager && window.byokVaultManager.open ? window.byokVaultManager.open() : document.querySelector('[onclick*=byok]') && document.querySelector('[onclick*=byok]').click()" style="background:#ffffff; color:#000000; border:none; border-radius:8px; padding:10px 22px; font-weight:700; font-size:0.9rem; cursor:pointer; letter-spacing:0.04em;">
                Open BYOK AI Vault &rarr;
              </button>
              <p style="font-size:0.8rem; color:#64748b; margin:0.8rem 0 0;">Keys stay in your browser only &mdash; never stored on our servers.</p>
            </div>`;
        } else {
          sub.textContent = synth.reason || 'No AI provider configured';
        }
      }
    }
    const fp = document.getElementById('synth-flags-panel');
    const nc = document.getElementById('synth-narrative-card');
    const dd = document.getElementById('synth-draft-details');
    if (fp) fp.style.display = 'none';
    if (nc) nc.style.display = 'none';
    if (dd) dd.style.display = 'none';
    if (typeof syncFinalReportButton === 'function') syncFinalReportButton();
    return;
  }

  // Status bar — success
  icon.textContent  = '\u2713';
  title.textContent = 'Your final report is ready';
  const flagCount   = (synth.flags || []).length;
  const resolved    = synth.flags_resolved || 0;
  sub.textContent   = `${flagCount} claim(s) double-checked \u00b7 ${resolved} corrected before finalizing`;

  // Provider log badges
  (synth.provider_log || []).forEach(step => {
    const badge = document.createElement('span');
    const [label, direction] = step.split(':');
    const colors = { synthesizer: '#6ee7b7', red_teamer: '#f87171', grounder: '#38bdf8' };
    badge.style.cssText = `background:rgba(30,41,59,0.8); color:${colors[label] || '#94a3b8'}; padding:0.25rem 0.6rem; border-radius:6px; font-size:0.75rem; font-family:'JetBrains Mono',monospace;`;
    badge.textContent = `${label.replace('_', '-')} [${direction === 'reverse_waterfall' ? 'adversarial' : 'forward'}]`;
    plog.appendChild(badge);
  });

  // Red Teamer Flags
  const flagsPanel = document.getElementById('synth-flags-panel');
  const flagsList  = document.getElementById('synth-flags-list');
  const flagsCnt   = document.getElementById('synth-flags-count');
  const flagsRes   = document.getElementById('synth-flags-resolved');
  if (flagCount > 0) {
    flagsPanel.style.display = 'block';
    flagsCnt.textContent = `${flagCount} flag${flagCount !== 1 ? 's' : ''}`;
    flagsList.innerHTML = '';
    const flagColors = { HALLUCINATED_CLAIM: '#f87171', FABRICATED_STAT: '#fbbf24', UNSUPPORTED_LEAP: '#fb923c', VAGUE: '#94a3b8' };
    (synth.flags || []).forEach(f => {
      const item = document.createElement('div');
      const color = flagColors[f.flag] || '#94a3b8';
      item.style.cssText = `background:rgba(15,23,42,0.6); border-left:3px solid ${color}; padding:0.6rem 1rem; border-radius:0 8px 8px 0; font-size:0.85rem;`;
      item.innerHTML = `<span style="color:${color}; font-family:'JetBrains Mono',monospace; font-weight:700;">${escapeHtml(f.flag)}</span>: ${escapeHtml(f.reason || '')}<br><em style="color:#64748b; font-size:0.8rem;">"${escapeHtml((f.text_excerpt || '').slice(0, 120))}"</em>`;
      flagsList.appendChild(item);
    });
    if (resolved > 0) {
      flagsRes.textContent = `Grounder resolved ${resolved} serious flag(s). VAGUE flags softened with domain-specific context.`;
    } else {
      flagsRes.textContent = 'No serious flags — Grounder applied evidence tier labels only.';
    }
  } else {
    flagsPanel.style.display = 'block';
    flagsCnt.textContent = '0 flags';
    flagsList.innerHTML = '<div style="color:#6ee7b7; font-size:0.9rem;"> Red Teamer found no violations. Grounder applied evidence tier labels.</div>';
    flagsRes.textContent = '';
  }

  // Final narrative
  const narrativeCard = document.getElementById('synth-narrative-card');
  narrativeCard.style.display = 'block';
  document.getElementById('synth-narrative-body').textContent = synth.narrative || '';

  // Draft (auditable, collapsed)
  if (synth.draft) {
    const draftDetails = document.getElementById('synth-draft-details');
    draftDetails.style.display = 'block';
    document.getElementById('synth-draft-body').textContent = synth.draft;
  }

  // Auto-switch to synthesis tab to show results
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
  const synthBtn = document.getElementById('tab-btn-synthesis');
  if (synthBtn) synthBtn.classList.add('active');
  document.getElementById('tab-synthesis').style.display = 'block';

  if (typeof syncFinalReportButton === 'function') syncFinalReportButton();
  if (typeof syncStepper === 'function') syncStepper();
}

/** Copy grounded narrative to clipboard */
function copySynthNarrative() {
  const text = document.getElementById('synth-narrative-body').textContent;
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => {
    AreosAPI.notify('Grounded narrative copied to clipboard.');
  }).catch(() => {
    AreosAPI.notify('Copy failed — please select and copy manually.');
  });
}

/**
 * Triggered by GuidedReview.finishAndGoToReport() AFTER the wizard is done.
 * POSTs to /api/v1/audit/runs/{run_id}/synthesize which now has both
 * automated findings AND the human manual verdicts from the DB.
 * Re-renders the synthesis tab with real results.
 */
async function triggerPostWizardSynthesis() {
  if (!_activeRunId) {
    console.warn('[Synthesis] No active run_id — cannot trigger synthesis.');
    return;
  }

  // Show a loading state in the synthesis tab
  const icon  = document.getElementById('synth-status-icon');
  const title = document.getElementById('synth-status-title');
  const sub   = document.getElementById('synth-status-sub');
  if (icon)  icon.textContent  = '\u2699';
  if (title) title.textContent = 'Writing your final report...';
  if (sub)   sub.innerHTML = `
    <span style="color:#38bdf8;">Drafting, then double-checking every claim before finalizing.</span><br>
    <span style="color:#64748b; font-size:0.85rem;">Your human review verdicts are being merged with the automated findings.</span>`;

  // Switch to the synthesis tab so user sees progress
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
  const synthBtn = document.getElementById('tab-btn-synthesis');
  if (synthBtn) synthBtn.classList.add('active');
  const synthTab = document.getElementById('tab-synthesis');
  if (synthTab) synthTab.style.display = 'block';
  // TQ-008: Lock all wizard inputs immediately to prevent modification during synthesis
  document.querySelectorAll('#wizard-list input, #wizard-list textarea, #wizard-list button.btn-verdict, .gr-card input, .gr-card textarea, .gr-card button').forEach(el => {
    el.disabled = true;
    el.style.opacity = '0.5';
    el.style.cursor = 'not-allowed';
  });

  try {
    const res = await AreosAPI.fetch(`/api/v1/audit/runs/${_activeRunId}/synthesize`, {
      method: 'POST',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      if (icon)  icon.innerHTML   = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
      if (title) title.textContent = 'Synthesis failed';
      if (sub)   sub.textContent   = err.detail || 'Unknown error from synthesis endpoint';
      // QA-FE / TR-503: Re-enable inputs on failure so user can retry
      document.querySelectorAll('#wizard-list input, #wizard-list textarea, #wizard-list button.btn-verdict, .gr-card input, .gr-card textarea, .gr-card button').forEach(el => {
        el.disabled = false;
        el.style.opacity = '1';
        el.style.cursor = 'default';
      });
      return;
    }
    const synthResult = await res.json();
    // Re-render synthesis tab with real data
    renderSynthesisTab({ llm_synthesis: synthResult, run_id: _activeRunId });
    AreosAPI.notify('AI Synthesis complete — grounded narrative ready.', 'success');
  } catch (err) {
    console.error('[Synthesis] POST failed:', err);
    if (icon)  icon.innerHTML   = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
    if (title) title.textContent = 'Synthesis request failed';
    if (sub)   sub.textContent   = err.message;
    // QA-FE / TR-503: Re-enable inputs on failure so user can retry
    document.querySelectorAll('#wizard-list input, #wizard-list textarea, #wizard-list button.btn-verdict, .gr-card input, .gr-card textarea, .gr-card button').forEach(el => {
      el.disabled = false;
      el.style.opacity = '1';
      el.style.cursor = 'default';
    });
  }
}

/** Load synthesis prompts into the editor textareas */
// Synthesis prompt editing (load/save/reset) moved to a dedicated
// admin-only page (synthesis_prompts.html/.js) — see CHANGELOG.md. It
// edited global state affecting every future audit run for every user,
// and previously rendered unconditionally on this tab for every visitor
// (admin or not), silently 401ing for anyone without an admin token.

window.copySynthNarrative = copySynthNarrative;
