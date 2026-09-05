/**
 * help.js
 * Onboarding panel + minimizable FAB for Citeable
 */

const HELP_HTML = `
<style>
.help-pill-btn {
  position: fixed;
  bottom: 24px;
  right: 24px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px 6px 8px;
  background: #FFFFFF;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-full);
  color: var(--text-secondary);
  font-family: inherit;
  font-size: var(--text-xs);
  font-weight: 600;
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  z-index: 9999;
  transition: all var(--duration-snappy) var(--ease-damped);
  outline: none;
}
.help-pill-btn:hover {
  border-color: var(--border-strong);
  color: var(--text-primary);
  box-shadow: var(--shadow-md);
  transform: none;
}
.help-pill-btn:active {
  transform: translateY(1px);
}
.help-pill-icon {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--surface-sunken);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 11px;
}
.help-pill-kbd {
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 4px;
  background: var(--surface-sunken);
  border: 1px solid var(--border-default);
  color: var(--text-tertiary);
}

.help-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: var(--surface-overlay);
  backdrop-filter: blur(4px);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.3s;
}
.help-overlay.active {
  opacity: 1;
  pointer-events: auto;
}

.help-panel {
  width: 90%;
  max-width: 800px;
  background: #FFFFFF;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 0;
  display: flex;
  flex-direction: column;
  max-height: 90vh;
  box-shadow: var(--shadow-xl);
  transform: scale(0.95) translateY(20px);
  transition: all 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.help-overlay.active .help-panel {
  transform: scale(1) translateY(0);
}

.help-header {
  padding: 24px 32px;
  border-bottom: 1px solid var(--border-default);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.help-header h2 { margin: 0; font-size: 1.3rem; font-weight: 800; color: var(--text-primary); }
.help-close {
  background: none; border: none; color: var(--text-tertiary);
  font-size: 1.5rem; cursor: pointer; padding: 4px; border-radius: 4px;
}
.help-close:hover { color: var(--text-primary); background: var(--surface-sunken); }

.help-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.help-toc {
  width: 240px;
  border-right: 1px solid var(--border-default);
  padding: 24px;
  background: var(--surface-sunken);
}
.help-toc-item {
  padding: 10px 14px;
  margin-bottom: 6px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  font-weight: 600;
  transition: all 0.15s;
}
.help-toc-item:hover { background: #FFFFFF; color: var(--brand-500); }
.help-toc-item.active {
  background: var(--brand-50);
  color: var(--brand-500);
  border: 1px solid var(--brand-100);
  font-weight: 700;
}

.help-content {
  flex: 1;
  padding: 32px;
  overflow-y: auto;
}
.help-step { display: none; }
.help-step.active { display: block; animation: fadeIn 0.3s; }

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.help-step h3 { font-size: 1.2rem; font-weight: 700; margin-top: 0; margin-bottom: 12px; color: var(--text-primary); }
.help-step p { color: var(--text-secondary); line-height: 1.6; margin-bottom: 24px; font-size: var(--text-sm); }
.help-img-placeholder {
  width: 100%; height: 240px;
  background: var(--surface-sunken);
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-md);
  display: flex; align-items: center; justify-content: center;
  color: var(--text-tertiary); font-size: 0.9rem; margin-bottom: 24px;
}
.help-nav-btns {
  display: flex; justify-content: space-between;
  margin-top: 32px; padding-top: 24px; border-top: 1px solid var(--border-default);
}

@media (max-width: 640px) {
  .help-body { flex-direction: column; }
  .help-toc { width: 100%; border-right: none; border-bottom: 1px solid var(--border-default); display: flex; overflow-x: auto; padding: 16px; }
  .help-toc-item { white-space: nowrap; margin-bottom: 0; margin-right: 8px; }
  .help-content { padding: 20px; }
}
</style>

<button id="help-fab" class="help-pill-btn" aria-label="Open Help and Tour" title="Documentation & Quick Tour (Press ? or Ctrl+/)">
  <span class="help-pill-label">Help & Tour</span>
</button>

<div id="help-overlay" class="help-overlay">
  <div class="help-panel">
    <div class="help-header">
      <h2>How to use Citeable</h2>
      <button class="help-close" id="help-close" aria-label="Minimize">&times;</button>
    </div>
    
    <div class="help-body">
      <div class="help-toc" id="help-toc">
        <div class="help-toc-item active" data-step="0">1. Getting Started</div>
        <div class="help-toc-item" data-step="1">2. Adding Your AI Key</div>
        <div class="help-toc-item" data-step="2">3. Running an Audit</div>
        <div class="help-toc-item" data-step="3">4. Reviewing Results</div>
      </div>
      
      <div class="help-content">
        <!-- Step 0 -->
        <div class="help-step active" data-step="0">
          <h3>Welcome to the Audit Studio</h3>
          <p>Citeable is a tool to test if your website can be read and cited by AI engines like ChatGPT and Gemini. This isn't traditional SEO — we test actual generative AI retrieval.</p>
          <div class="help-img-placeholder">
            <img src="assets/help-dashboard.png" alt="Screenshot: The main Dashboard" style="width:100%; height:100%; object-fit:cover; border-radius:inherit;" onerror="this.parentElement.innerHTML='[ Screenshot Loading... ]'">
          </div>
          <div class="help-nav-btns">
            <div></div>
            <button class="btn-primary" onclick="window.helpTour.goTo(1)">Next Step &rarr;</button>
          </div>
        </div>
        
        <!-- Step 1 -->
        <div class="help-step" data-step="1">
          <h3>Adding Your AI Key (BYOK)</h3>
          <p>Because Citeable runs live AI queries to test your site, you need to provide your own API key. We recommend getting a free Google Gemini key or Groq key. Your keys never leave your browser.</p>
          <div class="help-img-placeholder">
            <img src="assets/help-byok.png" alt="Screenshot: BYOK Vault Modal" style="width:100%; height:100%; object-fit:cover; border-radius:inherit;" onerror="this.parentElement.innerHTML='[ Screenshot Loading... ]'">
          </div>
          <div class="help-nav-btns">
            <button class="btn-secondary" onclick="window.helpTour.goTo(0)">&larr; Back</button>
            <button class="btn-primary" onclick="window.helpTour.goTo(2)">Next Step &rarr;</button>
          </div>
        </div>

        <!-- Step 2 -->
        <div class="help-step" data-step="2">
          <h3>Running an Audit</h3>
          <p>Once your key is set, simply enter your website domain (e.g. <code>yoursite.com</code>) on the Audit Studio page and click "Run Full Spectrum Audit". The system will crawl your site, analyze its technical layers, and test AI citation eligibility.</p>
          <div class="help-img-placeholder">
            <img src="assets/help-running.png" alt="Screenshot: Audit running with stepper" style="width:100%; height:100%; object-fit:cover; border-radius:inherit;" onerror="this.parentElement.innerHTML='[ Screenshot Loading... ]'">
          </div>
          <div class="help-nav-btns">
            <button class="btn-secondary" onclick="window.helpTour.goTo(1)">&larr; Back</button>
            <button class="btn-primary" onclick="window.helpTour.goTo(3)">Next Step &rarr;</button>
          </div>
        </div>

        <!-- Step 3 -->
        <div class="help-step" data-step="3">
          <h3>Reviewing the Final Report</h3>
          <p>When finished, Citeable generates a scored AI-readiness report across 5 diagnostic layers (Access, Schema, Content, Citation, Authority), with a prioritized remediation plan showing exactly what technical fixes to make.</p>
          <div class="help-img-placeholder">
            <img src="assets/help-report.png" alt="Screenshot: The Final Report Scorecard" style="width:100%; height:100%; object-fit:cover; border-radius:inherit;" onerror="this.parentElement.innerHTML='[ Screenshot Loading... ]'">
          </div>
          <div class="help-nav-btns">
            <button class="btn-secondary" onclick="window.helpTour.goTo(2)">&larr; Back</button>
            <button class="btn-primary" id="help-finish">Got it, let's go!</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
`;

