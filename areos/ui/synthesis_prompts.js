// synthesis_prompts.js — Admin-only editor for the three-step AI synthesis
// pipeline's system prompts (Synthesizer / Red Teamer / Grounder).
//
// Moved out of studio.js / index.html per UX audit: this used to render
// unconditionally on the Studio "AI Synthesis" tab — the same screen a
// client might be viewing their finished report on — and silently 401'd
// for any visitor without an admin token, leaving permanently blank
// textareas with no explanation. It's also global state: saving here
// changes the AI's behavior for every future audit run, for every user,
// not just the person editing it. Both problems are why this now lives on
// its own admin-gated page with an explicit warning, instead of embedded
// in the report-viewing flow.

const STEP_LABELS = {
  synthesizer: {
    title: "1. Synthesizer System Prompt",
    badge: "Synthesis Lead",
    desc: "Drafts the executive summary and ranked technical findings from raw automated telemetry and human review verdicts."
  },
  red_teamer: {
    title: "2. Adversarial Red-Teamer System Prompt",
    badge: "Adversarial QA",
    desc: "Audits the draft narrative for hallucinations, unsupported claims, or ungrounded assertions before report generation."
  },
  grounder: {
    title: "3. Grounder & Citation System Prompt",
    badge: "Verification Gating",
    desc: "Calibrates findings against the empirical knowledge graph and produces final markdown citations and remediation steps."
  }
};

document.addEventListener('DOMContentLoaded', () => {
  checkAdminAccessAndLoad();

  const authSubmit = document.getElementById('admin-auth-submit');
  if (authSubmit) {
    authSubmit.addEventListener('click', () => {
      setTimeout(checkAdminAccessAndLoad, 100);
    });
  }
});

function checkAdminAccessAndLoad() {
  const gate = document.getElementById('prompts-auth-gate');
  const gateTitle = document.getElementById('prompts-gate-title');
  const gateDesc = document.getElementById('prompts-gate-desc');
  const editorArea = document.getElementById('prompts-editor-container');
  const hasToken = typeof getToken === 'function' && !!getToken();

  if (!hasToken) {
    if (gateTitle) gateTitle.textContent = "Admin Authentication Required";
    if (gateDesc) gateDesc.textContent = "Viewing and editing global synthesis prompts requires an active administrator token. Authenticate to manage pipeline instructions.";
    if (gate) gate.style.display = 'block';
    if (editorArea) editorArea.style.display = 'none';
    return;
  }

  if (gate) gate.style.display = 'none';
  loadSynthesisPrompts();
}

