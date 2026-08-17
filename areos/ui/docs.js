/**
 * docs.js — Citeable documentation viewer.
 *
 * Responsibilities:
 *   1. Fetch and render the public documentation (Markdown -> HTML via marked.js).
 *   2. Render any ```mermaid fenced code blocks as diagrams.
 *   3. Assign stable heading IDs and build a scroll-spied "On This Page" TOC.
 *   4. If an authenticated session token is present, transparently include the
 *      internal documentation supplement alongside the public content.
 *
 * This file intentionally has no dependency on any other Citeable UI module —
 * it only needs marked.js and mermaid.js (both loaded from CDN in docs.html)
 * plus the shared `sessionStorage` auth-token convention used across the app.
 */

(() => {
  'use strict';

  const EXTERNAL_DOC_URL = 'docs/external.md';
  const INTERNAL_DOC_URL = 'docs/internal.md';
  const AUTH_TOKEN_KEY = 'areos_api_token';
  const TOC_HEADING_SELECTOR = 'h2, h3';
  const SCROLL_OFFSET_PX = 24; // breathing room above a heading when it's scrolled to

  // Accordion motion — reuses the app's existing design tokens
  // (--duration-slow / --ease-standard from index.css) rather than
  // inventing new timing values, so this page's motion matches the rest
  // of the app instead of feeling like a separate, bolted-on component.
  const SECTION_ANIMATION_MS = 400; // matches --duration-slow
  const SECTION_EASING = 'cubic-bezier(0.2, 0.8, 0.2, 1)'; // matches --ease-standard
  const STAGGER_STEP_MS = 60;
  const STAGGER_MAX_INDEX = 8; // caps total stagger delay so a long doc's
                                 // reveal never drags past ~500ms
  const REDUCED_MOTION_QUERY = window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)')
    : null;

  /**
   * Web Animations API calls are NOT covered by this app's site-wide CSS
   * reduced-motion override (that only zeroes CSS transition/animation
   * durations) — so anywhere this file drives motion via `element.animate()`
   * must check this explicitly.
   */
  function prefersReducedMotion() {
    return !!(REDUCED_MOTION_QUERY && REDUCED_MOTION_QUERY.matches);
  }

  // ---------------------------------------------------------------------
  // Markdown fetching
  // ---------------------------------------------------------------------

  /**
   * Fetch a Markdown file as plain text. Never throws — returns an object
   * describing success/failure so callers can degrade gracefully.
   */
  async function fetchMarkdown(url) {
    try {
      const res = await fetch(url, { credentials: 'same-origin' });
      if (!res.ok) {
        return { ok: false, status: res.status, text: '' };
      }
      const text = await res.text();
      return { ok: true, status: res.status, text };
    } catch (err) {
      return { ok: false, status: 0, text: '', error: err };
    }
  }

  /**
   * Returns the current admin/session token, or null if none is set.
   * Presence of a token is the sole (client-side) signal used to decide
   * whether the internal documentation supplement is also loaded.
   */
  function getSessionToken() {
    try {
      return sessionStorage.getItem(AUTH_TOKEN_KEY) || null;
    } catch (err) {
      return null; // sessionStorage unavailable (e.g. privacy mode) — degrade to public-only
    }
  }

  /**
   * Builds the full Markdown source to render: public docs, plus the
   * internal supplement appended seamlessly when a session token is present.
   * There is no visible indicator of which branch was taken — the internal
   * content, when present, reads as a continuation of the same document.
   */
  async function loadDocumentationSource() {
    const external = await fetchMarkdown(EXTERNAL_DOC_URL);
    let combined = external.ok
      ? external.text
      : '## Documentation Unavailable\n\nThe documentation could not be loaded right now. Please try again shortly.';

    const token = getSessionToken();
    if (token) {
      const internal = await fetchMarkdown(INTERNAL_DOC_URL);
      if (internal.ok && internal.text.trim()) {
        combined += `\n\n${internal.text}`;
      }
      // A failed internal fetch is silently ignored — the public
      // documentation must never be affected by it.
    }

    return combined;
  }

  // ---------------------------------------------------------------------
  // Markdown rendering
  // ---------------------------------------------------------------------

  /** Configures marked.js once, defensively (CDN load can fail or race). */
  function configureMarked() {
    if (!window.marked) return false;
    try {
      window.marked.setOptions({
        gfm: true,
        breaks: false,
        headerIds: false, // we assign our own stable IDs after render
        mangle: false,
      });
      return true;
    } catch (err) {
      return false;
    }
  }

  /** Renders Markdown to an HTML string. Falls back to escaped <pre> if marked failed to load. */
  function renderMarkdownToHtml(markdown) {
    if (window.marked && typeof window.marked.parse === 'function') {
      try {
        return window.marked.parse(markdown);
      } catch (err) {
        // fall through to plaintext fallback below
      }
    }
    const escaped = markdown
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    return `<pre>${escaped}</pre>`;
  }

  // ---------------------------------------------------------------------
  // Mermaid diagrams
  // ---------------------------------------------------------------------

  /**
   * marked.js renders ```mermaid fenced blocks as <pre><code class="language-mermaid">.
   * Mermaid expects plain <div class="mermaid">...</div> containers to render into.
   * This converts every such block in place, then (if mermaid.js loaded) initializes it.
   */
  function renderMermaidDiagrams(containerEl) {
    const codeBlocks = containerEl.querySelectorAll('pre > code.language-mermaid');
    if (codeBlocks.length === 0) return;

    codeBlocks.forEach((codeEl) => {
      const pre = codeEl.parentElement;
      const diagramSource = codeEl.textContent;
      const wrapper = document.createElement('div');
      wrapper.className = 'mermaid';
      wrapper.textContent = diagramSource;
      pre.replaceWith(wrapper);
    });

    if (!window.mermaid) return; // CDN blocked/unavailable — leave raw diagram source visible

    try {
      // A custom 'base' theme, rather than mermaid's stock 'dark' preset,
      // so diagrams use Citeable's actual monochrome-plus-cyan palette instead
      // of mermaid's own blue/purple defaults.
      window.mermaid.initialize({
        startOnLoad: false,
        theme: 'base',
        securityLevel: 'strict',
        fontFamily: 'JetBrains Mono, ui-monospace, monospace',
        themeVariables: {
          background: '#000000',
          primaryColor: '#141414',
          primaryTextColor: '#ffffff',
          primaryBorderColor: '#666666',
          secondaryColor: '#141414',
          tertiaryColor: '#1a1a1a',
          lineColor: '#888888',
          textColor: '#ffffff',
          mainBkg: '#141414',
          nodeTextColor: '#ffffff',
          clusterBkg: '#0d0d0d',
          clusterBorder: '#38bdf8',
          edgeLabelBackground: '#000000',
          actorBkg: '#141414',
          actorBorder: '#666666',
          actorTextColor: '#ffffff',
          actorLineColor: '#666666',
          signalColor: '#e2e8f0',
          signalTextColor: '#ffffff',
          labelBoxBkgColor: '#141414',
          labelBoxBorderColor: '#666666',
          labelTextColor: '#ffffff',
          loopTextColor: '#ffffff',
          noteBkgColor: 'rgba(56, 189, 248, 0.1)',
          noteBorderColor: '#38bdf8',
          noteTextColor: '#ffffff',
          activationBkgColor: '#1a1a1a',
          activationBorderColor: '#38bdf8',
          sequenceNumberColor: '#000000',
        },
      });
      const diagramEls = containerEl.querySelectorAll('.mermaid');
      window.mermaid.run({ nodes: diagramEls }).catch(() => {
        // A single bad diagram must not break the rest of the page.
      });
    } catch (err) {
      // Mermaid failing to initialize should never take down the doc viewer.
    }
  }

  // ---------------------------------------------------------------------
  // Heading IDs + Table of Contents
  // ---------------------------------------------------------------------

  /** Matches the slug scheme used for the in-document cross-reference links in external.md. */
  function slugifyHeadingText(text) {
    return text
      .trim()
      .toLowerCase()
      .replace(/[^\w\s-]/g, '')
      .replace(/\s/g, '-');
  }

  /**
   * Walks every H2/H3 in the rendered content, assigns a stable, unique
   * `id`, and returns the ordered list describing them for TOC building.
   */
  function assignHeadingIds(containerEl) {
    const headings = Array.from(containerEl.querySelectorAll(TOC_HEADING_SELECTOR));
    const seen = new Map();

    return headings.map((el) => {
      const text = el.textContent || '';
      const base = slugifyHeadingText(text) || 'section';
      const count = seen.get(base) || 0;
      seen.set(base, count + 1);
      const id = count === 0 ? base : `${base}-${count}`;

      el.id = id;
      el.classList.add('docs-heading');

      return {
        id,
        text,
        level: el.tagName === 'H2' ? 2 : 3,
      };
    });
  }

  /** Renders the right-rail "On This Page" navigation from the heading list. */
  function buildTableOfContents(headings, tocNavEl) {
    tocNavEl.innerHTML = '';
    const tocAsideEl = document.getElementById('docs-toc');

    if (headings.length === 0) {
      if (tocAsideEl) tocAsideEl.style.display = 'none';
      return;
    }
    if (tocAsideEl) tocAsideEl.style.display = '';

    const fragment = document.createDocumentFragment();
    headings.forEach((h) => {
      const link = document.createElement('a');
      link.href = `#${h.id}`;
      link.textContent = h.text;
      link.className = `docs-toc-link docs-toc-level-${h.level}`;
      link.dataset.targetId = h.id;
      fragment.appendChild(link);
    });
    tocNavEl.appendChild(fragment);
  }

  /**
   * The "On This Page" panel is a native <details> element: collapsed by
   * default (a 60+ entry TOC dumped open above the content would push the
   * actual documentation off-screen on a narrow viewport), expandable on
   * tap. On wide viewports it should simply always be open.
   *
   * This is done from JS via matchMedia, rather than CSS alone, because
   * closed-<details> content visibility is enforced by an internal browser
   * mechanism that a same-specificity CSS override on the child cannot
   * reliably defeat — directly setting the `open` property is the
   * supported way to control it.
   */
  function setupResponsiveTocState(detailsEl) {
    if (!detailsEl || !window.matchMedia) return;
    const desktopQuery = window.matchMedia('(min-width: 1101px)');
    const applyState = () => {
      detailsEl.open = desktopQuery.matches;
    };
    applyState();
    if (desktopQuery.addEventListener) {
      desktopQuery.addEventListener('change', applyState);
    } else if (desktopQuery.addListener) {
      desktopQuery.addListener(applyState); // Safari < 14 fallback
    }
  }

  /** Intercepts TOC (and in-content) anchor clicks for a smooth, offset-aware scroll. */
  function setupSmoothAnchorScroll(rootEl) {
    rootEl.addEventListener('click', (event) => {
      const link = event.target.closest('a[href^="#"]');
      if (!link) return;
      const id = decodeURIComponent(link.getAttribute('href').slice(1));
      if (!id) return;
      const target = document.getElementById(id);
      if (!target) return;

      event.preventDefault();
      // The target may be inside a currently-collapsed accordion section
      // (e.g. a [\u00a7N.M] cross-reference, or a TOC entry for a
      // subsection whose parent section hasn't been opened yet) — open it
      // first so we're not scrolling toward a zero-height hidden element.
      openAncestorSection(target);
      const top = target.getBoundingClientRect().top + window.scrollY - SCROLL_OFFSET_PX;
      window.scrollTo({ top, behavior: 'smooth' });
      history.replaceState(null, '', `#${id}`);
    });
  }

  /**
   * Highlights the TOC entry for whichever heading is currently most visible,
   * using IntersectionObserver so it stays cheap on long documents.
   */
  function setupScrollSpy(headings, tocNavEl) {
    if (!('IntersectionObserver' in window) || headings.length === 0) return;

    const linkById = new Map(
      Array.from(tocNavEl.querySelectorAll('.docs-toc-link')).map((el) => [el.dataset.targetId, el])
    );

    let activeId = null;
    const setActive = (id) => {
      if (id === activeId) return;
      if (activeId && linkById.has(activeId)) linkById.get(activeId).classList.remove('active');
      if (id && linkById.has(id)) linkById.get(id).classList.add('active');
      activeId = id;
    };

    const visibleIds = new Set();
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            visibleIds.add(entry.target.id);
          } else {
            visibleIds.delete(entry.target.id);
          }
        });

        if (visibleIds.size > 0) {
          // Prefer the heading closest to the top of the viewport among visible ones.
          const topMost = headings.find((h) => visibleIds.has(h.id));
          if (topMost) setActive(topMost.id);
        }
      },
      { rootMargin: '0px 0px -70% 0px', threshold: [0, 1] }
    );

    headings.forEach((h) => {
      const el = document.getElementById(h.id);
      if (el) observer.observe(el);
    });
  }

  // ---------------------------------------------------------------------
  // Collapsible sections (accordion)
  // ---------------------------------------------------------------------

  /**
   * Restructures the flat rendered content into a set of collapsible
   * <details class="docs-section"> elements, one per top-level (H2)
   * section, so a reader sees a scannable list of section titles first
   * instead of the entire document at once.
   *
   * Built with real DOM node moves (appendChild), never by re-stringifying
   * innerHTML — appendChild on a node that already has a parent detaches
   * it from that parent automatically, so this is safe to run after
   * renderMermaidDiagrams() even though mermaid.run() is async and may
   * still be populating a diagram's SVG when this executes: the element
   * reference mermaid is writing into is simply relocated, not recreated.
   *
   * Anything before the first H2 (the intro paragraph and the "30-second"
   * summary table) is left exactly where it is, outside any accordion,
   * since that content is meant to always be visible.
   */
  function buildAccordionSections(containerEl) {
    const originalChildren = Array.from(containerEl.childNodes);
    const sections = [];
    let current = null;

    originalChildren.forEach((node) => {
      const isH2 = node.nodeType === 1 && node.tagName === 'H2';
      if (isH2) {
        current = { headerEl: node, bodyNodes: [] };
        sections.push(current);
      } else if (current) {
        current.bodyNodes.push(node);
      }
      // Nodes before the first H2 are never bucketed, so they're never moved.
    });

    // Fewer than 2 sections isn't worth an accordion (e.g. a render-failure
    // fallback that's just a single <pre> block) — leave content as-is.
    if (sections.length < 2) return;

    const fragment = document.createDocumentFragment();
    sections.forEach((section, idx) => {
      const details = document.createElement('details');
      details.className = 'docs-section';
      details.style.setProperty('--stagger-index', String(Math.min(idx, STAGGER_MAX_INDEX)));

      const summary = document.createElement('summary');
      summary.className = 'docs-section-summary';
      summary.setAttribute('aria-expanded', 'false');
      summary.appendChild(section.headerEl); // moves the real H2 — keeps its id + docs-heading class

      const body = document.createElement('div');
      body.className = 'docs-section-body';
      section.bodyNodes.forEach((n) => body.appendChild(n)); // moves real nodes; mermaid-safe

      details.appendChild(summary);
      details.appendChild(body);
      fragment.appendChild(details);
    });

    containerEl.appendChild(fragment);
  }

  /**
   * Animated open/close for one accordion section. Falls back to an
   * instant toggle if the user prefers reduced motion, the browser lacks
   * Element.animate(), or the caller explicitly opts out (used for the
   * "expand/collapse all" control, where animating N sections at once
   * would be more noise than polish).
   */
  function setSectionOpen(details, shouldOpen, opts) {
    const animate = !opts || opts.animate !== false;
    const body = details.querySelector(':scope > .docs-section-body');
    const summary = details.querySelector(':scope > .docs-section-summary');

    if (!body || !animate || prefersReducedMotion() || typeof body.animate !== 'function') {
      details.open = shouldOpen;
      if (summary) summary.setAttribute('aria-expanded', String(shouldOpen));
      return;
    }

    if (shouldOpen) {
      details.open = true; // must be open to measure natural height
      if (summary) summary.setAttribute('aria-expanded', 'true');
      const targetHeight = body.scrollHeight;
      body.style.overflow = 'hidden';
      const anim = body.animate(
        [
          { height: '0px', opacity: 0 },
          { height: `${targetHeight}px`, opacity: 1 },
        ],
        { duration: SECTION_ANIMATION_MS, easing: SECTION_EASING }
      );
      anim.onfinish = () => {
        body.style.height = '';
        body.style.overflow = '';
      };
    } else {
      const startHeight = body.scrollHeight;
      if (summary) summary.setAttribute('aria-expanded', 'false');
      body.style.overflow = 'hidden';
      const anim = body.animate(
        [
          { height: `${startHeight}px`, opacity: 1 },
          { height: '0px', opacity: 0 },
        ],
        { duration: SECTION_ANIMATION_MS, easing: SECTION_EASING }
      );
      anim.onfinish = () => {
        details.open = false;
        body.style.height = '';
        body.style.overflow = '';
      };
    }
  }

  /**
   * Finds the ancestor accordion section for a heading (or any element
   * inside one) and force-opens it, without animation — used right before
   * scrolling to a deep link or TOC/cross-reference target that may
   * currently be collapsed, so the browser isn't asked to scroll to a
   * zero-height hidden element.
   */
  function openAncestorSection(el) {
    if (!el) return;
    const details = el.closest('details.docs-section');
    if (details && !details.open) {
      setSectionOpen(details, true, { animate: false });
    }
  }

  /**
   * Wires up click handling for every accordion summary (with
   * preventDefault, since setSectionOpen drives `open` itself so the
   * animation can run before the state actually flips) plus the header's
   * "Expand all / Collapse all" control.
   *
   * Also listens for the native `toggle` event on each <details>, which
   * fires regardless of *how* open state changed — including the
   * browser's own find-in-page mechanism force-opening a closed section
   * to reveal a search match. That path never calls setSectionOpen(), so
   * this keeps aria-expanded and any leftover inline height style in sync
   * even when a section was opened outside this file's own code.
   */
  function setupAccordionInteractions(containerEl) {
    const sections = Array.from(containerEl.querySelectorAll('details.docs-section'));
    if (sections.length === 0) return;

    sections.forEach((details) => {
      const summary = details.querySelector(':scope > .docs-section-summary');
      const body = details.querySelector(':scope > .docs-section-body');
      if (!summary) return;

      summary.addEventListener('click', (event) => {
        event.preventDefault();
        setSectionOpen(details, !details.open);
      });

      details.addEventListener('toggle', () => {
        summary.setAttribute('aria-expanded', String(details.open));
        if (body) {
          body.style.height = '';
          body.style.overflow = '';
        }
      });
    });

    const toggleAllBtn = document.getElementById('docs-toggle-all');
    if (!toggleAllBtn) return;
    toggleAllBtn.addEventListener('click', () => {
      const anyOpen = sections.some((d) => d.open);
      const nextState = !anyOpen; // if any are open, this click collapses all; else expands all
      sections.forEach((d) => setSectionOpen(d, nextState, { animate: false }));
      toggleAllBtn.textContent = nextState ? 'Collapse all sections' : 'Expand all sections';
      toggleAllBtn.setAttribute('aria-expanded', String(nextState));
    });
  }

  // ---------------------------------------------------------------------
  // Orchestration
  // ---------------------------------------------------------------------

  async function initDocsViewer() {
    const contentEl = document.getElementById('docs-content');
    const tocNavEl = document.getElementById('docs-toc-nav');
    if (!contentEl) return;

    configureMarked();

    let markdown;
    try {
      markdown = await loadDocumentationSource();
    } catch (err) {
      contentEl.innerHTML = '<div class="docs-error">Documentation could not be loaded. Please refresh the page.</div>';
      return;
    }

    try {
      contentEl.innerHTML = renderMarkdownToHtml(markdown);
    } catch (err) {
      contentEl.innerHTML = '<div class="docs-error">Documentation could not be rendered. Please refresh the page.</div>';
      return;
    }

    try {
      renderMermaidDiagrams(contentEl);
    } catch (err) {
      // Diagram rendering is best-effort; the surrounding text content still stands.
    }

    try {
      // Assign heading IDs BEFORE restructuring into an accordion, so the
      // TOC and slug scheme are built from the exact same elements that
      // then get moved into <details> wrappers — id/classList travel with
      // a node when it's moved, so order here doesn't strictly matter for
      // correctness, but doing IDs first keeps this block's data flow
      // easy to follow top-to-bottom.
      const headings = assignHeadingIds(contentEl);
      if (tocNavEl) {
        buildTableOfContents(headings, tocNavEl);
        setupScrollSpy(headings, tocNavEl);
        setupResponsiveTocState(document.querySelector('.docs-toc-details'));
      }
      setupSmoothAnchorScroll(document.body);

      // Collapsible sections are a progressive enhancement layered on top
      // of the fully-rendered, already-correct flat document — if this
      // throws, the reader still has the complete (just non-collapsible)
      // content from the try block above, not a blank page.
      buildAccordionSections(contentEl);
      setupAccordionInteractions(contentEl);

      // Deep-link support: if the page was loaded with a hash, open its
      // section (it starts collapsed like every other section) and scroll
      // to it once content (and heading IDs) actually exist.
      if (window.location.hash) {
        const target = document.getElementById(decodeURIComponent(window.location.hash.slice(1)));
        if (target) {
          openAncestorSection(target);
          requestAnimationFrame(() => {
            const top = target.getBoundingClientRect().top + window.scrollY - SCROLL_OFFSET_PX;
            window.scrollTo({ top, behavior: 'auto' });
          });
        }
      }
    } catch (err) {
      // TOC/accordion are progressive enhancements — failures here must
      // not affect the already-rendered documentation body.
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    initDocsViewer();
  });
})();
