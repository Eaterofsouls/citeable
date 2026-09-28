// guided_review.js — Citeable Guided Manual-Review Walkthrough Controller (Category F)
// Designed as an additive, human-centered manual for non-technical executives and analysts.
// Explains clearly WHY each check matters, WHAT to look for, and HOW to verify step-by-step.
// Integrates natively with manual_review.js without altering API endpoints or database schemas.

window.GuidedReview = (function() {
  let queue = [];
  let currentIndex = 0;
  let activeVerdict = null;

  const FAMILY_BY_CARD_ID = {
    "A1_PROMPT_VALIDATION": "pre_audit",
    "B1_SCHEMA_HONESTY": "schema",
    "B2_CONTENT_ANSWERABILITY": "content",
    "B3_CLOAKING_INTENT": "schema",
    "C1_BRAND_ACCURACY": "citations",
    "C2_CONTENT_TRUSTWORTHINESS": "authority",
    "C3_CITATION_FRAMING": "citations",
    "C4_CITATION_GAP": "citations",
    "C5_SPEAKABLE": "authority",
    "D1_LLMS_TXT_REVIEW": "synthesis",
    "D2_ROOT_CAUSE_DIAGNOSIS": "synthesis"
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

  const CLAIM_TO_QUESTION = {
    "C052": "B2_CONTENT_ANSWERABILITY",
    "C053": "B1_SCHEMA_HONESTY",
    "C054": "B1_SCHEMA_HONESTY",
    "C056": "C2_CONTENT_TRUSTWORTHINESS",
    "C058": "B2_CONTENT_ANSWERABILITY",
    "C061": "B2_CONTENT_ANSWERABILITY",
    "C062": "C2_CONTENT_TRUSTWORTHINESS",
    "C072": "A1_PROMPT_VALIDATION",
    "C073": "C4_CITATION_GAP",
    "C074": "C1_BRAND_ACCURACY",
    "C077": "C1_BRAND_ACCURACY",
    "C078": "C2_CONTENT_TRUSTWORTHINESS",
    "C079": "C5_SPEAKABLE",
    "C082": "C4_CITATION_GAP",
    "C090": "D2_ROOT_CAUSE_DIAGNOSIS"
  };

  // Per-card guidance, keyed by real card_id and Track B question_id
  const CARD_GUIDANCE = {
    // Track B Question IDs
    A1_PROMPT_VALIDATION: {
      question: "Do the test prompts accurately represent how your target audience would ask AI about your brand/product?",
      why: "Validates if the queries match real user intent.",
      steps: ["Review the test prompts provided in the audit."],
      structured_output: {},
      maps_to_claims: ["C072", "C073"]
    },
    B1_SCHEMA_HONESTY: {
      question: "Compare the JSON-LD claims below with the visible page content. Are all schema claims truthful and verifiable on the page?",
      why: "Ensures structured data matches visible content.",
      steps: ["Check schema facts against page text."],
      structured_output: {},
      maps_to_claims: ["C053","C054"]
    },
    B2_CONTENT_ANSWERABILITY: {
      question: "Read the extracted lead text below. Could an AI model answer a user's question about your brand using ONLY this text?",
      why: "Ensures content is effectively accessible.",
      steps: ["Read extracted text to check for context completeness."],
      structured_output: {},
      maps_to_claims: ["C052", "C058", "C061"]
    },
    B3_CLOAKING_INTENT: {
      question: "The automated scan detected differences between browser and bot versions of your page. Is this intentional or a technical issue?",
      why: "Detects potentially harmful crawler discrepancies.",
      steps: ["Investigate the source of cloaking."],
      structured_output: {},
      maps_to_claims: ["C052"],
      conditional: true
    },
    C1_BRAND_ACCURACY: {
      question: "Review the AI-generated answers below. Are there any factual errors about your brand, products, or services?",
      why: "Identifies incorrect LLM beliefs about the brand.",
      steps: ["Review facts in the generated answers."],
      structured_output: {},
      maps_to_claims: ["C074", "C077"]
    },
    C2_CONTENT_TRUSTWORTHINESS: {
      question: "Does the page demonstrate first-hand expertise, authoritative sourcing, and editorial trustworthiness (E-E-A-T)?",
      why: "Determines E-E-A-T signals.",
      steps: ["Evaluate page content for authority markers."],
      structured_output: {},
      maps_to_claims: ["C056", "C062", "C078"]
    },
    C3_CITATION_FRAMING: {
      question: "Review how your brand is framed in AI citations. Is the sentiment accurate and the context appropriate?",
      why: "Evaluates qualitative context of citations.",
      steps: ["Analyze sentiment of the citations."],
      structured_output: {},
      maps_to_claims: ["C077"],
      conditional: true
    },
    C4_CITATION_GAP: {
      question: "Your brand was NOT cited in some AI responses. Review the competitor domains that WERE cited. What content gaps might explain this?",
      why: "Reveals competitive content advantages.",
      steps: ["Compare your content against cited competitors."],
      structured_output: {},
      maps_to_claims: ["C073", "C082"],
      conditional: true
    },
    C5_SPEAKABLE: {
      question: "Review the speakable markup found on the page. Is the text suitable for voice assistants to read aloud?",
      why: "Ensures audio format viability.",
      steps: ["Read markup aloud to check fluency."],
      structured_output: {},
      maps_to_claims: ["C079"],
      conditional: true
    },
    D1_LLMS_TXT_REVIEW: {
      question: "Review the llms.txt file content. Does it accurately summarize your site for AI consumption?",
      why: "Verifies the AI summary file.",
      steps: ["Read llms.txt for completeness and accuracy."],
      structured_output: {},
      maps_to_claims: ["C082"],
      conditional: true
    },
    D2_ROOT_CAUSE_DIAGNOSIS: {
      question: "Based on everything you've reviewed, write a 2-3 sentence root cause diagnosis explaining WHY your brand is/isn't appearing correctly in AI answers.",
      why: "Synthesizes all findings into an actionable conclusion.",
      steps: ["Summarize the audit findings."],
      structured_output: {},
      maps_to_claims: ["C090"]
    },

    // Specific 14 Check Code Instructions
    C052: {
      question: "Are critical JavaScript or CSS assets blocked by crawler directives or CDN challenges?",
      why: "If AI rendering bots cannot load scripts or stylesheets, your page may appear completely blank or broken to RAG extractors.",
      steps: [
        "Inspect robots.txt to ensure CSS and JS endpoints are not disallowed.",
        "Verify that core page content renders in raw HTML without requiring client-side JS execution."
      ],
      structured_output: {},
      maps_to_claims: ["C052"]
    },
    C053: {
      question: "Compare the JSON-LD schema with the visible page content. Are all claims truthful and verifiable?",
      why: "AI engines and search algorithms penalize sites that claim features, ratings, or facts in schema that do not appear on the visible page.",
      steps: [
        "Inspect schema blocks (Organization, Product, FAQ, Article).",
        "Compare schema properties directly with on-page text to ensure 100% semantic honesty."
      ],
      structured_output: {},
      maps_to_claims: ["C053", "C054"]
    },
    C056: {
      question: "Is your brand and product entity clearly disambiguated from similarly named concepts or competitors?",
      why: "LLMs easily conflate brands with common nouns or similar company names, leading to hallucinated or misattributed answers.",
      steps: [
        "Verify schema includes sameAs links to official Wikidata, LinkedIn, or Crunchbase profiles.",
        "Ensure introductory page paragraphs clearly define the entity category and distinct brand identity."
      ],
      structured_output: {},
      maps_to_claims: ["C056"]
    },
    C058: {
      question: "Is critical product or brand information trapped inside images, charts, or video without text fallbacks?",
      why: "AI models primarily parse textual DOM elements; text flattened inside graphic banners or videos is invisible to retrieval bots.",
      steps: [
        "Review key diagrams, infographics, and pricing charts.",
        "Ensure all critical data points have corresponding HTML text, captions, or descriptive alt text."
      ],
      structured_output: {},
      maps_to_claims: ["C058"]
    },
    C061: {
      question: "Is the page DOM layout organized so AI scrapers can extract core content without distraction?",
      why: "Deep DOM nesting, interstitials, cookie banners, and excessive boilerplate dilute token density in LLM context windows.",
      steps: [
        "Check that main informational content resides inside semantic tags (<main>, <article>).",
        "Verify that popups and boilerplate banners do not push primary answer text down the page."
      ],
      structured_output: {},
      maps_to_claims: ["C061"]
    },
    C062: {
      question: "Does the page demonstrate credible E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness)?",
      why: "Generative engines favor sources with verified author credentials, transparent editorial standards, and authoritative citations.",
      steps: [
        "Inspect author bylines, expert bios, and publication dates.",
        "Verify clear links to about pages, corporate disclosures, and verifiable methodology."
      ],
      structured_output: {},
      maps_to_claims: ["C062"]
    },
    C072: {
      question: "Do the test prompts accurately reflect how prospective buyers query AI assistants about your market?",
      why: "Testing visibility on artificial or narrow prompts produces misleading audit scores.",
      steps: [
        "Review the prompt set used in this audit.",
        "Confirm the queries represent realistic conversational queries across discovery, comparison, and evaluation."
      ],
      structured_output: {},
      maps_to_claims: ["C072"]
    },
    C073: {
      question: "Why was your brand cited or omitted in AI engine responses (Causal Attribution)?",
      why: "AI providers do not expose ranking algorithms; diagnosing whether Access, Content, or Authority caused omission is essential to prioritize fixes.",
      steps: [
        "Review automated findings: did crawler access fail, schema fail, or extractability score drop?",
        "Compare against cited competitors to determine whether they hold content or domain authority advantages.",
        "Record the primary failure layer (Access, Content, or Authority) in your notes."
      ],
      structured_output: {},
      maps_to_claims: ["C073"]
    },
    C074: {
      question: "Did AI engines hallucinate features, pricing, or capabilities when answering about your brand?",
      why: "Hallucinated answers mislead prospective customers and damage market perception.",
      steps: [
        "Read the generated AI answers carefully.",
        "Flag any inaccurate product attributes, fake pricing, or fabricated partnership claims."
      ],
      structured_output: {},
      maps_to_claims: ["C074"]
    },
    C077: {
      question: "How is your brand framed in AI responses? Is the sentiment accurate, fair, and authoritative?",
      why: "Even when cited, negative or secondary framing (e.g. 'expensive alternative', 'outdated') depresses conversion.",
      steps: [
        "Examine the tone, adjectives, and competitive positioning used by the AI engine.",
        "Document any unfair framing or outdated market perceptions in your notes."
      ],
      structured_output: {},
      maps_to_claims: ["C077"]
    },
    C078: {
      question: "Does the AI engine generate a zero-click answer that satisfies user intent without sending traffic to your site?",
      why: "Direct zero-click answers replace website visits unless your brand is established as the definitive authority.",
      steps: [
        "Evaluate if the AI summary answers the query completely without encouraging click-through.",
        "Check if structured schema or actionable takeaways encourage navigation to your domain."
      ],
      structured_output: {},
      maps_to_claims: ["C078"]
    },
    C079: {
      question: "Is content structured and marked up for voice assistants to read aloud cleanly (Speakable Schema)?",
      why: "Voice assistants require concise, conversational 2-3 sentence answers without markdown or table noise.",
      steps: [
        "Inspect SpeakableSpecification markup or lead summary paragraphs.",
        "Read the passage aloud to confirm natural syntax and conversational flow."
      ],
      structured_output: {},
      maps_to_claims: ["C079"]
    },
    C082: {
      question: "Which third-party sources (review platforms, trade media, aggregators) are winning citations instead of your brand?",
      why: "AI engines often prioritize third-party consensus (G2, Trustpilot, trade media, Wikipedia) over self-published corporate claims.",
      steps: [
        "Review the third-party domains cited in AI answers where your domain was omitted.",
        "Identify what makes their coverage authoritative (comparative tables, user reviews, neutral tone).",
        "Formulate a digital PR strategy to secure brand inclusion on winning third-party platforms."
      ],
      structured_output: {},
      maps_to_claims: ["C082"]
    },
    C090: {
      question: "Based on all findings and citation data, what is your synthesized Root Cause Diagnosis?",
      why: "Connecting isolated findings (low DR, schema issues, crawler rules) into a unified narrative guides executive remediation.",
      steps: [
        "Synthesize technical audit findings with real-time AI citation performance.",
        "Identify whether the primary barrier is Crawl Access, Content Quality, or Off-Page Authority.",
        "Write a 2-3 sentence root cause diagnosis to guide the remediation roadmap."
      ],
      structured_output: {},
      maps_to_claims: ["C090"]
    }
  };

  const FALLBACK_GUIDANCE = {
    question: "Does this check hold up when you look at the actual page?",
    why: "This is a check our automated scan flagged for a human to confirm — it's the kind of judgment call a script can't make reliably on its own.",
    steps: [
      "Open the page or setting this check refers to (see the reference below).",
      "Compare what you see against what the check is asking about.",
      "Use your judgment: does it look correct, borderline, or clearly broken?"
    ]
  };

  function getSimpleGuidance(card) {
    if (!card) return FALLBACK_GUIDANCE;
    const cid = card.card_id;
    if (cid && CARD_GUIDANCE[cid]) {
      return CARD_GUIDANCE[cid];
    }
    const mapped = cid ? CLAIM_TO_QUESTION[cid] : null;
    if (mapped && CARD_GUIDANCE[mapped]) {
      return CARD_GUIDANCE[mapped];
    }
    if (card.what_to_look_for && card.title && card.title !== "Expert Human Inspection Required") {
      return {
        question: card.title.endsWith("?") ? card.title : `${card.title}?`,
        why: card.what_to_look_for,
        steps: [card.how_to_fill || "Inspect on-page evidence and record observations."]
      };
    }
    return FALLBACK_GUIDANCE;
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

  // Inline Wizard State Management (Task 14)
  let inlineCards = [];
  let inlineOpts = {};
  let inlineCurrentIndex = 0;
  let inlineVerdicts = {}; // cardId -> { verdict, notes }

  async function submitInlineVerdict(cardId, verdict, opts) {
    const notesEl = document.getElementById(`notes-${cardId}`);
    const notes = notesEl && notesEl.value.trim() ? notesEl.value.trim() : `Human qualitative verification recorded as ${verdict.toUpperCase()}`;
    const runId = (opts && opts.runId) || window.currentRunId || "";
    const severity = verdict === 'pass' ? 'info' : (verdict === 'warn' ? 'warning' : 'error');

    const mappedQid = CLAIM_TO_QUESTION[cardId] || cardId;
    const questionDef = CARD_GUIDANCE[cardId] || CARD_GUIDANCE[mappedQid] || {};
    const maps_to_claims = questionDef.maps_to_claims || (cardId.startsWith("C") ? [cardId] : []);

    try {
      if (runId && typeof AreosAPI !== "undefined") {
        const headers = (typeof getAuthHeaders === "function") ? getAuthHeaders({ "Content-Type": "application/json" }) : { "Content-Type": "application/json" };
        const res = await AreosAPI.fetch(`/api/v1/audit/runs/${runId}/observations`, {
          method: "POST",
          headers: headers,
          body: JSON.stringify({
            question_id: mappedQid,
            maps_to_claims: maps_to_claims,
            structured_data: {},
            severity: severity,
            diagnosis_text: notes
          })
        });
        if (!res.ok) {
          if (typeof AreosAPI !== "undefined" && AreosAPI.notify) AreosAPI.notify("Failed to save evaluation. Please retry.");
          return;
        }
      }

      if (opts && typeof opts.onVerdict === "function") {
        opts.onVerdict(cardId, verdict);
      }
    } catch (error) {
      console.error("Error saving verdict:", error);
      if (typeof AreosAPI !== "undefined" && AreosAPI.notify) AreosAPI.notify("Network error while submitting evaluation.");
    }
  }

  function goToInlineStep(idx) {
    if (idx >= 0 && idx < inlineCards.length) {
      inlineCurrentIndex = idx;
      renderInlineCard();
    }
  }

  function prevInlineStep() {
    if (inlineCurrentIndex > 0) {
      inlineCurrentIndex--;
      renderInlineCard();
    }
  }

  function nextInlineStep() {
    const currentCard = inlineCards[inlineCurrentIndex];
    if (currentCard && !inlineVerdicts[currentCard.card_id]) {
      if (typeof AreosAPI !== 'undefined' && AreosAPI.notify) {
        AreosAPI.notify("Please select a verdict (Pass, Warn, or Fail) to continue.");
      } else {
        alert("Please select a verdict (Pass, Warn, or Fail) to continue.");
      }
      return;
    }

    if (inlineCurrentIndex < inlineCards.length - 1) {
      inlineCurrentIndex++;
      renderInlineCard();
    } else {
      const allAnswered = inlineCards.every(c => !!inlineVerdicts[c.card_id]);
      if (allAnswered) {
        finishAndGoToReport();
      } else {
        const firstUnanswered = inlineCards.findIndex(c => !inlineVerdicts[c.card_id]);
        if (firstUnanswered !== -1) {
          inlineCurrentIndex = firstUnanswered;
          renderInlineCard();
        }
      }
    }
  }

  function renderInlineWizard(cards, opts) {
    const cEl = document.querySelector(opts.container || "#wizard-list");
    if (!cEl) return;

    inlineCards = cards;
    inlineOpts = opts;
    inlineCurrentIndex = 0;

    // Seed existing verdicts if present
    inlineCards.forEach((c) => {
      if (c.verdicts && c.verdicts.length > 0) {
        const v = c.verdicts[0];
        inlineVerdicts[c.card_id] = {
          verdict: (v.verdict || v).toLowerCase(),
          notes: v.notes || v.diagnosis_text || ""
        };
      }
    });

    // Start on first unanswered card if any
    const firstUnanswered = inlineCards.findIndex(c => !inlineVerdicts[c.card_id]);
    if (firstUnanswered !== -1) {
      inlineCurrentIndex = firstUnanswered;
    }

    renderInlineCard();
  }

  function renderInlineCard() {
    const cEl = document.querySelector(inlineOpts.container || "#wizard-list");
    if (!cEl) return;
    cEl.innerHTML = "";

    const cards = inlineCards;
    const idx = inlineCurrentIndex;
    const wiz = cards[idx];
    if (!wiz) return;

    const domainInput = document.getElementById("domain-input");
    const domain = domainInput ? domainInput.value.trim() : "";
    const siteUrl = domain ? (domain.startsWith("http") ? domain : `https://${domain}`) : null;

    const guide = getSimpleGuidance(wiz);
    const stepsHtml = (guide.steps || []).map(s => `<li>${s}</li>`).join("");
    const checkRef = escapeHtml((wiz.reason || wiz.check_name || "QUALITATIVE_EVALUATION")).replace(/^Check code\(s\) fired:\s*/i, "");

    const saved = inlineVerdicts[wiz.card_id] || null;
    const savedVerdict = saved ? saved.verdict : null;
    const savedNotes = saved ? saved.notes : "";

    const wizCard = document.createElement("div");
    wizCard.className = "gr-card";
    wizCard.id = `wizard-card-${wiz.card_id}`;

    let prepopulatedHtml = "";
    const auditResult = (window.AreosContext && window.AreosContext.auditResult) || {};
    const effectiveQid = CLAIM_TO_QUESTION[wiz.card_id] || wiz.card_id;
    if ((effectiveQid === "B1_SCHEMA_HONESTY" || wiz.card_id === "C053") && auditResult.schema_claims) {
      prepopulatedHtml = `<div class="gr-card-prepopulate"><strong>Pre-populated Data (Schema Claims):</strong>\n${escapeHtml(typeof auditResult.schema_claims === 'string' ? auditResult.schema_claims : JSON.stringify(auditResult.schema_claims, null, 2))}</div>`;
    } else if ((effectiveQid === "B2_CONTENT_ANSWERABILITY" || wiz.card_id === "C052") && auditResult.extracted_lead_text) {
      prepopulatedHtml = `<div class="gr-card-prepopulate"><strong>Pre-populated Data (Extracted Lead Text):</strong>\n${escapeHtml(auditResult.extracted_lead_text)}</div>`;
    } else if ((effectiveQid === "C1_BRAND_ACCURACY" || wiz.card_id === "C077" || wiz.card_id === "C074") && auditResult.citation_result && auditResult.citation_result.full_responses) {
      prepopulatedHtml = `<div class="gr-card-prepopulate"><strong>Pre-populated Data (Full Responses):</strong>\n${escapeHtml(typeof auditResult.citation_result.full_responses === 'string' ? auditResult.citation_result.full_responses : JSON.stringify(auditResult.citation_result.full_responses, null, 2))}</div>`;
    } else if ((effectiveQid === "C4_CITATION_GAP" || wiz.card_id === "C073" || wiz.card_id === "C082") && auditResult.citation_analytics && auditResult.citation_analytics.competitor_domains) {
      prepopulatedHtml = `<div class="gr-card-prepopulate"><strong>Pre-populated Data (Competitor Domains):</strong>\n${escapeHtml(typeof auditResult.citation_analytics.competitor_domains === 'string' ? auditResult.citation_analytics.competitor_domains : JSON.stringify(auditResult.citation_analytics.competitor_domains, null, 2))}</div>`;
    }

    const exampleHtml = guide.example
      ? `<div class="gr-card-example">
           <strong>Try it yourself</strong>
           ${escapeHtml(guide.example.replace(/\{\{domain\}\}/g, domain || "yourdomain.com"))}
         </div>`
      : "";

    const dotsHtml = cards.map((c, i) => {
      const isDone = !!inlineVerdicts[c.card_id];
      const isCurrent = i === idx;
      let cls = "";
      if (isDone) cls += " is-done";
      if (isCurrent) cls += " is-current";
      return `<button type="button" class="gr-dot-btn${cls}" onclick="window.GuidedReview.goToInlineStep(${i})" title="Question ${i + 1} of ${cards.length}: ${isDone ? 'Evaluated' : 'Unanswered'}" aria-label="Question ${i + 1} of ${cards.length}"></button>`;
    }).join("");

    const isLastCard = idx === cards.length - 1;
    const allAnswered = cards.every(c => !!inlineVerdicts[c.card_id]);

    wizCard.innerHTML = `
      <div class="gr-question-progress">
        <span>Question ${idx + 1} of ${cards.length}</span>
        <div class="gr-question-dots">
          ${dotsHtml}
        </div>
      </div>

      ${prepopulatedHtml}

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

      ${siteUrl ? `<a class="gr-view-page-btn" href="${siteUrl}" target="_blank" rel="noopener">👀 View the site we're asking about</a>` : ""}

      <input type="text" class="verdict-notes" id="notes-${wiz.card_id}" value="${escapeHtml(savedNotes)}" placeholder="Add an observation note (optional)...">

      <div class="gr-verdict-row" style="margin-bottom:18px;">
        <button type="button" class="btn-verdict gr-verdict-btn yes ${savedVerdict === 'pass' ? 'selected' : ''}" data-card-id="${wiz.card_id}" data-verdict="pass">✓ Pass</button>
        <button type="button" class="btn-verdict gr-verdict-btn partly ${savedVerdict === 'warn' ? 'selected' : ''}" data-card-id="${wiz.card_id}" data-verdict="warn">⚠ Warn</button>
        <button type="button" class="btn-verdict gr-verdict-btn no ${savedVerdict === 'fail' ? 'selected' : ''}" data-card-id="${wiz.card_id}" data-verdict="fail">✗ Fail</button>
      </div>

      <div class="gr-wizard-nav" style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border-default); padding-top:16px; margin-top:16px; flex-wrap:wrap; gap:12px;">
        <button type="button" class="btn-secondary" ${idx === 0 ? 'disabled style="opacity:0.4; cursor:not-allowed;"' : ''} onclick="window.GuidedReview.prevInlineStep()">
          &larr; Previous Question
        </button>

        <div id="inline-verdict-status" style="font-size:0.85rem; font-weight:600;">
          ${savedVerdict ? `<span class="status-pill success text-xs">Evaluated: ${savedVerdict.toUpperCase()}</span>` : `<span style="color:var(--text-tertiary);">Select verdict to continue</span>`}
        </div>

        <button type="button" class="btn-primary" onclick="window.GuidedReview.nextInlineStep()">
          ${isLastCard ? (allAnswered ? 'Complete Review & View Report &rarr;' : 'Finish Review &rarr;') : 'Next Question &rarr;'}
        </button>
      </div>

      <div class="gr-card-footnote" title="System check ${escapeHtml(wiz.card_id || "")}">Diagnostic Verification &middot; ${checkRef}</div>
    `;

    const passBtn = wizCard.querySelector(".yes");
    const warnBtn = wizCard.querySelector(".partly");
    const failBtn = wizCard.querySelector(".no");

    const onSelect = (v) => {
      wizCard.querySelectorAll(".gr-verdict-btn").forEach(b => b.classList.remove("selected"));
      if (v === 'pass' && passBtn) passBtn.classList.add("selected");
      if (v === 'warn' && warnBtn) warnBtn.classList.add("selected");
      if (v === 'fail' && failBtn) failBtn.classList.add("selected");

      const notes = document.getElementById(`notes-${wiz.card_id}`)?.value || "";
      inlineVerdicts[wiz.card_id] = { verdict: v, notes: notes };

      const statusEl = document.getElementById("inline-verdict-status");
      if (statusEl) statusEl.innerHTML = `<span class="status-pill success text-xs">Evaluated: ${v.toUpperCase()} (Saved)</span>`;

      const dots = wizCard.querySelectorAll(".gr-dot-btn");
      if (dots[idx]) dots[idx].classList.add("is-done");

      submitInlineVerdict(wiz.card_id, v, inlineOpts);
    };

    if (passBtn) passBtn.onclick = () => onSelect('pass');
    if (warnBtn) warnBtn.onclick = () => onSelect('warn');
    if (failBtn) failBtn.onclick = () => onSelect('fail');

    const notesInput = document.getElementById(`notes-${wiz.card_id}`);
    if (notesInput) {
      notesInput.addEventListener('input', () => {
        if (inlineVerdicts[wiz.card_id]) {
          inlineVerdicts[wiz.card_id].notes = notesInput.value;
        }
      });
    }

    cEl.appendChild(wizCard);
  }

  function isQuestionVisible(questionId) {
    const qid = CLAIM_TO_QUESTION[questionId] || questionId;
    const mode = window.AreosContext && window.AreosContext.reviewMode ? window.AreosContext.reviewMode : 'full';
    if (mode === 'express') {
      return ['B2_CONTENT_ANSWERABILITY', 'C1_BRAND_ACCURACY', 'C2_CONTENT_TRUSTWORTHINESS', 'D2_ROOT_CAUSE_DIAGNOSIS'].includes(qid);
    }
    
    // If it's a backend triggered claim card (e.g. C073, C082, C090), it was already triggered by report.py
    if (typeof questionId === "string" && questionId.startsWith("C0")) {
      return true;
    }

    const auditResult = (window.AreosContext && window.AreosContext.auditResult) || {};
    
    if (qid === 'B3_CLOAKING_INTENT') {
      const findings = auditResult.findings || [];
      return findings.includes('CLOAKING_DETECTED') || findings.includes('CLOAKING_MINOR');
    }
    if (qid === 'C3_CITATION_FRAMING') {
      return (auditResult.cited_count || 0) > 0;
    }
    if (qid === 'C4_CITATION_GAP') {
      const cited_count = auditResult.cited_count || 0;
      const total_prompts = auditResult.total_prompts || 0;
      return cited_count < total_prompts;
    }
    if (qid === 'C5_SPEAKABLE') {
      return auditResult.speakable_found === true;
    }
    if (qid === 'D1_LLMS_TXT_REVIEW') {
      return auditResult.llms_exists === true;
    }
    
    return true;
  }

  function start(cards, opts) {
    if (!window.AreosContext || !window.AreosContext.auditResult) {
      console.warn("Cannot start wizard: window.AreosContext.auditResult is not populated.");
      return;
    }

    if (!cards || !Array.isArray(cards)) {
      cards = window.currentCards || [];
    }
    
    cards = cards.filter(c => isQuestionVisible(c.card_id));
    
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
   
    if (whyEl) whyEl.textContent = guide.why;
    if (whatEl) whatEl.textContent = guide.what;
    if (stepsEl) {
      stepsEl.innerHTML = (guide.steps || []).map(s => `<li style="margin-bottom: 8px;">${typeof escapeHtml === 'function' ? escapeHtml(s) : s}</li>`).join("");
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
    if (nextBtn) nextBtn.textContent = "Submit & Next";

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
        <div style="width: 56px; height: 56px; border-radius: 50%; background: var(--status-success-bg); border: 2px solid var(--status-success-border); display: flex; align-items: center; justify-content: center; margin: 0 auto 18px auto;">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--status-success)" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
        </div>
        <h2 style="font-size: 1.6rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; color: var(--text-primary);">
          Guided Walkthrough Complete
        </h2>
        <p style="font-size: 1.05rem; color: var(--text-secondary); max-width: 480px; margin: 0 auto 28px; line-height: 1.6;">
          All queued diagnostic checks have been evaluated and recorded into the empirical audit repository. Your executive summary report is ready for review.
        </p>
        <button class="btn-primary" style="padding: 14px 28px; font-size: 0.95rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em;" onclick="GuidedReview.finishAndGoToReport()">
          Compile & View Final Report
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
    goToInlineStep: goToInlineStep,
    prevInlineStep: prevInlineStep,
    nextInlineStep: nextInlineStep,
    isQuestionVisible: isQuestionVisible,
    FAMILY_BY_CARD_ID: FAMILY_BY_CARD_ID
  };
})();
