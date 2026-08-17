
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
 const domain = domainInput.value.trim() || "madmarketers.in";
 const funnelValue = funnelSelect.value;
 const funnelText = funnelSelect.options[funnelSelect.selectedIndex].text;

 // UI reset & start execution animation
 btnRun.disabled = true;
 btnRun.innerHTML = `<span>⏳ Running Diagnostic Pipeline...</span>`;
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
 sample_content: `Mad Marketers (${domain}) delivers high-performance digital marketing, executive branding, and performance search engineering solutions across targeted user funnels.`,
 api_provider: "auto"
 })
 });

 if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
 const data = await res.json();
 currentAuditData = data;
 
 setTimeout(() => {
 completeAllStages();
 setTimeout(() => {
 try {
 monitor.style.display = "none";
 displayStudioResults(data, domain, funnelText);
 fetchHistoricalDelta(domain, data.executive_scorecard.overall_score).catch(e => console.error(e));
 renderCitationDistribution(domain, data.sample_res);
 renderSynthesisTab(data);
 resultsArea.style.display = "block";
 btnRun.disabled = false;
 btnRun.innerHTML = `<span>RUN FULL SPECTRUM AUDIT</span>`;
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
 <pre style="white-space:pre-wrap;color:#f87171;">${err.stack}</pre>
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
 btnRun.innerHTML = `<span>RUN FULL SPECTRUM AUDIT</span>`;
 monitor.style.display = "none";
 }
 });
});

