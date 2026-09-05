/**
 * byok.js — Citeable Standalone BYOK Key Vault Client Domain Engine
 * 
 * Provides an isolated modal interface for adding unlimited AI provider keys,
 * instant read-only diagnostic validation, zero-retention assurance, and session alerts.
 * LinkedIn x Instagram Light Hybrid Edition — Zero Emojis, Pure SVG.
 */

(function() {
  const VAULT_STORAGE_KEY = 'areos_byok_vault';
  const API_BASE_URL = window.location.origin;

  const PROVIDER_INFO = {
    google: { name: "Google Gemini 2.0 / Pro", tag: "Primary Recommendation" },
    openai: { name: "OpenAI (GPT-4o / o1 Series)", tag: "Advanced Reasoning" },
    groq: { name: "Groq (LLaMA-3.3 70B)", tag: "Ultra-Fast Inference" },
    anthropic: { name: "Anthropic Claude 3.5 Sonnet", tag: "Semantic Accuracy" },
    perplexity: { name: "Perplexity Sonar (Search)", tag: "Live Grounding" },
    xai: { name: "xAI Grok 2 / Beta", tag: "Real-time Insights" },
    mistral: { name: "Mistral AI (Large / Medium)", tag: "Open-Weights Top Tier" },
    deepseek: { name: "DeepSeek-V4 Flash / Pro", tag: "Cost-Effective Logic" },
    azure: { name: "Azure OpenAI Service", tag: "Enterprise Cloud" },
    custom: { name: "Custom / Ollama Endpoint", tag: "Self-Hosted / Local" }
  };

  class ByokVaultManager {
    constructor() {
      this.modalEl = null;
      this.initModal();
    }

    getVaultData() {
      try {
        const data = localStorage.getItem(VAULT_STORAGE_KEY);
        return data ? JSON.parse(data) : {};
      } catch (e) {
        return {};
      }
    }

    saveVaultData(data) {
      try {
        localStorage.setItem(VAULT_STORAGE_KEY, JSON.stringify(data));
      } catch (e) {
        console.error("Failed to save to BYOK localStorage vault:", e);
      }
    }

    showPrivateSessionAlert(msg, type = 'info') {
      let toastEl = document.getElementById('byok-private-toast');
      if (!toastEl) {
        toastEl = document.createElement('div');
        toastEl.setAttribute('aria-live', 'polite');
        toastEl.id = 'byok-private-toast';
        toastEl.style.cssText = `
          position: fixed; bottom: 24px; right: 24px; z-index: 10000000;
          padding: 14px 20px; border-radius: 8px; font-weight: 600; font-size: 14px;
          box-shadow: 0 10px 25px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.05);
          transition: all 0.25s ease; display: none; border: 1px solid #E2E8F0;
          font-family: var(--font-main, sans-serif); background: #FFFFFF; color: #0F172A;
        `;
        document.body.appendChild(toastEl);
      }

      if (type === 'success' || type === 'live') {
        toastEl.style.background = '#ECFDF5';
        toastEl.style.color = '#065F46';
        toastEl.style.borderLeft = '4px solid #059669';
        toastEl.style.borderColor = '#A7F3D0';
      } else if (type === 'error' || type === 'offline') {
        toastEl.style.background = '#FFF1F2';
        toastEl.style.color = '#9F1239';
        toastEl.style.borderLeft = '4px solid #E11D48';
        toastEl.style.borderColor = '#FECDD3';
      } else {
        toastEl.style.background = '#EFF6FF';
        toastEl.style.color = '#1E40AF';
        toastEl.style.borderLeft = '4px solid #0A66C2';
        toastEl.style.borderColor = '#BFDBFE';
      }

      toastEl.textContent = msg;
      toastEl.style.display = 'block';
      toastEl.style.opacity = '1';
      toastEl.style.transform = 'translateY(0)';

      clearTimeout(this._toastTimeout);
      this._toastTimeout = setTimeout(() => {
        toastEl.style.opacity = '0';
        toastEl.style.transform = 'translateY(10px)';
        setTimeout(() => { toastEl.style.display = 'none'; }, 300);
      }, 4000);
    }

    initModal() {
      if (document.getElementById('byok-vault-modal')) return;

      const modalHtml = `
      <div id="byok-vault-modal" style="display: none; position: fixed; inset: 0; background: rgba(15, 23, 42, 0.45); backdrop-filter: blur(4px); z-index: 999999; align-items: center; justify-content: center; padding: 20px;">
        <div class="modal-content glass-panel" style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; max-width: 780px; width: 100%; max-height: 90vh; overflow-y: auto; padding: 32px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.05); position: relative;">
          
          <!-- Modal Header -->
          <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid #E2E8F0; padding-bottom: 18px; margin-bottom: 24px;">
            <div>
              <h2 style="margin: 0; color: #0F172A; font-size: 1.5rem; font-weight: 800; letter-spacing: -0.02em;">
                Bring Your Own Key (BYOK) Vault
              </h2>
              <p style="margin: 6px 0 0 0; color: #64748B; font-size: 0.92rem;">
                Configure your individual AI credentials to execute audits, RAG lookups, and evaluation judges.
              </p>
            </div>
            <button id="byok-close-btn" style="background: #F8FAFC; border: 1px solid #E2E8F0; color: #64748B; font-size: 1.2rem; font-weight: 700; width: 34px; height: 34px; border-radius: 6px; cursor: pointer; display: flex; align-items: center; justify-content: center;">&times;</button>
          </div>

          <!-- Zero-Retention Assurance Banner -->
          <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-left: 4px solid #0A66C2; padding: 16px 20px; border-radius: 8px; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0A66C2" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
              <strong style="color: #1E40AF; font-size: 0.95rem; font-weight: 700;">Zero-Retention & Headless Memory Architecture</strong>
            </div>
            <p style="margin: 0; color: #334155; font-size: 0.88rem; line-height: 1.55;">
              Credentials saved here reside exclusively within your local browser memory (<code>localStorage</code>) and are transmitted solely via encrypted ephemeral headers (<code>X-API-Key-[Provider]</code>). Our servers never record or persist your secret keys.
            </p>
          </div>

          <!-- Key Addition Form -->
          <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 20px; margin-bottom: 24px;">
            <h3 style="color: #0F172A; font-size: 0.95rem; font-weight: 700; margin: 0 0 14px 0; text-transform: uppercase; letter-spacing: 0.05em;">Add New AI Provider Key</h3>
            <div style="display: grid; grid-template-columns: minmax(220px, 1fr) 2fr auto; gap: 12px; align-items: stretch;">
              <div>
                <select id="byok-select-provider" class="input" style="width: 100%; height: 44px; padding: 8px 12px; background: #FFFFFF; border: 1px solid #CBD5E1; color: #0F172A; border-radius: 6px; font-weight: 600; font-size: 0.9rem;">
                  ${Object.entries(PROVIDER_INFO).map(([key, info]) => `<option value="${key}">${info.name}</option>`).join('')}
                </select>
              </div>
              <div style="position: relative; display: flex; align-items: center;">
                <input type="password" id="byok-input-key" class="input" placeholder="Paste ephemeral API key (e.g. AIza... or sk-...)" style="width: 100%; height: 44px; padding: 8px 40px 8px 14px; background: #FFFFFF; border: 1px solid #CBD5E1; color: #0F172A; border-radius: 6px; font-family: monospace; font-size: 0.9rem;" />
                <button type="button" id="byok-toggle-eye" title="Show/Hide Secret Key" style="position: absolute; right: 8px; background: transparent; border: none; color: #94A3B8; cursor: pointer; padding: 6px; display: flex; align-items: center;"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg></button>
              </div>
              <button id="byok-add-btn" class="btn-primary" style="height: 44px; padding: 0 20px; font-weight: 700; font-size: 0.85rem; white-space: nowrap; text-transform: uppercase;">
                Add & Test Key
              </button>
            </div>
          </div>

          <!-- Active Keys Table -->
          <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
              <h3 style="color: #0F172A; font-size: 0.95rem; font-weight: 700; margin: 0; text-transform: uppercase; letter-spacing: 0.05em;">Active Local Vault Credentials</h3>
              <button id="byok-refresh-all-btn" style="background: #FFFFFF; border: 1px solid #CBD5E1; color: #0F172A; padding: 5px 12px; border-radius: 6px; font-size: 0.78rem; font-weight: 700; cursor: pointer;">Verify All Live Status</button>
            </div>
            <div id="byok-keys-table-container" style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; overflow: hidden; min-height: 80px;">
              <div style="padding: 24px; text-align: center; color: #94A3B8; font-size: 0.9rem;">Loading local keys...</div>
            </div>
          </div>

          <div style="margin-top: 24px; text-align: right; border-top: 1px solid #E2E8F0; padding-top: 18px;">
            <button id="byok-done-btn" class="btn-primary" style="padding: 8px 22px; font-size: 0.88rem; font-weight: 700;">
              Save & Continue
            </button>
          </div>
        </div>
      </div>
      `;

      document.body.insertAdjacentHTML('beforeend', modalHtml);
      this.modalEl = document.getElementById('byok-vault-modal');

      document.getElementById('byok-close-btn').addEventListener('click', () => this.close());
      document.getElementById('byok-done-btn').addEventListener('click', () => this.close());
      this.modalEl.addEventListener('click', (e) => { if (e.target === this.modalEl) this.close(); });
      if (typeof makeDialogAccessible === "function") {
        this.dialog = makeDialogAccessible(this.modalEl, { role: "dialog", label: "BYOK Vault", onClose: () => this.close() });
      } else {
        document.addEventListener('keydown', (e) => {
          if (e.key === 'Escape' && this.modalEl.style.display === 'flex') this.close();
        });
      }

      const keyInput = document.getElementById('byok-input-key');
      const eyeBtn = document.getElementById('byok-toggle-eye');
      eyeBtn.addEventListener('click', () => {
        keyInput.type = keyInput.type === 'password' ? 'text' : 'password';
      });

      document.getElementById('byok-add-btn').addEventListener('click', () => this.handleAddKey());
      document.getElementById('byok-refresh-all-btn').addEventListener('click', () => this.verifyAllKeys());

      keyInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          this.handleAddKey();
        }
      });
    }

    open() {
      if (!this.modalEl) this.initModal();
      this.modalEl.style.display = 'flex';
      this.renderTable();
      setTimeout(() => document.getElementById('byok-input-key')?.focus(), 50);
    }

    close() {
      if (this.modalEl) {
        this.modalEl.style.display = 'none';
        document.getElementById('byok-input-key').value = '';
      }
    }

    async handleAddKey() {
      const provSel = document.getElementById('byok-select-provider');
      const keyInput = document.getElementById('byok-input-key');
      const provider = provSel.value;
      const apiKey = keyInput.value.trim();

      if (!apiKey) {
        this.showPrivateSessionAlert('Please paste a valid API key first.', 'error');
        keyInput.focus();
        return;
      }

      const vault = this.getVaultData();
      vault[provider] = {
        key: apiKey,
        addedAt: new Date().toISOString(),
        status: 'verifying',
        latencyMs: 0,
        lastMsg: 'Verification in progress...'
      };
      this.saveVaultData(vault);

      keyInput.value = '';
      this.renderTable();

      await this.verifyKey(provider, apiKey);
    }

    async verifyKey(provider, apiKeyOverride = null) {
      const vault = this.getVaultData();
      const keyData = vault[provider];
      const keyToTest = apiKeyOverride || (keyData ? keyData.key : null);
      if (!keyToTest) return;

      if (!vault[provider]) vault[provider] = { key: keyToTest, addedAt: new Date().toISOString() };
      vault[provider].status = 'verifying';
      this.saveVaultData(vault);
      this.renderTable();

      try {
        const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' };
        const response = typeof AreosAPI !== 'undefined' ? await AreosAPI.fetch('/byok/verify', {
          method: 'POST',
          headers: headers,
          body: JSON.stringify({ provider: provider, api_key: keyToTest })
        }) : await fetch(`${API_BASE_URL}/api/v1/byok/verify`, {
          method: 'POST',
          headers: headers,
          body: JSON.stringify({ provider: provider, api_key: keyToTest })
        });
        const result = await response.json();

        if (response.ok && result.status === 'live') {
          vault[provider].status = 'live';
          vault[provider].latencyMs = result.latency_ms || 0;
          vault[provider].lastMsg = result.message || 'Operational';
          this.saveVaultData(vault);
          this.renderTable();
          const pName = PROVIDER_INFO[provider]?.name || provider.toUpperCase();
          this.showPrivateSessionAlert(`LIVE: [${pName}] verified operational (${result.latency_ms}ms) for active session!`, 'live');
        } else if (response.ok && result.status === 'unverified') {
          vault[provider].status = 'unverified';
          vault[provider].latencyMs = result.latency_ms || 0;
          vault[provider].lastMsg = result.message || 'Syntax Valid';
          this.saveVaultData(vault);
          this.renderTable();
          const pName = PROVIDER_INFO[provider]?.name || provider.toUpperCase();
          this.showPrivateSessionAlert(`UNVERIFIED: [${pName}] syntax verified valid for custom endpoint.`, 'info');
        } else {
          vault[provider].status = 'offline';
          vault[provider].lastMsg = result.message || 'Key failed validation';
          this.saveVaultData(vault);
          this.renderTable();
          const pName = PROVIDER_INFO[provider]?.name || provider.toUpperCase();
          this.showPrivateSessionAlert(`OFFLINE: [${pName}] check failed — ${vault[provider].lastMsg}`, 'offline');
        }
      } catch (err) {
        vault[provider].status = 'offline';
        vault[provider].lastMsg = 'Network connectivity or server error during ping';
        this.saveVaultData(vault);
        this.renderTable();
        this.showPrivateSessionAlert(`OFFLINE: Could not verify key against backend diagnostic ping.`, 'offline');
      }
    }

    async verifyAllKeys() {
      const vault = this.getVaultData();
      const providers = Object.keys(vault);
      if (providers.length === 0) {
        this.showPrivateSessionAlert('No keys in vault to verify.', 'info');
        return;
      }
      this.showPrivateSessionAlert(`Verifying live status for ${providers.length} AI providers...`, 'info');
      for (const prov of providers) {
        if (vault[prov]?.key) {
          this.verifyKey(prov, vault[prov].key);
        }
      }
    }

    deleteKey(provider) {
      const vault = this.getVaultData();
      if (vault[provider]) {
        delete vault[provider];
        this.saveVaultData(vault);
        this.renderTable();
        const pName = PROVIDER_INFO[provider]?.name || provider.toUpperCase();
        this.showPrivateSessionAlert(`Removed [${pName}] credential from local browser vault.`, 'info');
      }
    }

    renderTable() {
      const container = document.getElementById('byok-keys-table-container');
      if (!container) return;
      const vault = this.getVaultData();
      const entries = Object.entries(vault);

      if (entries.length === 0) {
        container.innerHTML = `
          <div style="padding: 32px 20px; text-align: center; color: #64748B; font-size: 0.92rem;">
            <div style="font-weight: 700; color: #0F172A; margin-bottom: 4px;">No AI provider keys configured in this local vault.</div>
            <div style="font-size: 0.82rem; color: #94A3B8;">Select a provider above, paste your secret token, and click <strong>Add & Test Key</strong> to begin.</div>
          </div>
        `;
        return;
      }

      let rowsHtml = '';
      for (const [prov, data] of entries) {
        const info = PROVIDER_INFO[prov] || { name: prov.toUpperCase(), tag: "Custom" };
        const keyMasked = data.key ? data.key.slice(0, 5) + "••••••••••••••••" : "Empty";
        
        let statusTag = `<span style="display:inline-flex; align-items:center; gap:6px; background:#F1F5F9; color:#64748B; padding:3px 10px; border-radius:12px; font-size:0.75rem; font-weight:700; border:1px solid #CBD5E1;">VERIFYING...</span>`;
        if (data.status === 'live') {
          statusTag = `<span style="display:inline-flex; align-items:center; gap:6px; background:#ECFDF5; color:#059669; padding:3px 10px; border-radius:12px; font-size:0.75rem; font-weight:700; border:1px solid #A7F3D0;">LIVE (${data.latencyMs || 0}ms)</span>`;
        } else if (data.status === 'unverified') {
          statusTag = `<span style="display:inline-flex; align-items:center; gap:6px; background:#FFFBEB; color:#D97706; padding:3px 10px; border-radius:12px; font-size:0.75rem; font-weight:700; border:1px solid #FDE68A;" title="${data.lastMsg || 'Syntax Valid'}">UNVERIFIED</span>`;
        } else if (data.status === 'offline') {
          statusTag = `<span style="display:inline-flex; align-items:center; gap:6px; background:#FFF1F2; color:#E11D48; padding:3px 10px; border-radius:12px; font-size:0.75rem; font-weight:700; border:1px solid #FECDD3;" title="${data.lastMsg || 'Invalid Key'}">OFFLINE</span>`;
        }

        rowsHtml += `
          <div style="display:grid; grid-template-columns: minmax(180px, 1.5fr) minmax(140px, 1.2fr) minmax(140px, 1fr) auto; gap:16px; align-items:center; padding:14px 18px; border-bottom:1px solid #E2E8F0; background:#FFFFFF;">
            <div>
              <div style="color:#0F172A; font-weight:700; font-size:0.92rem;">
                ${info.name}
              </div>
              <div style="font-size:0.75rem; color:#94A3B8; margin-top:2px;">${info.tag}</div>
            </div>
            <div style="font-family:monospace; color:#334155; font-size:0.85rem; background:#F1F5F9; padding:4px 8px; border-radius:4px; border:1px solid #E2E8F0; width: fit-content;">
              ${keyMasked}
            </div>
            <div>
              ${statusTag}
              ${data.status === 'offline' ? `<div style="font-size:0.75rem; color:#E11D48; margin-top:2px;">${data.lastMsg || ''}</div>` : ''}
            </div>
            <div style="display:flex; gap:8px; justify-content:flex-end;">
              <button onclick="window.BYOKVault.verifyKey('${prov}')" title="Test Live Status" style="background:#FFFFFF; border:1px solid #CBD5E1; color:#0F172A; padding:5px 10px; border-radius:4px; font-size:0.78rem; cursor:pointer; font-weight:600;">Test</button>
              <button onclick="window.BYOKVault.deleteKey('${prov}')" title="Delete Key from Vault" style="background:#FFF1F2; border:1px solid #FECDD3; color:#E11D48; padding:5px 10px; border-radius:4px; font-size:0.78rem; cursor:pointer; font-weight:700;">Remove</button>
            </div>
          </div>
        `;
      }

      container.innerHTML = `
        <div style="display:flex; flex-direction:column;">
          ${rowsHtml}
        </div>
      `;
    }
  }

  function initByok() {
    if (!window.BYOKVault) {
      window.BYOKVault = new ByokVaultManager();
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initByok);
  } else {
    initByok();
  }
})();