/** Load synthesis prompts into the editor textareas. */
async function loadSynthesisPrompts() {
  const gate = document.getElementById('prompts-auth-gate');
  const gateTitle = document.getElementById('prompts-gate-title');
  const gateDesc = document.getElementById('prompts-gate-desc');
  const editorArea = document.getElementById('prompts-editor-container');

  try {
    const res = await AreosAPI.fetch('/api/v1/synthesis/prompts', {
      headers: getAuthHeaders({})
    });

    if (res.status === 401 || res.status === 403) {
      if (gateTitle) gateTitle.textContent = "Admin Token Invalid or Expired";
      if (gateDesc) gateDesc.textContent = "Your admin token was rejected by the server (HTTP " + res.status + "). Please authenticate with a valid administrator token.";
      if (gate) gate.style.display = 'block';
      if (editorArea) editorArea.style.display = 'none';
      return;
    }
    if (!res.ok) {
      AreosAPI.notify(`Could not load prompts: HTTP ${res.status}`);
      return;
    }

    if (gate) gate.style.display = 'none';
    if (editorArea) editorArea.style.display = 'flex';

    const data = await res.json();
    const prompts = data.prompts || [];

    let editorHtml = '';
    prompts.forEach(p => {
      const meta = STEP_LABELS[p.step] || {
        title: `${p.step.toUpperCase()} Prompt`,
        badge: "Pipeline Step",
        desc: "Global system prompt for this synthesis pipeline step."
      };
      const updatedStr = p.updated_at ? `Updated: ${p.updated_at} (${p.updated_by || 'system'})` : 'Default system configuration';

      editorHtml += `
        <div class="card" style="padding:24px; background:var(--surface-card); border:1px solid var(--border-default); border-radius:8px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; flex-wrap:wrap; gap:8px;">
            <div>
              <div style="display:flex; align-items:center; gap:8px;">
                <h3 style="margin:0; font-size:1.05rem; font-weight:700; color:var(--text-primary);">${meta.title}</h3>
                <span class="status-pill info text-xs">${meta.badge}</span>
              </div>
              <p style="margin:4px 0 0; font-size:0.8125rem; color:var(--text-secondary); line-height:1.5;">${meta.desc}</p>
            </div>
            <span style="font-family:var(--font-mono); font-size:0.75rem; color:var(--text-tertiary);">${updatedStr}</span>
          </div>

          <textarea id="prompt-${p.step}" class="input" rows="8" style="width:100%; font-family:var(--font-mono); font-size:0.85rem; padding:12px; border-radius:6px; resize:vertical; line-height:1.5; background:var(--surface-sunken); color:var(--text-primary); border:1px solid var(--border-default); margin-bottom:16px;">${(p.system_prompt || '').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</textarea>

          <div style="display:flex; justify-content:flex-end; gap:10px; align-items:center;">
            <button type="button" class="btn-secondary" onclick="window.resetPrompt('${p.step}')" style="font-size:0.82rem; font-weight:600; padding:6px 14px;">Reset to Default</button>
            <button type="button" class="btn-primary" onclick="window.savePrompt('${p.step}')" style="font-size:0.82rem; font-weight:700; padding:6px 16px;">Save Prompt Changes</button>
          </div>
        </div>
      `;
    });

    editorArea.innerHTML = editorHtml;
  } catch (e) {
    console.warn('Could not load synthesis prompts:', e);
    AreosAPI.notify('Network error loading prompts: ' + e.message);
  }
}

/** Save a prompt step to the API. */
async function savePrompt(step) {
  const ta = document.getElementById(`prompt-${step}`);
  if (!ta || !ta.value.trim()) return AreosAPI.notify('Prompt cannot be empty.');
  try {
    const res = await AreosAPI.fetch(`/api/v1/synthesis/prompts/${step}`, {
      method: 'PUT',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ system_prompt: ta.value.trim() })
    });
    if (res.ok) {
      AreosAPI.notify(`${step} prompt saved — this now affects every future audit run.`);
    } else if (res.status === 401 || res.status === 403) {
      AreosAPI.notify('Your admin token was rejected. Re-authenticate and try again.');
      checkAdminAccessAndLoad();
    } else {
      AreosAPI.notify(`Save failed for ${step}: HTTP ${res.status}`);
    }
  } catch (e) {
    AreosAPI.notify('Network error saving prompt: ' + e.message);
  }
}

/** Reset a prompt to its server-side default. */
async function resetPrompt(step) {
  try {
    const res = await AreosAPI.fetch(`/api/v1/synthesis/prompts/reset/${step}`, {
      method: 'POST',
      headers: getAuthHeaders({})
    });
    if (res.ok) {
      AreosAPI.notify(`${step} prompt reset to default.`);
      await loadSynthesisPrompts();
    } else if (res.status === 401 || res.status === 403) {
      AreosAPI.notify('Your admin token was rejected. Re-authenticate and try again.');
      checkAdminAccessAndLoad();
    } else {
      AreosAPI.notify(`Reset failed: HTTP ${res.status}`);
    }
  } catch (e) {
    AreosAPI.notify('Network error resetting prompt: ' + e.message);
  }
}

window.savePrompt = savePrompt;
window.resetPrompt = resetPrompt;
