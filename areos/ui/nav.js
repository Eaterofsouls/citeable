/**
 * nav.js
 * Centralized navigation for all 7 Citeable pages (Batch B1).
 * LinkedIn x Instagram Light Hybrid Edition — 100% Vector SVG Iconography.
 */

const ROUTES = [
  {
    label: 'Audit Studio',
    path: 'index.html',
    icon: `<svg class="w-4 h-4 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`
  },
  {
    label: 'Knowledge Explorer',
    path: 'knowledge_explorer.html',
    icon: `<svg class="w-4 h-4 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>`
  },
  {
    label: 'Approvals',
    path: 'approvals.html',
    icon: `<svg class="w-4 h-4 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`
  },
  {
    label: 'Documentation',
    path: 'docs.html',
    icon: `<svg class="w-4 h-4 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>`
  },
  {
    label: 'Prompt Design',
    path: 'prompts.html',
    icon: `<svg class="w-4 h-4 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`
  },
  {
    label: 'Synthesis Prompts',
    path: 'synthesis_prompts.html',
    icon: `<svg class="w-4 h-4 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>`
  },
  {
    label: 'Case Study',
    path: 'case_study.html',
    icon: `<svg class="w-4 h-4 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="2" width="16" height="20" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="22"/><line x1="9" y1="7" x2="13" y2="7"/><line x1="9" y1="11" x2="13" y2="11"/></svg>`
  },
];

const paletteHTML = `
<div id="cmdk-modal" class="modal-overlay" style="display:none;">
  <div class="modal-content glass-panel" style="max-width:520px; width:100%; padding:0; overflow:hidden; box-shadow:var(--shadow-xl);">
    <div style="display:flex; align-items:center; padding:0 16px; border-bottom:1px solid var(--border-default); background:var(--surface-panel);">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input type="text" id="cmdk-input" role="searchbox" aria-label="Search claims or navigate to a page" placeholder="Search claims or navigate to..." style="width:100%; padding:16px 12px; border:none; background:transparent; color:var(--text-primary); font-size:1.0rem; outline:none;">
    </div>
    <div id="cmdk-results" role="listbox" aria-label="Results" style="max-height:380px; overflow-y:auto; padding:8px 0; background:var(--surface-panel);"></div>
  </div>
</div>

<div id="admin-auth-modal" class="modal-overlay" style="display:none;">
  <div class="modal-content glass-panel" style="max-width:400px; width:100%; padding:28px; text-align:center; box-shadow:var(--shadow-xl);">
    <div style="width:44px; height:44px; border-radius:50%; background:var(--brand-50); border:1px solid var(--brand-100); color:var(--brand-500); display:flex; align-items:center; justify-content:center; margin:0 auto 16px auto;">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
    </div>
    <h3 style="margin-bottom:8px; color:var(--text-primary); font-weight:800;">Admin Authentication</h3>
    <p style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:18px;">Enter administrative key to access synthesis prompt controls.</p>
    <input type="password" id="admin-auth-input" placeholder="Enter Admin Token" style="width:100%; padding:12px 14px; margin-bottom:16px; border-radius:6px; border:1px solid var(--border-default); background:var(--surface-sunken); color:var(--text-primary); outline:none;">
    <button id="admin-auth-submit" class="btn-primary" style="width:100%;">Authenticate</button>
  </div>
</div>`;

let cmdkDialog = null;

document.addEventListener('DOMContentLoaded', () => {
  document.body.insertAdjacentHTML('beforeend', paletteHTML);

  const cmdkModal = document.getElementById('cmdk-modal');
  const cmdkInput = document.getElementById('cmdk-input');
  const cmdkResults = document.getElementById('cmdk-results');

  if (typeof makeDialogAccessible === 'function') {
    cmdkDialog = makeDialogAccessible(cmdkModal, {
      label: 'Command palette',
      onClose: () => { cmdkModal.style.display = 'none'; cmdkDialog.close(); },
    });
  }

  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'a') {
      e.preventDefault();
      const authModal = document.getElementById('admin-auth-modal');
      authModal.style.display = 'flex';
      document.getElementById('admin-auth-input').focus();
    }
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      if (cmdkModal.style.display === 'flex') {
        if (cmdkDialog) cmdkDialog.close();
        cmdkModal.style.display = 'none';
        return;
      }
      cmdkModal.style.display = 'flex';
      cmdkInput.focus();
      if (cmdkDialog) cmdkDialog.open();
      renderCmdk(cmdkInput.value);
    }
    if (e.key === 'Escape') {
      if (cmdkModal.style.display === 'flex') {
        if (cmdkDialog) cmdkDialog.close();
        cmdkModal.style.display = 'none';
      }
      const authModal = document.getElementById('admin-auth-modal');
      if (authModal && authModal.style.display === 'flex') {
        authModal.style.display = 'none';
      }
    }
  });

  document.getElementById('admin-auth-submit').addEventListener('click', () => {
    const token = document.getElementById('admin-auth-input').value.trim();
    if (token) {
      sessionStorage.setItem('areos_api_token', token);
      window.location.reload();
    }
  });

  document.getElementById('admin-auth-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') document.getElementById('admin-auth-submit').click();
  });

  cmdkModal.addEventListener('click', (e) => {
    if (e.target === cmdkModal) {
      if (cmdkDialog) cmdkDialog.close();
      cmdkModal.style.display = 'none';
    }
  });

  let cmdkTimeout;
  cmdkInput.addEventListener('input', (e) => {
    clearTimeout(cmdkTimeout);
    cmdkTimeout = setTimeout(() => renderCmdk(e.target.value), 300);
  });

  cmdkResults.addEventListener('click', (e) => {
    const target = e.target.closest('.cmdk-item');
    if (target && target.dataset.href) {
      window.location.href = target.dataset.href;
    }
  });
});