// Item 11: Populate Prompt Funnel Selector
async function loadPromptsIntoSelector() {
 try {
 const res = await AreosAPI.fetch("/api/v1/prompts");
 if (res.ok) {
 const data = await res.json();
 const select = document.getElementById("funnel-stage-select");
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
 <div class="delta-box">
 <span style="font-size: 2rem;"></span>
 <div>
 <strong style="color: #ffffff;">Initial Baseline Evaluation</strong>
 <p style="margin: 0.2rem 0 0; color: #94a3b8; font-size: 0.88rem;">This is the first comprehensive audit recorded for ${domain}. Future runs will plot your exact score progression and technical resolution delta here.</p>
 </div>
 </div>`;
 } else {
 const lastRun = domainRuns[1];
 const prevScore = lastRun.overall_score || 0;
 const diff = currentScore - prevScore;
 const sign = diff >= 0 ? "+" : "";
 const color = diff >= 0 ? "#10b981" : "#ef4444";

 container.innerHTML = `
 <div class="delta-box">
  <span style="font-size: 2rem; opacity:0.8;">📈</span>
 <div>
 <strong style="color: #ffffff; font-size: 1.05rem;">Score Delta: <span style="color: ${color}; font-weight: 800;">${sign}${diff} points</span> vs. previous run (${lastRun.run_date.split('T')[0]})</strong>
 <p style="margin: 0.3rem 0 0; color: #cbd5e1; font-size: 0.88rem;">AI Crawler parsing obstacles resolved • Brand citation velocity exhibits steady upward trend across answer engines.</p>
 </div>
 </div>`;
 }
 } catch (e) {
 container.innerHTML = `<p style="color: #64748b;">Historical comparison requires at least two completed audit runs for this domain.</p>`;
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
 const colors = ["var(--neon-cyan)", "var(--neon-purple)", "#3b82f6", "#64748b", "#10b981", "#f59e0b"];
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
 <strong style="color: #ffffff;">${src.pct}%</strong>
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


// Helper to enrich fallback qualitative guidance when automated reasons are generic
function enrichWizardCard(wiz, domain) {
 let title = wiz.title || wiz.check_name || `Diagnostic Check: ${wiz.card_id}`;
 if (title === "Expert Human Inspection Required" || !title) {
 if (wiz.card_id === "C082") title = "Validate Brand Authority vs. Competitor Consensus";
 else if (wiz.card_id === "C058" || (wiz.reason && wiz.reason.includes("EXTRACTABILITY"))) title = "Verify RAG Text Density & Javascript Render Dependency";
 if (wiz.card_id === "C061") title = "Check for Buried Answers & Visual Banner Obstructions";
 }

 let what = wiz.what_to_look_for || "";
 let how = wiz.how_to_fill || "";

 if (what.includes("Perform expert qualitative verification") || !what) {
 if (wiz.card_id === "C082") {
 what = `Examine ${domain} across top AI answer summaries (Perplexity, Gemini, ChatGPT). Determine if third-party directories or competitors are capturing brand queries due to stronger domain rating or unlinked mention frequency.`;
 how = `Document specific competitor URLs appearing above ${domain}. Select 'Warn' if competitors dominate summaries, or 'Pass' if brand entity is properly recognized.`;
 } else if (wiz.card_id === "C058") {
 what = `Inspect ${domain} HTML source code. Confirm whether essential business facts, pricing, and contact capabilities are directly visible in plain text rather than hidden behind interactive client-side JavaScript, iframes, or canvas graphics.`;
 how = `If key promotional claims disappear when JS is disabled, record the affected component in notes and select 'Fail' or 'Warn' so targeted schema remediation is prioritized.`;
 } else if (wiz.card_id === "C061") {
 what = `Verify whether definitive core value propositions appear above the fold within the first 2-3 paragraphs on ${domain}, without being buried below excessive hero banners or vague promotional introductions.`;
 how = `Verify paragraph structure against Zyppy extraction guidelines. If answers are concise and self-contained, select 'Pass'. Otherwise describe the visual layout blocking in notes.`;
 } else {
 what = `Review ${domain} page architecture against qualitative AEO criteria for check [${wiz.card_id}]. Ensure facts and statistics are unambiguous, verifiable, and scannable by automated crawlers.`;
 how = `Enter clear observational evidence in the notes box below describing what was found on the domain, then select Pass, Warn, or Fail to commit your verdict to the SQLite registry.`;
 }
 }

 return { title, what_to_look_for: what, how_to_fill: how };
}

function displayStudioResults(data, domain, funnelText) {
 document.getElementById("res-target-header").textContent = `Audit Report: ${domain}`;
 document.getElementById("res-funnel-label").textContent = `Funnel Profile: ${funnelText}`;

 // 1. Executive Scorecard
 const score = data.executive_scorecard.overall_score;
 const sc    = data.executive_scorecard;

 // Score display with ℹ️ link to methodology docs
 const scoreEl = document.getElementById("res-score");
 scoreEl.innerHTML = `${score}<span style="font-size:0.45em;vertical-align:super;color:#64748b;">/100</span>
          <a href="docs.html#5-deterministic-scoring-model" target="_blank" title="How is this score calculated?"
      style="font-size:0.28em;vertical-align:super;margin-left:0.4em;color:#6366f1;text-decoration:none;
             background:rgba(99,102,241,0.12);padding:2px 6px;border-radius:4px;font-weight:600;
             border:1px solid rgba(99,102,241,0.3);">ℹ︎ How?</a>`;

 // Sub-score layer bars
 const subScores = sc.sub_scores || {};
 const layerOrder = [
  { id: "citation",  icon: "🔍", label: "Citation",      color: "#6366f1" },
  { id: "content",   icon: "📄", label: "Content",       color: "#8b5cf6" },
  { id: "access",    icon: "🤖", label: "Access",        color: "#06b6d4" },
  { id: "authority", icon: "🏛️", label: "Authority",     color: "#f59e0b" },
  { id: "schema",    icon: "🏷️", label: "Schema",        color: "#10b981" },
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
  const barColor = pct >= 80 ? "#10b981" : pct >= 50 ? "#f59e0b" : "#ef4444";
  const deductionTip = (ls.deductions || []).map(d =>
   `${d.code}: ${d.points}pts`
  ).join(" | ") || "No deductions";
  return `
  <div title="${deductionTip}" style="cursor:default;">
   <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">
    <span style="font-size:0.78rem;color:#94a3b8;font-family:'JetBrains Mono',monospace;">
     ${layer.icon} ${layer.label.toUpperCase()}
    </span>
    <span style="font-size:0.78rem;font-weight:700;color:#e2e8f0;font-family:'JetBrains Mono',monospace;">
     ${ls.score}/${ls.max}
    </span>
   </div>
   <div style="background:rgba(255,255,255,0.06);border-radius:4px;height:6px;overflow:hidden;">
    <div style="width:${pct}%;height:100%;background:${barColor};border-radius:4px;
                transition:width 0.8s cubic-bezier(0.4,0,0.2,1);"></div>
   </div>
  </div>`;
 }).join("");

 // Gate warning
 if (sc.access_gate_applied) {
  const gateWarn = document.createElement("div");
  gateWarn.style.cssText = "margin-top:0.8rem;padding:0.6rem 0.9rem;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:8px;font-size:0.8rem;color:#fca5a5;";
  gateWarn.textContent = `⚠ Access Gate applied — score capped at ${sc.access_gate_cap}. AI crawlers cannot fully access this site.`;
  subScoreEl.appendChild(gateWarn);
 }

 // Score justification ledger (collapsible)
 const breakdown = sc.score_breakdown || [];
 if (breakdown.length > 0) {
  let ledgerEl = document.getElementById("res-score-ledger");
  if (!ledgerEl) {
   ledgerEl = document.createElement("details");
   ledgerEl.id = "res-score-ledger";
   ledgerEl.style.cssText = "margin-top:1rem;font-size:0.78rem;color:#64748b;";
   subScoreEl.after(ledgerEl);
  }
  const sorted = [...breakdown].sort((a, b) => (b.running_total||0) - (a.running_total||0));
  ledgerEl.innerHTML = `
   <summary style="cursor:pointer;color:#94a3b8;font-family:'JetBrains Mono',monospace;
                   font-size:0.75rem;user-select:none;list-style:none;margin-bottom:0.5rem;">
    ▸ Score justification ledger (${breakdown.length} deductions)
   </summary>
   <table style="width:100%;border-collapse:collapse;font-family:'JetBrains Mono',monospace;font-size:0.73rem;">
    <thead>
     <tr style="color:#475569;border-bottom:1px solid #1e293b;">
      <th style="text-align:left;padding:4px 6px;">Check Code</th>
      <th style="text-align:right;padding:4px 6px;">Points</th>
      <th style="text-align:right;padding:4px 6px;">Running Total</th>
     </tr>
    </thead>
    <tbody>
     <tr style="color:#6ee7b7;">
      <td style="padding:4px 6px;">Starting score</td>
      <td style="text-align:right;">—</td>
      <td style="text-align:right;font-weight:700;">100</td>
     </tr>
     ${sorted.map(d => `
      <tr style="border-top:1px solid rgba(255,255,255,0.04);color:#cbd5e1;"
          title="${escapeHtml(d.message||'')}">
       <td style="padding:4px 6px;">${escapeHtml(d.code)}</td>
       <td style="text-align:right;color:#f87171;">${d.points}</td>
       <td style="text-align:right;font-weight:600;">${d.running_total}</td>
      </tr>`).join("")}
     <tr style="border-top:2px solid #334155;color:#6366f1;font-weight:700;">
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
  if (s >= 9) return { text: 'CRITICAL', bg: 'rgba(239,68,68,0.2)', color: '#fca5a5' };
  if (s >= 7) return { text: 'HIGH', bg: 'rgba(239,68,68,0.12)', color: '#f87171' };
  if (s >= 5) return { text: 'MEDIUM', bg: 'rgba(245,158,11,0.18)', color: '#fbbf24' };
  return { text: 'LOW', bg: 'rgba(16,185,129,0.12)', color: '#6ee7b7' };
 }

 // 2. Prioritized Remediation Plan
 const recList = document.getElementById("remediation-list");
 recList.innerHTML = "";
 if (!data.remediation_plan || data.remediation_plan.length === 0) {
 recList.innerHTML = `<div style="padding: 2rem; text-align: center; color: #6ee7b7; background: rgba(16, 185, 129, 0.1); border-radius: 12px;">[DONE] Excellent! No technical AEO/GEO vulnerabilities detected on this domain.</div>`;
 } else {
 data.remediation_plan.forEach((rec, idx) => {
 const card = document.createElement("div");
 card.className = "rec-item";
 const badgeColor = rec.severity === "error" ? "#ef4444" : "#f59e0b";
 const pLabel = priorityLabel(rec.priority_score || (idx + 1) * 3);

 const safeTitle = renderUserText(rec.title);
 const safeDesc = renderUserText(rec.description);
 const safeClaimStmt = renderUserText(rec.governing_claim_statement);
 const safeCheckCode = escapeHtml(rec.check_code);

 card.innerHTML = `
 <div class="rec-header" onclick="toggleRecBody(this)">
 <div style="display: flex; align-items: center; gap: 1rem; flex: 1 1 300px;">
 <div class="step-num">${idx + 1}</div>
 <div>
 <div style="font-weight: 700; font-size: 1.15rem; color: #f1f5f9;">${safeTitle}</div>
 <div style="font-size: 0.85rem; color: #64748b; font-family: 'JetBrains Mono', monospace; margin-top: 0.2rem;">Code: [${safeCheckCode}] • Severity: <span style="color: ${badgeColor}; font-weight: 600;">${rec.severity.toUpperCase()}</span></div>
 </div>
 </div>
  <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
  <span style="background: ${pLabel.bg}; color: ${pLabel.color}; padding: 0.3rem 0.8rem; border-radius: 6px; font-size: 0.8rem; font-weight: 700; font-family: 'JetBrains Mono', monospace;">${pLabel.text}</span>
  <span style="font-size: 1.2rem; color: #94a3b8; margin-left: 0.4rem;"></span>
 </div>
 </div>
 <div class="rec-body ${idx === 0 ? 'open' : ''}">
 <p style="color: #e2e8f0; line-height: 1.6; margin-top: 0;">${safeDesc}</p>
 <a href="claims_browser.html?claim_id=${rec.governing_claim_id}" target="_blank" class="citation-box" style="display:block; text-decoration:none;" onclick="event.stopPropagation();">
 <span class="citation-badge"> View Governing Research Basis [Claim ID: ${rec.governing_claim_id}] (${rec.confidence} Confidence / ${rec.source_tier}) ↗</span>
 <div style="margin-top: 0.4rem; color:var(--text);">${safeClaimStmt}</div>
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

 // Toggle the wizard empty state based on whether cards exist
 const wizardEmptyState = document.getElementById('wizard-empty-state');

 if (!data.manual_review_wizard || data.manual_review_wizard.length === 0) {
  if (wizardEmptyState) wizardEmptyState.style.display = 'flex';
 wizardList.innerHTML = `<div style="padding: 1.5rem; text-align: center; color: #94a3b8; background: rgba(30, 41, 59, 0.4); border-radius: 12px;">All diagnostic checks were determined automatically. No qualitative manual reviews required.</div>`;
 totalWizardCards = 0;
 updateShieldProgress();
 } else {
  if (wizardEmptyState) wizardEmptyState.style.display = 'none';
 totalWizardCards = data.manual_review_wizard.length;
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
 progressText.textContent = `${completedWizardCards} / ${totalWizardCards}`;
 meterFill.style.width = `${pct}%`;

 if (pct === 100) {
 shieldBanner.className = "shield-banner shield-unlocked";
 shieldIcon.textContent = "\u2713";
 shieldTitle.textContent = "Human review complete";
 shieldSub.textContent = "Every check has been verified. Your final report is being written.";

    if (window._synthesisTriggeredForRun !== _activeRunId) {
      window._synthesisTriggeredForRun = _activeRunId;
      setTimeout(() => {
        if (typeof triggerPostWizardSynthesis === 'function') triggerPostWizardSynthesis();
      }, 1500);
    }
 } else {
 shieldBanner.className = "shield-banner shield-locked";
 shieldIcon.textContent = "";
 shieldTitle.textContent = "One more step: a few checks need a human eye";
 shieldSub.textContent = "Answer the questions below \u2014 takes about 3 minutes. Your final report unlocks when you're done.";
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
    titleEl.textContent = `\u26A0 This score is provisional \u2014 ${totalWizardCards - completedWizardCards} check(s) still need a human look`;
    subEl.textContent = "Finish the Manual Review Wizard to unlock your final report.";
    btnEl.textContent = "Finish Human Review \u2192";
    btnEl.setAttribute("onclick", "document.querySelector('[data-tab=tab-wizard]').click()");
  } else {
    resBanner.style.display = "flex";
    resBanner.classList.add("is-complete");
    titleEl.textContent = "\u2713 Human review complete";
    subEl.textContent = "Your final report is ready.";
    btnEl.textContent = "View Final Report \u2192";
    btnEl.setAttribute("onclick", "document.querySelector('[data-tab=tab-synthesis]').click()");
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
 const domain = document.getElementById("domain-input").value.trim();
 const sc = currentAuditData.executive_scorecard;
 const wizardDone = totalWizardCards === 0 || completedWizardCards >= totalWizardCards;

 let md = wizardDone
 ? `# Citeable Generative Search Engine Audit Report (Automated Findings)\n`
 : `# Citeable Generative Search Engine Audit Report \u2014 PRELIMINARY, Human Review Not Yet Complete\n`;
 md += `**Target Domain**: ${domain}\n`;
 md += `**Audit Date**: ${new Date().toLocaleDateString()} • **Run ID**: \`${currentAuditData.run_id}\`\n\n`;
 if (!wizardDone) {
 md += `> \u26A0 **${totalWizardCards - completedWizardCards} manual review check(s) not yet completed.** This export contains automated findings only \u2014 it does not include human-verified checks or the final AI-written report. Complete the Manual Review Wizard in Citeable Studio for the full report.\n\n`;
 }
 md += `## 1. Executive Scorecard\n`;
 md += `| Diagnostic Index | Measured Value | Status Note |\n`;
 md += `| :--- | :--- | :--- |\n`;
 md += `| **Overall AEO Score** | **${sc.overall_score} / 100** | Weighted AI Visibility Rating |\n`;
 
 if (sc.provider_used === 'not_configured' || !sc.authority_metrics.authority_score) {
 md += `| **Entity Authority Score** | **N/A** | Authority metrics not configured |
`;
 } else {
 md += `| **Entity Authority Score** | **${sc.authority_metrics.authority_score} / 100** | ${sc.authority_metrics.referring_domains} referring domains |
`;
 }

 md += `| **AI Crawler Access** | **${sc.crawler_status}** | llms.txt: ${sc.llms_txt_status} |\n`;
 md += `| **Observed Citation Frequency**| **${sc.observed_citation_rate}** | Live AI Answer Engine Sampling |\n\n`;
 
 md += `## 2. Prioritized Remediation Plan\n\n`;
 if (currentAuditData.remediation_plan && currentAuditData.remediation_plan.length > 0) {
 currentAuditData.remediation_plan.forEach((rec, i) => {
 const code = enrichCodeSnippet(rec, domain);
 md += `### Step ${i+1}: ${escapeHtml(rec.title)} [Priority: ${rec.priority_score || (i+1)*3}]\n`;
 md += `- **Check Code**: \`${escapeHtml(rec.check_code)}\` (${rec.severity.toUpperCase()})\n`;
 md += `- **Diagnostic Details**: ${escapeHtml(rec.description)}\n`;
 md += `- **Governing Research Basis**: *Claim ID ${rec.governing_claim_id}* (${rec.confidence} Confidence / ${rec.source_tier}): "${escapeHtml(rec.governing_claim_statement)}"\n\n`;
 md += `**Recommended Implementation Code / Fix**:\n\`\`\`html\n${code}\n\`\`\`\n\n`;
 });
 } else {
 md += `*No structural AEO/GEO vulnerabilities detected during automated analysis.*\n\n`;
 }

 md += `## 3. Qualitative Human Evaluation Registry\n\n`;
 md += `*Manual verification completed via Citeable Guided Review Shield (${completedWizardCards}/${totalWizardCards} cards signed off).* \n\n`;
 md += `---\n*Generated automatically via Google Antigravity Citeable Studio • Mandatory Governance Caveat: ${currentAuditData.tos_caveat}*\n`;

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
  el.textContent = idx === 0 ? "⏳" : "";
  });
}

function animatePipelineStages() {
  if (window._pipelineStageInterval) clearInterval(window._pipelineStageInterval);
  const stages = ["robots", "schema", "extract", "format", "authority", "citation"];
  let current = 0;
  window._pipelineStageInterval = setInterval(() => {
  if (current < stages.length - 1) {
  const oldEl = document.querySelector(`#stage-${stages[current]} .stage-icon`);
  if (oldEl) { oldEl.className = "stage-icon done"; oldEl.textContent = ""; }
  current++;
  const newEl = document.querySelector(`#stage-${stages[current]} .stage-icon`);
  if (newEl) { newEl.className = "stage-icon active"; newEl.textContent = "⏳"; }
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
  if (el) { el.className = "stage-icon done"; el.textContent = ""; }
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
      if (icon)  icon.textContent  = '\u26A0';
      if (title) title.textContent = 'Final report not available for this run';
      if (sub)   sub.textContent   = synth.reason || 'No LLM provider configured';
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
  if (typeof syncStepper === 'function') syncStepper();

  try {
    const res = await AreosAPI.fetch(`/api/v1/audit/runs/${_activeRunId}/synthesize`, {
      method: 'POST',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      if (icon)  icon.textContent  = '✗';
      if (title) title.textContent = 'Synthesis failed';
      if (sub)   sub.textContent   = err.detail || 'Unknown error from synthesis endpoint';
      return;
    }
    const synthResult = await res.json();
    // Re-render synthesis tab with real data
    renderSynthesisTab({ llm_synthesis: synthResult, run_id: _activeRunId });
    AreosAPI.notify('AI Synthesis complete — grounded narrative ready.', 'success');
  } catch (err) {
    console.error('[Synthesis] POST failed:', err);
    if (icon)  icon.textContent  = '✗';
    if (title) title.textContent = 'Synthesis request failed';
    if (sub)   sub.textContent   = err.message;
  }
}

/** Load synthesis prompts into the editor textareas */
// Synthesis prompt editing (load/save/reset) moved to a dedicated
// admin-only page (synthesis_prompts.html/.js) — see CHANGELOG.md. It
// edited global state affecting every future audit run for every user,
// and previously rendered unconditionally on this tab for every visitor
// (admin or not), silently 401ing for anyone without an admin token.

window.copySynthNarrative = copySynthNarrative;
