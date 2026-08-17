/**
 * identity.js
 * Manages analyst identity. Prompts on first launch, then persists to localStorage.
 * Once set, the modal is never shown again unless localStorage is cleared.
 */

document.addEventListener("DOMContentLoaded", () => {
  const STORAGE_KEY = "areos_analyst_id";
  const DEFAULT_ID  = "Analyst";

  // UX fix: the Claims Browser is read-only research browsing — it doesn't
  // log any action under an identity, so don't gate it behind this prompt.
  // Studio (manual review, verdicts, outcome logging) still requires it.
  const path = window.location.pathname.split("/").pop();
  if (path === "claims_browser.html") return;

  // Restore from localStorage first — avoids modal on every page reload
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored && stored.trim()) {
    window.AreosContext.analystId = stored.trim();
    return; // already identified, skip modal entirely
  }

  // Also honour a pre-set context value (e.g. injected by automated tools)
  let analystId = window.AreosContext?.analystId;
  if (analystId) {
    localStorage.setItem(STORAGE_KEY, analystId);
    return;
  }

  // Build modal UI
  const overlay = document.createElement("div");
  overlay.id = "identity-overlay";
  overlay.style.cssText = "position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.8);z-index:9999;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px);";

  const modal = document.createElement("div");
  modal.className = "glass-panel";
  modal.style.cssText = "padding:32px;background:#1e293b;border-radius:12px;text-align:center;max-width:400px;width:100%;border:1px solid #334155;box-shadow:0 25px 50px -12px rgba(0,0,0,0.5);";

  const h2 = document.createElement("h2");
  h2.textContent = "Welcome to Citeable";
  h2.style.cssText = "margin-top:0;color:#f8fafc;font-weight:600;";

  const p = document.createElement("p");
  p.textContent = "Enter your Analyst ID or name. All manual review actions are logged under this identity.";
  p.style.cssText = "color:#94a3b8;font-size:14px;margin-bottom:24px;";

  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = "e.g., A-742 or Alice S.";
  input.autocomplete = "name";
  input.style.cssText = "width:100%;padding:12px;background:#0f172a;border:1px solid #475569;border-radius:8px;color:#f8fafc;font-size:16px;margin-bottom:16px;box-sizing:border-box;outline:none;";

  const btn = document.createElement("button");
  btn.textContent = "Continue";
  btn.className = "btn-primary";
  btn.style.cssText = "width:100%;padding:12px;font-size:16px;background:#6366f1;color:white;border:none;border-radius:8px;cursor:pointer;font-weight:500;transition:opacity 0.2s;margin-bottom:12px;";

  // Skip link — sets a default ID so automated tools and first-time users
  // can dismiss without friction.
  const skip = document.createElement("a");
  skip.textContent = "Skip for now (use default identity)";
  skip.href = "#";
  skip.style.cssText = "display:block;color:#64748b;font-size:12px;text-decoration:none;cursor:pointer;margin-top:4px;";
  skip.onmouseover = () => { skip.style.color = "#94a3b8"; };
  skip.onmouseout  = () => { skip.style.color = "#64748b"; };

  const dismiss = (id) => {
    const val = (id || input.value.trim() || DEFAULT_ID);
    window.AreosContext.analystId = val;
    localStorage.setItem(STORAGE_KEY, val);
    document.body.removeChild(overlay);
  };

  const commit = () => {
    const val = input.value.trim();
    if (!val) {
      input.style.borderColor = "#ef4444";
      input.focus();
      return;
    }
    dismiss(val);
  };

  skip.onclick = (e) => { e.preventDefault(); dismiss(DEFAULT_ID); };
  btn.onclick = commit;
  btn.onmouseenter = () => { btn.style.opacity = "0.85"; };
  btn.onmouseleave = () => { btn.style.opacity = "1"; };

  input.onkeydown = (e) => {
    if (e.key === "Enter") commit();
    if (input.style.borderColor === "rgb(239, 68, 68)") {
      input.style.borderColor = "#475569";
    }
  };

  modal.appendChild(h2);
  modal.appendChild(p);
  modal.appendChild(input);
  modal.appendChild(btn);
  modal.appendChild(skip);
  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  // Small delay so page renders first, then focus
  setTimeout(() => input.focus(), 80);

  // Auto-dismiss after 6 s with whatever the user has typed (or default).
  // This ensures new visitors are never permanently blocked by the overlay.
  let _autoDismissTimer = setTimeout(() => {
    if (document.getElementById("identity-overlay")) {
      dismiss(input.value.trim() || DEFAULT_ID);
    }
  }, 6000);

  // If the user actively interacts, cancel the auto-timer so they can type freely.
  input.addEventListener("input", () => {
    clearTimeout(_autoDismissTimer);
    _autoDismissTimer = null;
  });
});
