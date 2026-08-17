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

document.addEventListener('DOMContentLoaded', () => {
  checkAdminAccessAndLoad();

  // Re-check if the person authenticates via the global Ctrl/Cmd+Shift+A
  // modal while already on this page (that flow reloads the page, but
  // this covers it defensively either way).
  const authSubmit = document.getElementById('admin-auth-submit');
  if (authSubmit) {
    authSubmit.addEventListener('click', () => {
      setTimeout(checkAdminAccessAndLoad, 100);
    });
  }
});

function checkAdminAccessAndLoad() {
  const gate = document.getElementById('prompts-auth-gate');
  const invalid = document.getElementById('prompts-auth-invalid');
  const editorArea = document.getElementById('prompt-editor-area');
  const hasToken = typeof getToken === 'function' && !!getToken();

  if (!hasToken) {
    if (gate) gate.style.display = 'block';
    if (invalid) invalid.style.display = 'none';
    if (editorArea) editorArea.style.display = 'none';
    return;
  }

  if (gate) gate.style.display = 'none';
  loadSynthesisPrompts();
}

/** Load synthesis prompts into the editor textareas. */
async function loadSynthesisPrompts() {
  const gate = document.getElementById('prompts-auth-gate');
  const invalid = document.getElementById('prompts-auth-invalid');
  const editorArea = document.getElementById('prompt-editor-area');

  try {
    const res = await AreosAPI.fetch('/api/v1/synthesis/prompts', {
      headers: getAuthHeaders({})
    });

    if (res.status === 401 || res.status === 403) {
      // A token is present but the server rejected it — distinct from "no
      // token at all" so the person knows to re-authenticate, not that
      // the page is broken.
      if (invalid) invalid.style.display = 'flex';
      if (editorArea) editorArea.style.display = 'none';
      if (gate) gate.style.display = 'none';
      return;
    }
    if (!res.ok) {
      AreosAPI.notify(`Could not load prompts: HTTP ${res.status}`);
      return;
    }

    if (invalid) invalid.style.display = 'none';
    if (editorArea) editorArea.style.display = 'flex';

    const data = await res.json();
    (data.prompts || []).forEach(p => {
      const ta = document.getElementById(`prompt-${p.step}`);
      if (ta) ta.value = p.system_prompt;
    });
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