async function renderCmdk(query) {
  let html = '';
  const q = query.toLowerCase();

  const matchedRoutes = ROUTES.filter(r => r.label && r.label.toLowerCase().includes(q));
  if (matchedRoutes.length > 0) {
    html += `<div style="padding:6px 16px 4px; font-size:0.75rem; font-weight:700; color:var(--text-tertiary); text-transform:uppercase; letter-spacing:0.06em;">Pages</div>`;
    matchedRoutes.forEach(r => {
      html += `<button type="button" role="option" class="cmdk-item" style="padding:10px 16px; cursor:pointer; display:flex; align-items:center; gap:10px;" data-href="${r.path}">
        <span>${r.icon}</span> <span style="font-weight:600; color:var(--text-primary);">${r.label}</span>
      </button>`;
    });
  }

  if (q.length > 2) {
    html += `<div style="padding:10px 16px 4px; font-size:0.75rem; font-weight:700; color:var(--text-tertiary); text-transform:uppercase; letter-spacing:0.06em;">Knowledge Base</div>`;
    try {
      const res = await fetch(`/api/v1/knowledge?search_query=${encodeURIComponent(q)}&limit=5`);
      if (res.ok) {
        const data = await res.json();
        if (data.records.length === 0) {
          html += `<div style="padding:10px 16px; color:var(--text-tertiary); font-size:0.85rem;">No records found</div>`;
        } else {
          data.records.forEach(c => {
            const safeKid = typeof escapeHtml === 'function' ? escapeHtml(c.kid) : String(c.kid);
            const safeType = typeof escapeHtml === 'function' ? escapeHtml(c.type) : String(c.type);
            const safeStmt = typeof escapeHtml === 'function' ? escapeHtml(c.statement) : String(c.statement);
            const encodedKid = encodeURIComponent(c.kid).replace(/'/g, '%27');
            html += `<button type="button" role="option" class="cmdk-item" style="padding:10px 16px; cursor:pointer;" data-href="knowledge_explorer.html?kid=${encodedKid}">
              <div style="font-size:0.82rem; font-weight:700; color:var(--brand-500);">${safeKid} <span style="font-weight:500; color:var(--text-tertiary);">• ${safeType}</span></div>
              <div style="font-size:0.92rem; color:var(--text-secondary); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-top:2px;">${safeStmt}</div>
            </button>`;
          });
        }
      }
    } catch(e) {}
  }

  cmdkResults.innerHTML = html;

  if (!document.getElementById('cmdk-style')) {
    const style = document.createElement('style');
    style.id = 'cmdk-style';
    style.textContent = `
      .cmdk-item { background: none; border: none; width: 100%; text-align: left; color: var(--text-primary); font-family: inherit; transition: background 0.15s; }
      .cmdk-item:hover, .cmdk-item:focus-visible { background: var(--surface-sunken); outline: none; }
    `;
    document.head.appendChild(style);
  }
}

window.AreosNav = {
  workflowItems: [
    {
      id: "studio",
      label: "Audit Studio",
      href: "index.html",
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`,
      strong: true
    },
    {
      id: "knowledge",
      label: "Knowledge Explorer",
      href: "knowledge_explorer.html",
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>`
    },
    {
      id: "approvals",
      label: "Approvals Queue",
      href: "approvals.html",
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`
    }
  ],
  configItems: [
    {
      id: "docs",
      label: "Documentation",
      href: "docs.html",
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>`
    },
    {
      id: "prompts",
      label: "Prompt Design",
      href: "prompts.html",
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`
    },
    {
      id: "synthesis_prompts",
      label: "Synthesis Prompts",
      href: "synthesis_prompts.html",
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>`
    },
    {
      id: "case_study",
      label: "Case Study",
      href: "case_study.html",
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="2" width="16" height="20" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="22"/><line x1="9" y1="7" x2="13" y2="7"/><line x1="9" y1="11" x2="13" y2="11"/></svg>`
    }
  ],

  
  renderSidebarFooter() {
    const sidebar = document.querySelector(".sidebar");
    if (!sidebar) return;
    
    let footerEl = document.getElementById("sidebar-footer");
    if (!footerEl) {
      footerEl = document.createElement("div");
      footerEl.id = "sidebar-footer";
      footerEl.className = "sidebar-footer";
      sidebar.appendChild(footerEl);
    }

    let keyCount = 0;
    try {
      const vault = JSON.parse(localStorage.getItem("areos_byok_vault") || "{}");
      keyCount = Object.keys(vault).length;
    } catch (_) {}

    const countLabel = keyCount > 0 ? `${keyCount} Live` : "BYOK";
    const pillClass = keyCount > 0 ? "status-pill success text-xs" : "status-pill text-xs";

    footerEl.innerHTML = `
      <button type="button" id="sidebar-byok-card" class="byok-sidebar-card" onclick="if (window.BYOKVault) { window.BYOKVault.open(); } else { alert('BYOK Vault loading...'); }">
        <div class="byok-card-top">
          <div class="byok-card-title-wrap">
            <div class="byok-icon-box">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2l-2 2m-1.5 1.5L14 9M3 21l7-7m0 0l2 2m-2-2l-2-2m7-7a5 5 0 11-7 7 5 5 0 017-7z"/></svg>
            </div>
            <span class="byok-card-title">AI Key Vault</span>
          </div>
          <span class="${pillClass}">${countLabel}</span>
        </div>
        <div class="byok-card-sub">Client-side ephemeral vault</div>
      </button>
    `;
  },

  renderNav(activeId) {
    if (!document.querySelector('script[src*="byok.js"]')) {
      const byokScript = document.createElement('script');
      byokScript.src = 'byok.js';
      document.head.appendChild(byokScript);
    }

    const navEl = document.getElementById("main-nav");
    if (!navEl) return;
    
    let html = "";
    const runId = window.AreosContext?.activeRunId;
    const qp = runId ? `?run_id=${encodeURIComponent(runId)}` : "";

    const adminIds = ["approvals", "prompts", "case_study", "synthesis_prompts"];
    const hasToken = !!sessionStorage.getItem('areos_api_token');
    
    const aliases = {
      "knowledge_explorer": "knowledge",
      "claims_browser": "knowledge",
      "index": "studio"
    };
    const currentActiveId = aliases[activeId] || activeId;

    for (const item of this.workflowItems) {
      if (adminIds.includes(item.id) && !hasToken) continue;
      const isActive = (item.id === currentActiveId || item.id === activeId) ? "active" : "";
      const content = item.strong ? `<strong>${item.label}</strong>` : item.label;
      html += `
        <a href="${item.href}${qp}" class="nav-item ${isActive}">
          ${item.icon}
          <span>${content}</span>
        </a>
      `;
    }

    
    for (const item of this.configItems) {
      if (adminIds.includes(item.id) && !hasToken) continue;
      const isActive = item.id === activeId ? "active" : "";
      const hrefAttr = item.id === "byok" ? 'href="javascript:void(0);"' : `href="${item.href}${qp}"`;
      const customStyle = item.id === "byok" ? 'border: 1px solid var(--brand-500); margin: 12px 4px 4px 4px; border-radius: 8px; font-weight: 700; background: var(--brand-50); color: var(--brand-500);' : '';
      const clickAttr = item.id === "byok" ? 'onclick="if (window.BYOKVault) { window.BYOKVault.open(); } else { alert(\'BYOK Vault loading...\'); } return false;"' : '';
      html += `
        <a ${hrefAttr} ${clickAttr} data-nav-id="${item.id}" class="nav-item ${isActive}" style="${customStyle}">
          ${item.icon}
          <span>${item.label}</span>
        </a>
      `;
    }
    
    navEl.innerHTML = html;
    this.renderSidebarFooter();


    const topbar = document.querySelector(".topbar");

    if (!document.getElementById("mobile-menu-btn")) {
      const hamburgerHtml = `
        <button id="mobile-menu-btn" aria-label="Toggle navigation menu" style="display:none; background:none; border:none; color:var(--text-primary); cursor:pointer; padding:8px 8px 8px 0; margin-right:8px; align-self:center;">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
        </button>
      `;
      if (topbar) {
        topbar.insertAdjacentHTML('afterbegin', hamburgerHtml);
      } else {
        const mainContent = document.querySelector('.main-content');
        if (mainContent) {
          mainContent.insertAdjacentHTML('afterbegin', hamburgerHtml);
        }
      }

      let backdrop = document.getElementById("sidebar-backdrop");
      if (!backdrop) {
        backdrop = document.createElement("div");
        backdrop.id = "sidebar-backdrop";
        backdrop.className = "sidebar-backdrop";
        document.body.appendChild(backdrop);
        backdrop.addEventListener("click", () => {
          const s = document.querySelector('.sidebar');
          if (s) s.classList.remove('open');
          backdrop.classList.remove('open');
        });
      }

      const btn = document.getElementById("mobile-menu-btn");
      if (btn) {
        btn.addEventListener('click', () => {
          const s = document.querySelector('.sidebar');
          if (s) {
            const isOpen = s.classList.toggle('open');
            if (backdrop) backdrop.classList.toggle('open', isOpen);
          }
        });
      }
    }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  const pageId = document.body.dataset.navId || window.location.pathname.split('/').pop().replace('.html', '') || 'studio';
  if (typeof window.AreosNav.renderNav === 'function') {
    window.AreosNav.renderNav(pageId);
  }
});
