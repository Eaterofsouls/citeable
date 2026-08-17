// guided_review.js — Citeable Guided Manual-Review Walkthrough Controller (Category F)
// Designed as an additive, human-centered manual for non-technical executives and analysts.
// Explains clearly WHY each check matters, WHAT to look for, and HOW to verify step-by-step.
// Integrates natively with manual_review.js without altering API endpoints or database schemas.

window.GuidedReview = (function() {
  let queue = [];
  let currentIndex = 0;
  let activeVerdict = null;

  const FAMILY_BY_CARD_ID = {
    "C052": "extractability",
    "C053": "schema",
    "C056": "schema",
    "C058": "extractability",
    "C061": "extractability",
    "C062": "citations",
    "C072": "citations",
    "C073": "citations",
    "C074": "citations",
    "C077": "citations",
    "C078": "citations",
    "C079": "schema",
    "C082": "citations",
    "C090": "fallback"
  };

  function getCheckFamily(cardId, checkName, reason) {
    if (cardId && FAMILY_BY_CARD_ID[cardId]) {
      return FAMILY_BY_CARD_ID[cardId];
    }
    const text = ((cardId || "") + " " + (checkName || "") + " " + (reason || "")).toUpperCase();
    if (text.includes("EXTRACT") || text.includes("LAYOUT") || text.includes("C061") || text.includes("DOM") || text.includes("RENDER") || text.includes("C052")) {
      return "extractability";
    }
    if (text.includes("SCHEMA") || text.includes("JSON") || text.includes("LD") || text.includes("SEMANTIC") || text.includes("C073") || text.includes("C082")) {
      return "schema";
    }
    if (text.includes("CRAWLER") || text.includes("ROBOT") || text.includes("LLM") || text.includes("TXT") || text.includes("BOT")) {
      return "crawler";
    }
    if (text.includes("CITATION") || text.includes("REFERENCE") || text.includes("AUTHORITY") || text.includes("BACKLINK") || text.includes("SOURCE")) {
      return "citations";
    }
    return "fallback";
  }

  function escapeHtml(s) {
    return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function getHumanReviewGuidance(cardId, checkName, reason) {
    const family = getCheckFamily(cardId, checkName, reason);
    if (family === "extractability") {
      return `<strong>Tailored AI Extractability Protocol:</strong> Inspect how clean content is retrieved by AI scrapers.<br>
      • <strong>PASS:</strong> Page main content is clean, semantic HTML directly visible without execution of complex client-side JS or obstructive interstitials.<br>
      • <strong>WARN:</strong> Content requires parsing nested layouts or unsemantic containers, which may slightly degrade token quality in LLM embeddings.<br>
      • <strong>FAIL:</strong> Layout blocks autonomous extraction, depends entirely on heavy client JS, or traps bots in obfuscated DOM wrappers.`;
    }
    if (family === "schema") {
      return `<strong>Tailored Structured Data Protocol:</strong> Verify structural assertions in HTML header/source.<br>
      • <strong>PASS:</strong> JSON-LD and semantic entity graphs accurately assert true organizational facts matching on-page content.<br>
      • <strong>WARN:</strong> Valid schema syntax, but missing essential entity declarations (Author, Organization, Date Modified) needed for authoritative LLM citation.<br>
      • <strong>FAIL:</strong> Unsupported or deceptive schema markup detected that contradicts empirical operational claims.`;
    }
    if (family === "crawler") {
      return `<strong>Tailored AI Autonomous Access Protocol:</strong> Verify AI bot user-agent permissions.<br>
      • <strong>PASS:</strong> Key autonomous research bots (<code>GPTBot</code>, <code>ClaudeBot</code>, <code>PerplexityBot</code>, <code>OAI-SearchBot</code>) enjoy unrestricted access.<br>
      • <strong>WARN:</strong> Partial allowance or contradictory directives between robots.txt and firewalls.<br>
      • <strong>FAIL:</strong> AI research agents encounter blanket 403 blocks, CAPTCHA walls, or complete robots.txt exclusion.`;
    }
    if (family === "citations") {
      return `<strong>Tailored Citations & External Authority Protocol:</strong> Verify third-party corroboration and citation evidence.<br>
      • <strong>PASS:</strong> Authoritative external publishers confirm empirical statements and brand entities.<br>
      • <strong>WARN:</strong> External coverage exists but contains ambiguous or outdated operational details.<br>
      • <strong>FAIL:</strong> External corroborating evidence is totally absent or contradicts on-page claims.`;
    }
    return `<strong>General Verification Protocol:</strong> Review this diagnostic check against empirical RAG visibility and LLM citation behavior.<br>
    • <strong>PASS:</strong> Empirical verification confirms zero degradation to AI reference quality or answer accuracy.<br>
    • <strong>WARN:</strong> Minor architectural formatting ambiguity that may lower citation frequency.<br>
    • <strong>FAIL:</strong> Issue severely disrupts Generative AI trust evaluation or prevents citation.`;
  }

  // Per-card guidance, keyed by the real card_id \u2014 rewritten after the
  // UX audit found that two different cards (e.g. C073 vs C082, C058 vs
  // C061) were showing byte-identical text because guidance was generated
  // from 5 generic keyword-matched families instead of the actual 14
  // instruction cards in areos/instruction_cards/*.md. Each entry below is
  // a simplified, layman-language adaptation of that card's real content
  // \u2014 not an invented generic template \u2014 so two different cards now say
  // two different things. `example`, where present, is filled in with the
  // real domain at render time and shows literal query text for
  // ChatGPT/Perplexity/Google AI Mode rather than an abstract instruction.
  const CARD_GUIDANCE = {
    C052: {
      question: "If you strip away the JavaScript, is your content still there?",
      why: "Some sites only show their real text after JavaScript finishes running. AI bots don't wait for that \u2014 they read the raw HTML. If your main content only exists after JS loads, bots see a blank page.",
      steps: [
        "Right-click the page \u2192 <em>View Page Source</em> (or Ctrl/Cmd+U) \u2014 this shows the raw HTML before any JavaScript runs.",
        "Ctrl/Cmd+F for a sentence you know is on the page.",
        "If you can't find it in that raw source, your content is JavaScript-only \u2014 AI bots likely can't read it."
      ]
    },
    C053: {
      question: "Does your structured data actually say what your page says \u2014 or does it oversell?",
      why: "AI engines read your invisible \u201cschema\u201d tags as factual claims. If those tags state something the visible page doesn't back up, that's a credibility mismatch AI models are specifically built to catch.",
      steps: [
        "View Page Source and Ctrl/Cmd+F for <code>application/ld+json</code>.",
        "Compare each fact in there (like FAQ answers) against what's actually written on the visible page.",
        "Watch for exaggerated claims (\u201caward-winning\u201d, \u201c24/7 support\u201d) that appear in the schema but nowhere on the page itself."
      ]
    },
    C056: {
      question: "When you ask an AI who you are, does it actually know?",
      why: "AI models sometimes confuse similarly-named brands. If yours isn't clearly anchored to an identity source (Wikipedia, Wikidata, LinkedIn), the AI may describe a completely different company under your name.",
      steps: [
        "Search your brand name on <a href=\"https://www.wikidata.org\" target=\"_blank\" rel=\"noopener\">wikidata.org</a> \u2014 does an entry exist, and does your site link to it?",
        "Ask an AI directly (see the example below).",
        "If the answer describes the wrong company, or hedges with \u201cI'm not sure\u201d, that's a disambiguation gap."
      ],
      example: "Open ChatGPT, Perplexity, or Google AI Mode and type: \u201cWhat does {{domain}} do?\u201d \u2014 read the answer closely. Is it describing you, or does it sound like it's talking about a different company?"
    },
    C058: {
      question: "Is important information trapped inside an image, video, or PDF instead of text?",
      why: "AI bots read text, not pictures. If key facts \u2014 pricing, specs, instructions \u2014 only exist inside an image, embedded video, or PDF, the AI can't see them at all, even though a human visitor can.",
      steps: [
        "Note anything on the page shown only as an image, embedded video, or PDF.",
        "Try to select that content as text (click and drag, or Ctrl/Cmd+C) \u2014 if you can't select it, it's an image, not text.",
        "Check whether that same information is also written out in plain text anywhere else on the page."
      ]
    },
    C061: {
      question: "Is your page laid out in a way that's easy to break into clean, quotable pieces?",
      why: "AI engines split pages into chunks to pull facts from. Long unbroken walls of text, or content hidden behind tabs and accordions, are harder to chunk cleanly \u2014 so AI is less confident quoting from them.",
      steps: [
        "Check whether the page has clear headings breaking it into sections.",
        "Check whether paragraphs are a few sentences long, or long unbroken blocks.",
        "Check whether any key content is hidden behind a click (tabs, accordions, \u201cread more\u201d) rather than visible immediately."
      ]
    },
    C062: {
      question: "Would a stranger reading this page believe the author actually knows what they're talking about?",
      why: "AI models favor content that shows real experience and a credible, named author over generic, unattributed text \u2014 this is the same \u201cE-E-A-T\u201d standard (Experience, Expertise, Authoritativeness, Trustworthiness) search engines use.",
      steps: [
        "Is there a named author with a visible bio or credentials \u2014 not just \u201cAdmin\u201d or no byline at all?",
        "Does the content include specific, first-hand details, or could it have been written by anyone about any company?",
        "Are factual claims backed by a source, or just stated outright?"
      ]
    },
    C072: {
      question: "Are we even testing the right questions about your brand?",
      why: "This report's citation results (\u201ccited in 3/5 runs\u201d) only mean something if the tested questions match what your real customers actually ask AI. The wrong questions produce misleading results.",
      steps: [
        "Think about what your customers actually type into ChatGPT or Google when researching your category.",
        "Compare that against the prompts this audit tested (see the Results tab).",
        "Flag it if the tested questions don't match how real customers actually ask."
      ]
    },
    C073: {
      question: "For pages AI isn't citing, do you actually know why?",
      why: "Our scan can tell you a page wasn't cited \u2014 it can't tell you why. That's a judgment call: comparing your page against one that WAS cited for the same question.",
      steps: [
        "Pick a page or topic that wasn't cited, and re-run that exact question in an AI tool (see the example below).",
        "Open whichever page WAS cited instead, and compare: clearer structure? schema? more detail?",
        "Write down your best-supported guess at the real cause."
      ],
      example: "Say your domain is {{domain}} and the topic is \u201cbest project management tools.\u201d Type that exact question into Perplexity. If a competitor's page is cited instead of yours, open their page and see what it has that yours doesn't."
    },
    C074: {
      question: "When you ask AI about your brand, does it actually get the facts right?",
      why: "AI engines sometimes state things about a brand that are outdated, exaggerated, or flat wrong \u2014 and once that's the answer people see, it can quietly do real damage.",
      steps: [
        "Ask AI the questions in the example below.",
        "Compare the answer line-by-line against your real website and official facts.",
        "Note anything wrong, outdated, or made up \u2014 even if it seems minor."
      ],
      example: "Type into ChatGPT, Perplexity, or Google AI Mode: \u201cWhat does {{domain}} do?\u201d and \u201cWhat is {{domain}} known for?\u201d \u2014 check every claim in the answer against your real About page."
    },
    C077: {
      question: "When AI mentions you, do you sound like a strong option \u2014 or a distant runner-up?",
      why: "An AI answer can be technically accurate and still make your brand look worse than a competitor \u2014 through subtle word choice, or by leaving you off a \u201ctop options\u201d list entirely. A simple positive/negative check misses this.",
      steps: [
        "Ask AI a question a real customer would ask that should mention you (see the example below).",
        "Read the full answer, not just whether you're mentioned.",
        "Watch for backhanded phrasing (\u201ca basic option for small businesses\u201d) or being left off a \u201ctop options\u201d list."
      ],
      example: "Ask Perplexity or ChatGPT: \u201cWhat are the best options for [your category]?\u201d If {{domain}} is missing from the list, or described as \u201csmaller\u201d or \u201cbasic\u201d while competitors are called \u201cleading,\u201d that's a framing problem, not just a visibility one."
    },
    C078: {
      question: "If AI already gave the user a full answer, would they ever bother visiting your site?",
      why: "Not being cited isn't the only risk \u2014 sometimes AI answers so completely that nobody clicks through anywhere, even to the site the answer came from. That's lost traffic either way.",
      steps: [
        "Ask AI a question tied to your business (see the example below).",
        "Read the answer: does it fully satisfy the question, or leave the user wanting more (and likely to click through)?",
        "If the answer is \u201ccomplete,\u201d consider whether that's fine for your business (brand awareness) or a real traffic risk (you need the click to sell something)."
      ],
      example: "Ask ChatGPT or Google AI Mode a question tied to {{domain}}'s business \u2014 e.g. \u201cHow does [your service] work?\u201d If the answer alone would satisfy most users, they may never click through to your site at all."
    },
    C079: {
      question: "If a smart speaker read your answer out loud, would it actually make sense?",
      why: "Voice assistants pull one specific short passage marked as \u201cspeakable.\u201d If it's too long, references something visual (\u201csee the chart below\u201d), or starts mid-sentence, it fails as a spoken answer even if it reads fine on screen.",
      steps: [
        "Find the \u201cspeakable\u201d section in the page's schema (or note if there isn't one).",
        "Read that exact passage out loud.",
        "Does it stand alone and make sense with no visual context, in under about 100 words?"
      ]
    },
    C082: {
      question: "When someone else gets cited instead of you, do you know who \u2014 and why?",
      why: "This is different from C073's root-cause question: this is specifically about third parties (news sites, review platforms, Wikipedia) winning the citation instead of you \u2014 which points to a PR/outreach gap, not a technical one.",
      steps: [
        "List every domain that gets cited when your brand isn't \u2014 industry press, review sites (G2, Trustpilot), Wikipedia, competitors.",
        "Open a couple of those pages and compare: simpler language? more neutral tone? schema markup you're missing?",
        "Note which category of gap this is \u2014 media coverage, review presence, or Wikipedia/Wikidata \u2014 since each has a different fix."
      ],
      example: "Ask Perplexity: \u201cWhat's the best [your category]?\u201d and see which third-party sites show up instead of {{domain}}. That list is your PR gap map."
    },
    C090: {
      question: "Looking at everything above, what's the real reason this page isn't getting cited?",
      why: "Each individual finding \u2014 blocked robots, thin content, missing schema \u2014 is a clue, not a verdict. This step connects the clues into one explanation, which is what actually tells you what to fix first.",
      steps: [
        "List every finding above for this page/topic, alongside whether it was cited or not.",
        "Check access first: could AI bots even reach and read the page? If not, that's your primary cause \u2014 fix it before anything else.",
        "If access is fine, work upward through content quality, then brand authority, to find where the chain actually breaks."
      ]
    }
  };

  const FALLBACK_GUIDANCE = {
    question: "Does this check hold up when you look at the actual page?",
    why: "This is a check our automated scan flagged for a human to confirm \u2014 it's the kind of judgment call a script can't make reliably on its own.",
    steps: [
      "Open the page or setting this check refers to (see the reference below).",
      "Compare what you see against what the check is asking about.",
      "Use your judgment: does it look correct, borderline, or clearly broken?"
    ]
  };

  // Rewritten per UX audit \u00a75.5 so each card reads like an interview
  // question, not a system-log dump. steps[] contains ONLY the how-to-check
  // procedure; PASS/WARN/FAIL definitions live on the buttons themselves
  // (see renderInlineWizard), not duplicated in prose.
  function getSimpleGuidance(card) {
    return CARD_GUIDANCE[card.card_id] || FALLBACK_GUIDANCE;
  }

  let guidedDialog = null;
  function getGuidedDialog() {
    if (!guidedDialog && typeof makeDialogAccessible === "function") {
      const modal = document.getElementById("guided-modal");
      if (modal) {
        guidedDialog = makeDialogAccessible(modal, {
          role: "dialog",
          label: "Guided Review Walkthrough",
          onClose: () => close()
        });
      }
    }
    return guidedDialog;
  }

  async function submitInlineVerdict(cardId, verdict, opts) {
    const notesEl = document.getElementById(`notes-${cardId}`);
    const notes = notesEl && notesEl.value.trim() ? notesEl.value.trim() : `Human qualitative verification recorded as ${verdict.toUpperCase()}`;
    const runId = opts.runId || window.currentRunId || "";
    const domainEl = document.getElementById("domain-input");
    const pageUrl = domainEl && domainEl.value ? "https://" + domainEl.value.trim() : "https://domain.com";
    const severity = verdict === 'pass' ? 'info' : (verdict === 'warn' ? 'warning' : 'error');

    try {
      if (runId && typeof AreosAPI !== "undefined") {
        const headers = (typeof getAuthHeaders === "function") ? getAuthHeaders({ "Content-Type": "application/json" }) : { "Content-Type": "application/json" };
        const res = await AreosAPI.fetch(`/api/v1/audit/runs/${runId}/verdicts`, {
          method: "POST",
          headers: headers,
          body: JSON.stringify({
            card_id: cardId,
            page_url: pageUrl,
            verdict: verdict,
            severity: severity,
            notes: notes
          })
        });
        if (!res.ok) {
          if (typeof AreosAPI !== "undefined" && AreosAPI.notify) AreosAPI.notify("Failed to save evaluation.");
        }
      }

      const cardEl = document.getElementById(`wizard-card-${cardId}`);
      if (cardEl) {
        cardEl.style.borderColor = verdict === 'pass' ? '#10b981' : (verdict === 'warn' ? '#f59e0b' : '#ef4444');
        cardEl.style.background = 'rgba(15, 23, 42, 0.9)';
        const verdictLabel = verdict === 'pass' ? 'Pass' : (verdict === 'warn' ? 'Warn' : 'Fail');
        cardEl.innerHTML = `
        <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 0.5rem;">
        <div>
        <strong style="color: #ffffff; font-size: 1.1rem;">\u2713 Answered: ${verdictLabel}</strong>
        ${notes ? `<p style="margin: 0.4rem 0 0; color: #94a3b8; font-size: 0.9rem;">${escapeHtml(notes)}</p>` : ""}
        </div>
        <span style="background: rgba(16, 185, 129, 0.2); color: #6ee7b7; padding: 0.4rem 1rem; border-radius: 8px; font-weight: 700; font-size: 0.85rem;">Saved</span>
        </div>`;
      }

      if (opts && typeof opts.onVerdict === "function") {
        opts.onVerdict(cardId, verdict);
      }
    } catch (error) {
      console.error("Error saving verdict:", error);
      if (typeof AreosAPI !== "undefined" && AreosAPI.notify) AreosAPI.notify("Network error while submitting evaluation.");
    }
  }

  // Redesigned per UX audit \u00a75.5: each card reads as one interview
  // question (headline) \u2014 why it matters \u2014 how to check it (numbered)
  // \u2014 a fast Pass/Warn/Fail answer. Check codes / card IDs move to a
  // small monospace footnote instead of leading the card.
  function renderInlineWizard(cards, opts) {
    const cEl = document.querySelector(opts.container || "#wizard-list");
    if (!cEl) return;
    cEl.innerHTML = "";

    const domainInput = document.getElementById("domain-input");
    const domain = domainInput ? domainInput.value.trim() : "";
    const siteUrl = domain ? (domain.startsWith("http") ? domain : `https://${domain}`) : null;

    cards.forEach((wiz, idx) => {
      const guide = getSimpleGuidance(wiz);
      const stepsHtml = (guide.steps || []).map(s => `<li>${s}</li>`).join("");
      const checkRef = escapeHtml((wiz.reason || wiz.check_name || "QUALITATIVE_EVALUATION")).replace(/^Check code\(s\) fired:\s*/i, "");

      const wizCard = document.createElement("div");
      wizCard.className = "gr-card";
      wizCard.id = `wizard-card-${wiz.card_id}`;
      const exampleHtml = guide.example
        ? `<div class="gr-card-example">
             <strong>Try it yourself</strong>
             ${escapeHtml(guide.example.replace(/\{\{domain\}\}/g, domain || "yourdomain.com"))}
           </div>`
        : "";
      wizCard.innerHTML = `
        <div class="gr-question-progress">
          <span>Question ${idx + 1} of ${cards.length}</span>
          <div class="gr-question-dots">
            ${cards.map((c, i) => `<span class="${i < idx ? 'is-done' : (i === idx ? 'is-current' : '')}"></span>`).join("")}
          </div>
        </div>

        <h3 class="gr-card-question">${escapeHtml(guide.question)}</h3>

        <div class="gr-card-why">
          <strong>Why this matters</strong>
          ${escapeHtml(guide.why)}
        </div>

        <div class="gr-card-how">
          <strong>How to check it</strong>
          <ol>${stepsHtml}</ol>
        </div>

        ${exampleHtml}

        ${siteUrl ? `<a class="gr-view-page-btn" href="${siteUrl}" target="_blank" rel="noopener">\uD83D\uDC40 View the site we're asking about</a>` : ""}

        <input type="text" class="verdict-notes" id="notes-${wiz.card_id}" placeholder="Add a note (optional)..." style="width: 100%; background: rgba(15,23,42,0.8); border: 1px solid rgba(255,255,255,0.1); padding: 0.7rem 0.9rem; border-radius: 6px; color: white; font-size: 0.9rem; margin-bottom: 0.9rem;">

        <div class="gr-verdict-row">
          <button class="btn-verdict gr-verdict-btn yes" data-card-id="${wiz.card_id}" data-verdict="pass">\u2713 Pass</button>
          <button class="btn-verdict gr-verdict-btn partly" data-card-id="${wiz.card_id}" data-verdict="warn">\u26A0 Warn</button>
          <button class="btn-verdict gr-verdict-btn no" data-card-id="${wiz.card_id}" data-verdict="fail">\u2717 Fail</button>
        </div>

        <div class="gr-card-footnote">Check ${escapeHtml(wiz.card_id || "")} \u00b7 ${checkRef}</div>
      `;
      const passBtn = wizCard.querySelector(".yes");
      const warnBtn = wizCard.querySelector(".partly");
      const failBtn = wizCard.querySelector(".no");
      if (passBtn) passBtn.onclick = () => { wizCard.querySelectorAll(".gr-verdict-btn").forEach(b => b.classList.remove("selected")); passBtn.classList.add("selected"); submitInlineVerdict(wiz.card_id, "pass", opts); };
      if (warnBtn) warnBtn.onclick = () => { wizCard.querySelectorAll(".gr-verdict-btn").forEach(b => b.classList.remove("selected")); warnBtn.classList.add("selected"); submitInlineVerdict(wiz.card_id, "warn", opts); };
      if (failBtn) failBtn.onclick = () => { wizCard.querySelectorAll(".gr-verdict-btn").forEach(b => b.classList.remove("selected")); failBtn.classList.add("selected"); submitInlineVerdict(wiz.card_id, "fail", opts); };
      cEl.appendChild(wizCard);
    });
  }

  function start(cards, opts) {
    if (!cards || !Array.isArray(cards)) {
      cards = window.currentCards || [];
    }
    opts = opts || { mode: "modal", container: "#guided-modal" };

    if (!cards || cards.length === 0) {
      if (opts.mode === "inline" && opts.container) {
        const cEl = document.querySelector(opts.container);
        if (cEl) cEl.innerHTML = `<div style="padding: 1.5rem; text-align: center; color: #94a3b8; background: rgba(30, 41, 59, 0.4); border-radius: 12px;">All diagnostic checks were determined automatically. No qualitative manual reviews required.</div>`;
      } else if (typeof showToast === "function") {
        showToast("No diagnostic checks available to review.", "warning");
      }
      return;
    }

    if (opts.mode === "inline") {
      renderInlineWizard(cards, opts);
      return;
    }

    queue = cards.filter(c => !(c.verdicts && c.verdicts.length > 0));
    if (queue.length === 0) {
      queue = cards.slice();
    }
    currentIndex = 0;
    activeVerdict = null;
    
    bindKeyboard();
    const modal = document.getElementById("guided-modal");
    if (modal) modal.style.display = "flex";
    const dlg = getGuidedDialog();
    if (dlg && typeof dlg.open === "function") dlg.open();
    renderCurrentStep();
  }

  function close() {
    unbindKeyboard();
    const modal = document.getElementById("guided-modal");
    if (modal) modal.style.display = "none";
    const dlg = getGuidedDialog();
    if (dlg && typeof dlg.close === "function") dlg.close();
  }

  function renderCurrentStep() {
    const card = queue[currentIndex];
    if (!card) {
      renderComplete();
      return;
    }
    activeVerdict = null;
    
    const stepLabel = document.getElementById("gr-step-label");
    const progressFill = document.getElementById("gr-progress-fill");
    if (stepLabel) stepLabel.textContent = `Step ${currentIndex + 1} of ${queue.length}`;
    if (progressFill) {
      const pct = Math.round(((currentIndex) / queue.length) * 100);
      progressFill.style.width = pct + "%";
    }

    const idEl = document.getElementById("gr-card-id");
    const titleEl = document.getElementById("gr-title");
    if (idEl) idEl.textContent = `[Check ID: ${card.card_id || "C---"}] — ${card.automatability === "Not" ? "Not Automatable" : "Partial"} Diagnostic`;
    if (titleEl) titleEl.textContent = card.check_name || "Diagnostic Check Review";

    const guide = getSimpleGuidance(card);
    const whyEl = document.getElementById("gr-why");
    const whatEl = document.getElementById("gr-what");
    const stepsEl = document.getElementById("gr-steps");
   
    if (whyEl) whyEl.innerHTML = guide.why;
    if (whatEl) whatEl.innerHTML = guide.what;
    if (stepsEl) {
      stepsEl.innerHTML = guide.steps.map(s => `<li style="margin-bottom: 8px;">${s}</li>`).join("");
    }

    const techBlock = document.getElementById("gr-technical");
    const techBtn = document.getElementById("gr-toggle-technical");
    if (techBlock) {
      techBlock.innerHTML = getHumanReviewGuidance(card.card_id || "", card.check_name || "", card.reason || "");
      techBlock.style.display = "none";
    }
    if (techBtn) techBtn.textContent = "Show full technical protocol";

    const notesEl = document.getElementById("gr-notes");
    const urlEl = document.getElementById("gr-url");
    if (notesEl) notesEl.value = "";
    if (urlEl) urlEl.value = "";

    ["pass", "warn", "fail", "na"].forEach(v => {
      const b = document.querySelector(`#gr-verdict-buttons .vbtn.${v}`);
      if (b) b.classList.remove("selected");
    });
    const backBtn = document.getElementById("gr-btn-back");
    const nextBtn = document.getElementById("gr-btn-next");
    if (backBtn) backBtn.disabled = (currentIndex === 0);
    if (nextBtn) nextBtn.textContent = "Submit & Next →";

    const scrollBody = document.querySelector("#guided-modal .modal-content > div:nth-child(2)");
    if (scrollBody) scrollBody.scrollTop = 0;
  }

  function setVerdict(verdict) {
    activeVerdict = verdict;
    ["pass", "warn", "fail", "na"].forEach(v => {
      const b = document.querySelector(`#gr-verdict-buttons .vbtn.${v}`);
      if (b) b.classList.remove("selected");
    });
    const selectedBtn = document.querySelector(`#gr-verdict-buttons .vbtn.${verdict}`);
    if (selectedBtn) selectedBtn.classList.add("selected");
  }

  function confirmAndNext() {
    if (!activeVerdict) {
      if (typeof showToast === "function") showToast("Please select a verdict (Pass / Warn / Fail / N-A) before submitting.", "error");
      return;
    }
    const card = queue[currentIndex];
    if (card && card.card_id) {
      const cid = card.card_id;
      const notes = document.getElementById("gr-notes")?.value || "";
      const url = document.getElementById("gr-url")?.value || "";

      const pageNotes = document.getElementById(`notes-${cid}`);
      const pageUrl = document.getElementById(`url-${cid}`);
      if (pageNotes) pageNotes.value = notes;
      if (pageUrl) pageUrl.value = url;

      if (typeof selectVerdict === "function") selectVerdict(cid, activeVerdict);
      if (typeof submitVerdict === "function") submitVerdict(cid);
    }
   
    currentIndex++;
    if (currentIndex < queue.length) {
      renderCurrentStep();
    } else {
      renderComplete();
    }
  }

  function skip() {
    currentIndex++;
    if (currentIndex < queue.length) {
      renderCurrentStep();
    } else {
      renderComplete();
    }
  }

  function back() {
    if (currentIndex > 0) {
      currentIndex--;
      renderCurrentStep();
    }
  }

  function toggleTechnical() {
    const techBlock = document.getElementById("gr-technical");
    const techBtn = document.getElementById("gr-toggle-technical");
    if (techBlock && techBtn) {
      const isHidden = (techBlock.style.display === "none" || !techBlock.style.display);
      techBlock.style.display = isHidden ? "block" : "none";
      techBtn.textContent = isHidden ? "Hide full technical protocol" : "Show full technical protocol";
    }
  }

  function renderComplete() {
    const stepLabel = document.getElementById("gr-step-label");
    const progressFill = document.getElementById("gr-progress-fill");
    if (stepLabel) stepLabel.textContent = "Walkthrough Complete";
    if (progressFill) progressFill.style.width = "100%";

    const body = document.querySelector("#guided-modal .modal-content > div:nth-child(2)");
    const footer = document.querySelector("#guided-modal .modal-content > div:nth-child(3)");
   
    if (body) {
      body.innerHTML = `
      <div style="text-align:center; padding: 40px 20px;">
      <div style="font-size: 3rem; margin-bottom: 16px;"></div>
      <h2 style="font-size: 1.6rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; color: #FFFFFF;">
      Guided Walkthrough Complete
      </h2>
      <p style="font-size: 1.05rem; color: #BBBBBB; max-width: 480px; margin: 0 auto 28px; line-height: 1.6;">
      All queued diagnostic checks have been evaluated and recorded into the empirical audit repository. Your executive summary report is ready for review.
      </p>
      <button class="btn-primary" style="padding: 16px 28px; font-size: 1rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em;" onclick="GuidedReview.finishAndGoToReport()">
      Compile & View Final Report →
      </button>
      </div>
      `;
    }
    if (footer) footer.style.display = "none";
  }

  function finishAndGoToReport() {
    close();
    if (typeof generateFinalReport === "function") generateFinalReport();
    const reportSec = document.getElementById("report-section");
    if (reportSec) {
      reportSec.style.display = "";
      reportSec.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    // Trigger the three-step LLM synthesis NOW that human verdicts are in the DB.
    // triggerPostWizardSynthesis() is defined in studio.js and calls
    // POST /api/v1/audit/runs/{run_id}/synthesize which merges automated
    // findings + manual verdicts before running the LLM pipeline.
    if (typeof triggerPostWizardSynthesis === "function") {
      triggerPostWizardSynthesis();
    } else {
      console.warn("[GuidedReview] triggerPostWizardSynthesis not found — synthesis will not run.");
    }
  }

  function handleKeyDown(e) {
    const modal = document.getElementById("guided-modal");
    if (!modal || modal.style.display === "none") return;

    if (document.activeElement && (document.activeElement.tagName === "TEXTAREA" || document.activeElement.tagName === "INPUT")) {
      if (e.key === "Escape") document.activeElement.blur();
      return;
    }

    if (e.key === "1") { setVerdict("pass"); e.preventDefault(); }
    if (e.key === "2") { setVerdict("warn"); e.preventDefault(); }
    if (e.key === "3") { setVerdict("fail"); e.preventDefault(); }
    if (e.key === "4") { setVerdict("na"); e.preventDefault(); }
    if (e.key === "ArrowLeft") { back(); e.preventDefault(); }
    if (e.key === "ArrowRight" || (e.key === "Enter" && activeVerdict)) { confirmAndNext(); e.preventDefault(); }
  }

  function bindKeyboard() {
    window.addEventListener("keydown", handleKeyDown);
  }

  function unbindKeyboard() {
    window.removeEventListener("keydown", handleKeyDown);
  }

  return {
    start: start,
    close: close,
    setVerdict: setVerdict,
    confirmAndNext: confirmAndNext,
    skip: skip,
    back: back,
    toggleTechnical: toggleTechnical,
    finishAndGoToReport: finishAndGoToReport,
    getHumanReviewGuidance: getHumanReviewGuidance,
    submitInlineVerdict: submitInlineVerdict,
    FAMILY_BY_CARD_ID: FAMILY_BY_CARD_ID
  };
})();