class HelpTour {
  constructor() {
    this.currentStep = 0;
    this.init();
  }

  init() {
    document.body.insertAdjacentHTML('beforeend', HELP_HTML);
    
    this.fab = document.getElementById('help-fab');
    this.overlay = document.getElementById('help-overlay');
    this.closeBtn = document.getElementById('help-close');
    this.finishBtn = document.getElementById('help-finish');
    this.tocItems = document.querySelectorAll('.help-toc-item');
    this.steps = document.querySelectorAll('.help-step');

    // Bind events
    this.fab.addEventListener('click', () => this.open());

    // Keyboard shortcut to open help tour (? or Ctrl+/)
    document.addEventListener('keydown', (e) => {
      if ((e.key === '?' || ((e.metaKey || e.ctrlKey) && e.key === '/')) && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
        e.preventDefault();
        if (this.overlay && this.overlay.classList.contains('active')) {
          this.close();
        } else {
          this.open();
        }
      }
    });

    this.closeBtn.addEventListener('click', () => this.close());
    this.finishBtn.addEventListener('click', () => this.close());
    
    // DEC-05: Backdrop click dismissal
    this.overlay.addEventListener('click', (e) => {
      if (e.target === this.overlay) this.close();
    });

    // DEC-05: Esc key closing
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.overlay && this.overlay.classList.contains('active')) {
        this.close();
      }
    });

    this.tocItems.forEach(item => {
      item.addEventListener('click', (e) => {
        const step = parseInt(e.currentTarget.getAttribute('data-step'));
        this.goTo(step);
      });
    });

    // Auto-open on very first visit
    if (!localStorage.getItem('citeable_help_seen')) {
      setTimeout(() => this.open(), 1000);
    }
  }

  open() {
    this.overlay.classList.add('active');
    localStorage.setItem('citeable_help_seen', 'true');
  }

  close() {
    this.overlay.classList.remove('active');
  }

  goTo(stepIndex) {
    this.currentStep = stepIndex;
    
    // Update TOC
    this.tocItems.forEach(item => item.classList.remove('active'));
    document.querySelector(`.help-toc-item[data-step="${stepIndex}"]`).classList.add('active');
    
    // Update Content
    this.steps.forEach(step => step.classList.remove('active'));
    document.querySelector(`.help-step[data-step="${stepIndex}"]`).classList.add('active');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.helpTour = new HelpTour();
});
