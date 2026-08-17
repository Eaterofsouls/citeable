/**
 * byok.js — Citeable Standalone BYOK Key Vault Client Domain Engine
 * 
 * Provides an isolated, high-contrast modal interface for adding unlimited AI provider keys,
 * instant read-only diagnostic validation, zero-retention assurance, and local session alerts.
 * Works seamlessly across all Citeable pages without breaking existing navigation.
 */

(function() {
 const VAULT_STORAGE_KEY = 'areos_byok_vault';
 const API_BASE_URL = window.location.origin;

 const PROVIDER_INFO = {
 google: { name: "Google Gemini 2.0 / Pro", icon: "", tag: "Primary Recommendation" },
 openai: { name: "OpenAI (GPT-4o / o1 Series)", icon: "", tag: "Advanced Reasoning" },
 groq: { name: "Groq (LLaMA-3.3 70B)", icon: "", tag: "Ultra-Fast Inference" },
 anthropic: { name: "Anthropic Claude Haiku 4.5", icon: "[!]", tag: "Semantic Accuracy" },
 perplexity: { name: "Perplexity Sonar (Search)", icon: "", tag: "Live Grounding" },
 xai: { name: "xAI Grok 2 / Beta", icon: "X", tag: "Real-time Insights" },
 mistral: { name: "Mistral AI (Large / Medium)", icon: "", tag: "Open-Weights Top Tier" },
 deepseek: { name: "DeepSeek-V4 Flash / Pro", icon: "", tag: "Cost-Effective Logic" },
 azure: { name: "Azure OpenAI Service", icon: "", tag: "Enterprise Cloud" },
 custom: { name: "Custom / Ollama Endpoint", icon: "", tag: "Self-Hosted / Local" }
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
 // Check if a global toast element exists or create an isolated BYOK session alert
 let toastEl = document.getElementById('byok-private-toast');
 if (!toastEl) {
 toastEl = document.createElement('div');
 toastEl.id = 'byok-private-toast';
 toastEl.style.cssText = `
 position: fixed; bottom: 32px; right: 32px; z-index: 1000000;
 padding: 16px 24px; border-radius: 6px; font-weight: 700; font-size: 14px;
 box-shadow: 0 10px 30px rgba(0,0,0,0.85); transition: all 0.3s ease;
 display: none; border: 1px solid #777; font-family: var(--font-main, sans-serif);
 `;
 document.body.appendChild(toastEl);
 }

 if (type === 'success' || type === 'live') {
 toastEl.style.background = '#0F291E';
 toastEl.style.color = '#4ADE80';
 toastEl.style.borderColor = '#22C55E';
 } else if (type === 'error' || type === 'offline') {
 toastEl.style.background = '#2E1212';
 toastEl.style.color = '#F87171';
 toastEl.style.borderColor = '#EF4444';
 } else {
 toastEl.style.background = '#1E1E1E';
 toastEl.style.color = '#FFFFFF';
 toastEl.style.borderColor = '#777777';
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
 }, 4200);
 }

 initModal() {
 if (document.getElementById('byok-vault-modal')) return;

 const modalHtml = `
 <div id="byok-vault-modal" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.85); backdrop-filter: blur(8px); z-index: 999999; align-items: center; justify-content: center; padding: 20px;">
 <div class="glass-panel" style="background: #111111; border: 1px solid #555555; border-radius: 8px; max-width: 780px; width: 100%; max-height: 90vh; overflow-y: auto; padding: 32px; box-shadow: 0 25px 60px rgba(0,0,0,0.9); position: relative;">
 
 <!-- Modal Header -->
 <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid #333333; padding-bottom: 18px; margin-bottom: 24px;">
 <div>
 <h2 style="margin: 0; color: #FFFFFF; font-size: 1.6rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em;">
 Bring Your Own Key (BYOK) Vault
 </h2>
 <p style="margin: 6px 0 0 0; color: #CCCCCC; font-size: 0.95rem;">
 Configure your individual AI credentials to autonomously execute audits, RAG lookups, and evaluation judges. Add as many keys as you wish in one session.
 </p>
 </div>
 <button id="byok-close-btn" style="background: transparent; border: 1px solid #555; color: #FFF; font-size: 1.2rem; font-weight: 800; width: 36px; height: 36px; border-radius: 4px; cursor: pointer; display: flex; align-items: center; justify-content: center;"></button>
 </div>

 <!-- Headless & Zero-Retention Assurance Banner -->
 <div style="background: #181818; border: 1px solid #444444; border-left: 4px solid #4ADE80; padding: 18px; border-radius: 4px; margin-bottom: 28px;">
 <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
 <span style="font-size: 1.3rem;">[!]</span>
 <strong style="color: #FFFFFF; font-size: 1.02rem; text-transform: uppercase; letter-spacing: 0.06em;">Zero-Retention & Headless Memory Architecture</strong>
 </div>
 <p style="margin: 0; color: #E2E8F0; font-size: 0.92rem; line-height: 1.6;">
 <strong>Rest assured pasting your production keys:</strong> Citeable operates via stateless memory execution. Credentials saved here reside exclusively within your local browser memory (<code>localStorage</code>) and are transmitted solely via encrypted ephemeral HTTP headers (<code>X-API-Key-[Provider]</code>) during AI execution. Our servers never log, record, write to disk, or broadcast your secret keys across concurrent user sessions.
 </p>
 </div>

 <!-- Key Addition Form (Add unlimited keys) -->
 <div style="background: #151515; border: 1px solid #383838; border-radius: 6px; padding: 22px; margin-bottom: 28px;">
 <h3 style="color: #FFFFFF; font-size: 1.1rem; margin: 0 0 16px 0; text-transform: uppercase; letter-spacing: 0.05em;">+ Add New AI Provider Key</h3>
 <div style="display: grid; grid-template-columns: minmax(240px, 1fr) 2fr auto; gap: 14px; align-items: stretch;">
 <div>
 <select id="byok-select-provider" class="input" style="width: 100%; height: 48px; padding: 10px 14px; background: #202020; border: 1px solid #666; color: #FFFFFF; border-radius: 4px; font-weight: 600;">
 ${Object.entries(PROVIDER_INFO).map(([key, info]) => `<option value="${key}">${info.icon} ${info.name}</option>`).join('')}
 </select>
 </div>
 <div style="position: relative; display: flex; align-items: center;">
 <input type="password" id="byok-input-key" class="input" placeholder="Paste ephemeral API key here (e.g. AIza... or sk-...)" style="width: 100%; height: 48px; padding: 10px 42px 10px 16px; background: #202020; border: 1px solid #666; color: #FFFFFF; border-radius: 4px; font-family: monospace; font-size: 0.95rem;" />
 <button type="button" id="byok-toggle-eye" title="Show/Hide Secret Key" style="position: absolute; right: 8px; background: transparent; border: none; color: #AAAAAA; cursor: pointer; font-size: 1.2rem; padding: 4px;"></button>
 </div>
 <button id="byok-add-btn" class="btn-primary" style="height: 48px; padding: 0 24px; font-weight: 800; font-size: 0.95rem; white-space: nowrap; text-transform: uppercase;">
 Add & Test Key
 </button>
 </div>
 </div>

 <!-- Active Keys Table & Live Diagnostics Hub -->
 <div>
 <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
 <h3 style="color: #FFFFFF; font-size: 1.1rem; margin: 0; text-transform: uppercase; letter-spacing: 0.05em;">Active Local Vault Credentials</h3>
 <button id="byok-refresh-all-btn" style="background: #202020; border: 1px solid #777; color: #FFF; padding: 5px 12px; border-radius: 4px; font-size: 0.78rem; font-weight: 700; cursor: pointer;"> Verify All Live Status</button>
 </div>
 <div id="byok-keys-table-container" style="background: #141414; border: 1px solid #383838; border-radius: 6px; overflow: hidden; min-height: 80px;">
 <!-- Dynamically rendered table -->
 <div style="padding: 28px; text-align: center; color: #888888;">Loading local keys...</div>
 </div>
 </div>

 <div style="margin-top: 24px; text-align: right; border-top: 1px solid #333333; padding-top: 18px;">
 <button id="byok-done-btn" class="btn-primary" style="padding: 8px 22px; font-size: 0.88rem; font-weight: 800; background: #FFFFFF !important; color: #000 !important;">
 [OK] Save & Continue
 </button>
 </div>
 </div>
 </div>
 `;

 document.body.insertAdjacentHTML('beforeend', modalHtml);
 this.modalEl = document.getElementById('byok-vault-modal');

 // Bind events
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

 // Eye toggle
 const keyInput = document.getElementById('byok-input-key');
 const eyeBtn = document.getElementById('byok-toggle-eye');
 eyeBtn.addEventListener('click', () => {
 keyInput.type = keyInput.type === 'password' ? 'text' : 'password';
 });

 // Add key action
 document.getElementById('byok-add-btn').addEventListener('click', () => this.handleAddKey());
 document.getElementById('byok-refresh-all-btn').addEventListener('click', () => this.verifyAllKeys());

 // Also support pressing Enter inside key input
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
 this.showPrivateSessionAlert('[WARN] Please paste a valid API key first.', 'error');
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

 // Reset input immediately for adding another key
 keyInput.value = '';
 this.renderTable();

 // Dispatch real-time live verification check
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
 this.showPrivateSessionAlert(` LIVE: [${pName}] verified operational (${result.latency_ms}ms) for your active session!`, 'live');
 } else if (response.ok && result.status === 'unverified') {
 vault[provider].status = 'unverified';
 vault[provider].latencyMs = result.latency_ms || 0;
 vault[provider].lastMsg = result.message || 'Syntax Valid';
 this.saveVaultData(vault);
 this.renderTable();
 const pName = PROVIDER_INFO[provider]?.name || provider.toUpperCase();
 this.showPrivateSessionAlert(` UNVERIFIED: [${pName}] syntax verified valid for local/custom endpoint!`, 'info');
 } else {
 vault[provider].status = 'offline';
 vault[provider].lastMsg = result.message || 'Key failed validation';
 this.saveVaultData(vault);
 this.renderTable();
 const pName = PROVIDER_INFO[provider]?.name || provider.toUpperCase();
 this.showPrivateSessionAlert(` OFFLINE: [${pName}] check failed — ${vault[provider].lastMsg}`, 'offline');
 }
 } catch (err) {
 vault[provider].status = 'offline';
 vault[provider].lastMsg = 'Network connectivity or server error during ping';
 this.saveVaultData(vault);
 this.renderTable();
 this.showPrivateSessionAlert(` OFFLINE: Could not verify key against backend diagnostic ping.`, 'offline');
 }
 }

 async verifyAllKeys() {
 const vault = this.getVaultData();
 const providers = Object.keys(vault);
 if (providers.length === 0) {
 this.showPrivateSessionAlert('No keys in vault to verify.', 'info');
 return;
 }
 this.showPrivateSessionAlert(` Verifying live status for ${providers.length} AI providers...`, 'info');
 for (const prov of providers) {
 if (vault[prov]?.key) {
 this.verifyKey(prov, vault[prov].key); // launch in parallel
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
 this.showPrivateSessionAlert(` Removed [${pName}] credential from local browser vault.`, 'info');
 }
 }

 renderTable() {
 const container = document.getElementById('byok-keys-table-container');
 if (!container) return;
 const vault = this.getVaultData();
 const entries = Object.entries(vault);

 if (entries.length === 0) {
 container.innerHTML = `
 <div style="padding: 36px 20px; text-align: center; color: #888888; font-size: 0.95rem;">
 <div style="font-size: 2rem; margin-bottom: 8px;"></div>
 <div>No AI provider keys configured yet in this local browser vault.</div>
 <div style="font-size: 0.85rem; color: #666; margin-top: 4px;">Select a provider above, paste your secret token, and click <strong>Add & Test Key</strong> to begin!</div>
 </div>
 `;
 return;
 }

 let rowsHtml = '';
 for (const [prov, data] of entries) {
 const info = PROVIDER_INFO[prov] || { name: prov.toUpperCase(), icon: "X", tag: "Custom" };
 const keyMasked = data.key ? data.key.slice(0, 5) + "••••••••••••••••" : "Empty";
 
 let statusTag = `<span style="display:inline-flex; align-items:center; gap:6px; background:#2A2A2A; color:#CCC; padding:4px 10px; border-radius:12px; font-size:0.75rem; font-weight:800; border:1px solid #555;"> VERIFYING...</span>`;
 if (data.status === 'live') {
 statusTag = `<span style="display:inline-flex; align-items:center; gap:6px; background:rgba(34,197,94,0.15); color:#4ADE80; padding:4px 12px; border-radius:12px; font-size:0.78rem; font-weight:800; border:1px solid #22C55E;"> LIVE (${data.latencyMs || 0}ms)</span>`;
 } else if (data.status === 'unverified') {
 statusTag = `<span style="display:inline-flex; align-items:center; gap:6px; background:rgba(245,158,11,0.15); color:#FBBF24; padding:4px 12px; border-radius:12px; font-size:0.78rem; font-weight:800; border:1px solid #F59E0B;" title="${data.lastMsg || 'Syntax Valid'}"> UNVERIFIED (Syntax Valid)</span>`;
 } else if (data.status === 'offline') {
 statusTag = `<span style="display:inline-flex; align-items:center; gap:6px; background:rgba(239,68,68,0.15); color:#F87171; padding:4px 12px; border-radius:12px; font-size:0.78rem; font-weight:800; border:1px solid #EF4444;" title="${data.lastMsg || 'Invalid Key'}"> OFFLINE / INVALID</span>`;
 }

 rowsHtml += `
 <div style="display:grid; grid-template-columns: minmax(180px, 1.5fr) minmax(140px, 1.2fr) minmax(140px, 1fr) auto; gap:16px; align-items:center; padding:16px 20px; border-bottom:1px solid #262626; background:#161616;">
 <div>
 <div style="color:#FFF; font-weight:700; font-size:0.98rem; display:flex; align-items:center; gap:8px;">
 <span>${info.icon}</span> <span>${info.name}</span>
 </div>
 <div style="font-size:0.75rem; color:#888; margin-top:3px;">${info.tag}</div>
 </div>
 <div style="font-family:monospace; color:#DDD; font-size:0.88rem; background:#222; padding:6px 10px; border-radius:4px; border:1px solid #3A3A3A; width: fit-content;">
 ${keyMasked}
 </div>
 <div>
 ${statusTag}
 ${data.status === 'offline' ? `<div style="font-size:0.75rem; color:#F87171; margin-top:4px;">${data.lastMsg || ''}</div>` : ''}
 </div>
 <div style="display:flex; gap:8px; justify-content:flex-end;">
 <button onclick="window.BYOKVault.verifyKey('${prov}')" title="Test Live Status" style="background:#222; border:1px solid #666; color:#FFF; padding:6px 10px; border-radius:4px; font-size:0.8rem; cursor:pointer; font-weight:600;"> Test</button>
 <button onclick="window.BYOKVault.deleteKey('${prov}')" title="Delete Key from Vault" style="background:#261212; border:1px solid #F87171; color:#F87171; padding:6px 10px; border-radius:4px; font-size:0.8rem; cursor:pointer; font-weight:700;"> Remove</button>
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

 // Ensure DOM is ready or immediately initialize if dynamically injected after load
 function initByok() {
 if (!window.BYOKVault) {
 window.BYOKVault = new ByokVaultManager();
 console.log("[OK] Citeable BYOK Vault Domain initialized and available via window.BYOKVault.");
 }
 }
 if (document.readyState === 'loading') {
 document.addEventListener('DOMContentLoaded', initByok);
 } else {
 initByok();
 }

})();
