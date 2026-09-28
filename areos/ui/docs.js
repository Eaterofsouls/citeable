/**
 * docs.js — Citeable documentation viewer.
 * High-precision 3-Column Developer Documentation Portal (Stripe / Linear / Apple Developer standard).
 */

(() => {
  'use strict';

  // Multi-file documentation manifest — ordered for navigation.
  const EXTERNAL_DOC_PAGES = [
    { id: 'index',           file: 'docs/index.md',            title: 'Overview',          section: 'external' },
    { id: 'lifecycle',       file: 'docs/lifecycle.md',        title: 'Audit Lifecycle',   section: 'external' },
    { id: 'scoring',         file: 'docs/scoring.md',          title: 'Scoring Model',     section: 'external' },
    { id: 'knowledge',       file: 'docs/knowledge.md',        title: 'Knowledge Base',    section: 'external' },
    { id: 'ai-architecture', file: 'docs/ai-architecture.md',  title: 'AI Architecture',   section: 'external' },
    { id: 'review',          file: 'docs/review.md',           title: 'Human Review',      section: 'external' },
    { id: 'api',             file: 'docs/api.md',              title: 'API Reference',     section: 'external' },
    { id: 'security',        file: 'docs/security.md',         title: 'Security',          section: 'external' },
    { id: 'testing',         file: 'docs/testing.md',          title: 'Testing',           section: 'external' },
    { id: 'limitations',     file: 'docs/limitations.md',      title: 'Limitations',       section: 'external' },
    { id: 'changelog',       file: 'docs/changelog.md',        title: 'Changelog',         section: 'external' },
    { id: 'legal',           file: 'docs/legal.md',            title: 'Legal',             section: 'external' },
  ];

  // Internal engineering documentation — only visible with admin session token.
  const INTERNAL_DOC_PAGES = [
    { id: 'int-orientation',  file: 'docs/internal/00-orientation.md',       title: 'Orientation',        section: 'internal' },
    { id: 'int-architecture', file: 'docs/internal/01-architecture.md',      title: 'Architecture',       section: 'internal' },
    { id: 'int-repo-map',     file: 'docs/internal/02-repository-map.md',    title: 'Repository Map',     section: 'internal' },
    { id: 'int-audit-engine', file: 'docs/internal/03-audit-engine.md',      title: 'Audit Engine',       section: 'internal' },
    { id: 'int-data-model',   file: 'docs/internal/04-data-model.md',        title: 'Data Model',         section: 'internal' },
    { id: 'int-evidence',     file: 'docs/internal/05-evidence-findings.md', title: 'Evidence & Findings', section: 'internal' },
    { id: 'int-scoring',      file: 'docs/internal/06-scoring.md',           title: 'Scoring Engine',     section: 'internal' },
    { id: 'int-ai-llm',       file: 'docs/internal/07-ai-llm.md',            title: 'AI / LLM',          section: 'internal' },
    { id: 'int-frontend',     file: 'docs/internal/08-frontend.md',           title: 'Frontend',          section: 'internal' },
    { id: 'int-api',          file: 'docs/internal/09-api-reference.md',      title: 'API (Internal)',    section: 'internal' },
    { id: 'int-security',     file: 'docs/internal/10-security.md',           title: 'Security Model',   section: 'internal' },
    { id: 'int-governance',   file: 'docs/internal/11-governance.md',         title: 'Governance',       section: 'internal' },
    { id: 'int-testing',      file: 'docs/internal/12-testing-qa.md',         title: 'Testing & QA',     section: 'internal' },
    { id: 'int-operations',   file: 'docs/internal/13-operations.md',         title: 'Operations',       section: 'internal' },
    { id: 'int-adrs',         file: 'docs/internal/14-adrs.md',               title: 'ADRs',             section: 'internal' },
    { id: 'int-known-issues', file: 'docs/internal/15-known-issues.md',       title: 'Known Issues',     section: 'internal' },
    { id: 'int-historical',   file: 'docs/internal/16-historical.md',         title: 'Historical',       section: 'internal' },
    { id: 'int-how-to-change',file: 'docs/internal/17-how-to-change.md',     title: 'How to Change',    section: 'internal' },
    { id: 'int-changelog',    file: 'docs/internal/18-changelog.md',          title: 'Int. Changelog',   section: 'internal' },
  ];

  /** Build the active page list — external always, internal only with admin token. */
  function getDocPages() {
    try {
      const token = sessionStorage.getItem('areos_api_token');
      if (token) return [...EXTERNAL_DOC_PAGES, ...INTERNAL_DOC_PAGES];
    } catch (err) {}
    return [...EXTERNAL_DOC_PAGES];
  }

  let DOC_PAGES = getDocPages();
  const DEFAULT_PAGE_ID = 'index';
  const SCROLL_OFFSET_PX = 88;

  let _currentPageId = DEFAULT_PAGE_ID;

  // ---------------------------------------------------------------------
  // Routing & Helpers
  // ---------------------------------------------------------------------
  function getPageIdFromHash() {
    const hash = window.location.hash.slice(1);
    if (!hash) return DEFAULT_PAGE_ID;
    const match = hash.match(/^page=([a-z0-9-]+)/);
    return match ? match[1] : DEFAULT_PAGE_ID;
  }

  function getSectionFromHash() {
    const hash = window.location.hash.slice(1);
    const ampIdx = hash.indexOf('&');
    return ampIdx >= 0 ? hash.slice(ampIdx + 1) : null;
  }

  // ---------------------------------------------------------------------
  // Left Navigation Tree (Column 1)
  // ---------------------------------------------------------------------
  function buildLeftNavTree() {
    const container = document.getElementById('docs-page-tree');
    if (!container) return;

    DOC_PAGES = getDocPages();
    container.innerHTML = '';

    const extPages = DOC_PAGES.filter(p => p.section === 'external');
    const intPages = DOC_PAGES.filter(p => p.section === 'internal');

    // 1. Public Reference Group
    const extGroup = document.createElement('div');
    extGroup.className = 'docs-subnav-group';
    extGroup.innerHTML = `
      <div class="docs-subnav-header">
        <span>Public Reference</span>
        <span class="docs-subnav-count">${extPages.length}</span>
      </div>
      <ul class="docs-subnav-list" id="docs-subnav-public"></ul>
    `;
    const extList = extGroup.querySelector('#docs-subnav-public');
    extPages.forEach(p => extList.appendChild(createNavLi(p)));
    container.appendChild(extGroup);

    // 2. Internal Engineering Group (if authenticated)
    if (intPages.length > 0) {
      const intGroup = document.createElement('div');
      intGroup.className = 'docs-subnav-group';
      intGroup.innerHTML = `
        <div class="docs-subnav-header" style="margin-top: 18px;">
          <span>Internal Specs</span>
          <span class="docs-subnav-count" style="background:#F1F5F9; color:#0F172A; font-weight:700;">ADMIN</span>
        </div>
        <ul class="docs-subnav-list" id="docs-subnav-internal"></ul>
      `;
      const intList = intGroup.querySelector('#docs-subnav-internal');
      intPages.forEach(p => intList.appendChild(createNavLi(p)));
      container.appendChild(intGroup);
    }

    // 3. Search Filter Logic
    const filterInput = document.getElementById('docs-nav-filter');
    if (filterInput) {
      filterInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        const allItems = container.querySelectorAll('.docs-subnav-item');
        allItems.forEach(item => {
          const text = item.textContent.toLowerCase();
          const match = text.includes(query);
          item.parentElement.style.display = match ? 'block' : 'none';
        });
      });
    }

    updatePageNavActive();
  }

  function createNavLi(page) {
    const li = document.createElement('li');
    const a = document.createElement('a');
    a.href = `#page=${page.id}`;
    a.className = `docs-subnav-item ${page.id === _currentPageId ? 'active' : ''}`;
    a.textContent = page.title;
    a.dataset.pageId = page.id;
    a.addEventListener('click', (e) => {
      e.preventDefault();
      navigateToPage(page.id);
    });
    li.appendChild(a);
    return li;
  }

  function updatePageNavActive() {
    const links = document.querySelectorAll('.docs-subnav-item');
    links.forEach(a => {
      const isActive = a.dataset.pageId === _currentPageId;
      a.classList.toggle('active', isActive);
    });
  }

  async function navigateToPage(pageId, sectionAnchor) {
    const page = DOC_PAGES.find(p => p.id === pageId) || DOC_PAGES[0];
    if (!page) return;
    _currentPageId = page.id;

    const hashVal = sectionAnchor ? `page=${page.id}&${sectionAnchor}` : `page=${page.id}`;
    history.replaceState(null, '', `#${hashVal}`);
    updatePageNavActive();

    const titleEl = document.querySelector('.page-title-wrap h2');
    if (titleEl) titleEl.textContent = page.title;

    await renderPage(page);
  }

  // ---------------------------------------------------------------------
  // Markdown Fetching & Link Resolution
  // ---------------------------------------------------------------------
  async function fetchMarkdown(url) {
    const cleanName = url.replace(/^(\/)?(docs\/)?/, '');
    const candidateUrls = [
      url,
      `docs/${cleanName}`,
      `/docs/${cleanName}`,
      `areos/ui/docs/${cleanName}`,
      `/areos/ui/docs/${cleanName}`
    ];
    // Build fetch options — include auth header for internal docs
    const isInternal = cleanName.includes('internal/');
    const fetchOpts = { credentials: 'same-origin' };
    if (isInternal) {
      const token = sessionStorage.getItem('areos_api_token');
      if (token) {
        fetchOpts.headers = { 'Authorization': `Bearer ${token}` };
      }
    }
    for (const candidate of candidateUrls) {
      try {
        const res = await fetch(candidate, fetchOpts);
        if (res.ok) {
          const text = await res.text();
          if (text && text.trim().length > 0) {
            return { ok: true, status: res.status, text };
          }
        } else if (res.status === 401 || res.status === 403) {
          return { ok: false, status: res.status, unauthenticated: true, text: '' };
        }
      } catch (err) {}
    }
    return { ok: false, status: 0, text: '' };
  }

  async function loadDocumentationSource(page) {
    const result = await fetchMarkdown(page.file);
    if (!result.ok) {
      if (result.unauthenticated || result.status === 401 || result.status === 403) {
        return `
<div style="padding:3rem 1.5rem;text-align:center;background:var(--surface-panel);border:1px solid var(--border-default);border-radius:12px;margin:2rem auto;max-width:540px;">
  <div style="width:48px;height:48px;border-radius:50%;background:var(--brand-50);border:1px solid var(--brand-100);color:var(--brand-500);display:flex;align-items:center;justify-content:center;margin:0 auto 16px;">
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
  </div>
  <h3 style="font-weight:700;color:var(--text-primary);margin-bottom:8px;">Admin Authentication Required</h3>
  <p style="font-size:0.9rem;color:var(--text-secondary);line-height:1.5;margin-bottom:20px;">
    Internal engineering specifications require administrative credentials. Please authenticate to view internal system architecture and audit directives.
  </p>
  <button type="button" class="btn-primary" onclick="const m = document.getElementById('admin-auth-modal'); if (m) { m.style.display = 'flex'; const i = document.getElementById('admin-auth-input'); if (i) i.focus(); }" style="padding:10px 20px;font-weight:600;cursor:pointer;">
    Authenticate with Admin Token
  </button>
</div>`;
      }
      return '## Documentation Unavailable\n\nThe documentation could not be loaded right now. Please try again shortly.';
    }
    return result.text;
  }

  function resolveDocLinks(containerEl) {
    const links = containerEl.querySelectorAll('a[href]');
    links.forEach(a => {
      const href = a.getAttribute('href');
      if (!href) return;
      const match = href.match(/^([a-z0-9_-]+)\.md(?:#(.+))?$/i);
      if (match) {
        const targetPageId = match[1];
        const section = match[2] || null;
        const targetPage = DOC_PAGES.find(p => p.id === targetPageId);
        if (targetPage) {
          a.href = section ? `#page=${targetPageId}&${section}` : `#page=${targetPageId}`;
          a.addEventListener('click', (e) => {
            e.preventDefault();
            navigateToPage(targetPageId, section);
          });
        }
      }
    });
  }

  function configureMarked() {
    if (!window.marked) return false;
    try {
      window.marked.setOptions({
        gfm: true,
        breaks: false,
        headerIds: false,
        mangle: false,
      });
      return true;
    } catch (err) {
      return false;
    }
  }

  function renderMarkdownToHtml(markdown) {
    if (window.marked && typeof window.marked.parse === 'function') {
      try {
        return window.marked.parse(markdown);
      } catch (err) {}
    }
    const escaped = markdown.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return `<pre>${escaped}</pre>`;
  }

  function extractFrontmatter(markdown) {
    let metadata = {};
    let content = markdown;
    const fmMatch = markdown.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n/);
    if (fmMatch) {
      const rawFm = fmMatch[1];
      content = markdown.slice(fmMatch[0].length);
      rawFm.split(/\r?\n/).forEach(line => {
        const parts = line.split(':');
        if (parts.length >= 2) {
          const key = parts[0].trim();
          let val = parts.slice(1).join(':').trim().replace(/^["']|["']$/g, '');
          if (val && !val.includes('{{COMMIT_HASH}}')) {
            metadata[key] = val;
          }
        }
      });
    }
    return { metadata, content };
  }

  // ---------------------------------------------------------------------
  // Heading IDs, Breadcrumbs & Pagination
  // ---------------------------------------------------------------------
  function assignHeadingIds(containerEl) {
    const headings = Array.from(containerEl.querySelectorAll('h2, h3'));
    const usedSlugs = new Set();
    const result = [];

    headings.forEach((heading) => {
      const text = heading.textContent.trim();
      let slug = text
        .toLowerCase()
        .replace(/[^\w\s-]/g, '')
        .replace(/\s+/g, '-')
        .replace(/^-+|-+$/g, '');

      if (!slug) slug = 'section';
      let uniqueSlug = slug;
      let counter = 1;
      while (usedSlugs.has(uniqueSlug)) {
        uniqueSlug = `${slug}-${counter++}`;
      }
      usedSlugs.add(uniqueSlug);
      heading.id = uniqueSlug;
      heading.classList.add('docs-heading');

      result.push({
        id: uniqueSlug,
        text,
        level: heading.tagName === 'H2' ? 2 : 3,
      });
    });

    return result;
  }

  function renderBreadcrumbsAndPagination(page) {
    // 1. Breadcrumbs
    const breadcrumbsEl = document.getElementById('docs-breadcrumbs');
    if (breadcrumbsEl) {
      const sectionName = page.section === 'internal' ? 'Internal Specifications' : 'Public Reference';
      breadcrumbsEl.innerHTML = `
        <div class="docs-breadcrumbs-list">
          <a href="#page=index">Documentation</a>
          <span>/</span>
          <span>${sectionName}</span>
          <span>/</span>
          <span class="current">${page.title}</span>
        </div>
      `;
    }

    // 2. Pagination (Previous / Next)
    const paginationEl = document.getElementById('docs-pagination');
    if (paginationEl) {
      const idx = DOC_PAGES.findIndex(p => p.id === page.id);
      const prevPage = idx > 0 ? DOC_PAGES[idx - 1] : null;
      const nextPage = idx < DOC_PAGES.length - 1 ? DOC_PAGES[idx + 1] : null;

      let html = '';
      if (prevPage) {
        html += `
          <a href="#page=${prevPage.id}" class="docs-pagination-card prev" data-page="${prevPage.id}">
            <span class="pagination-label">← Previous</span>
            <span class="pagination-title">${prevPage.title}</span>
          </a>
        `;
      } else {
        html += `<div></div>`;
      }

      if (nextPage) {
        html += `
          <a href="#page=${nextPage.id}" class="docs-pagination-card next" data-page="${nextPage.id}">
            <span class="pagination-label">Next →</span>
            <span class="pagination-title">${nextPage.title}</span>
          </a>
        `;
      }

      paginationEl.innerHTML = html;

      paginationEl.querySelectorAll('a[data-page]').forEach(card => {
        card.addEventListener('click', (e) => {
          e.preventDefault();
          navigateToPage(card.dataset.page);
        });
      });
    }
  }

  // ---------------------------------------------------------------------
  // Table of Contents & Scroll-Spy (Column 3)
  // ---------------------------------------------------------------------
  function buildTableOfContents(headings, tocNavEl) {
    tocNavEl.innerHTML = '';
    if (headings.length === 0) {
      tocNavEl.innerHTML = '<span style="font-size:0.75rem; color:var(--text-tertiary);">No section anchors</span>';
      return;
    }

    headings.forEach((h) => {
      const a = document.createElement('a');
      a.href = `#${h.id}`;
      a.className = `docs-toc-link docs-toc-level-${h.level}`;
      a.textContent = h.text;
      a.dataset.targetId = h.id;
      a.addEventListener('click', (e) => {
        e.preventDefault();
        const target = document.getElementById(h.id);
        if (target) {
          const top = target.getBoundingClientRect().top + window.scrollY - SCROLL_OFFSET_PX;
          window.scrollTo({ top, behavior: 'smooth' });
          history.replaceState(null, '', `#page=${_currentPageId}&${h.id}`);
        }
      });
      tocNavEl.appendChild(a);
    });
  }

  function setupScrollSpy(headings, tocNavEl) {
    if (headings.length === 0) return;
    const links = Array.from(tocNavEl.querySelectorAll('.docs-toc-link'));
    if (links.length === 0) return;

    const linkById = new Map(links.map(a => [a.dataset.targetId, a]));
    let activeId = null;

    const setActive = (id) => {
      if (id === activeId) return;
      links.forEach(a => a.classList.remove('active'));
      if (linkById.has(id)) {
        linkById.get(id).classList.add('active');
      }
      activeId = id;
    };

    const onScroll = () => {
      let currentId = '';
      for (const h of headings) {
        const el = document.getElementById(h.id);
        if (el) {
          const rect = el.getBoundingClientRect();
          if (rect.top <= 140) {
            currentId = h.id;
          }
        }
      }
      if (currentId) setActive(currentId);
      else if (headings.length > 0) setActive(headings[0].id);
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // ---------------------------------------------------------------------
  // 1-Click Code Copy Button
  // ---------------------------------------------------------------------
  function setupCodeCopyButtons(containerEl) {
    const preElements = containerEl.querySelectorAll('pre');
    preElements.forEach((pre) => {
      if (pre.parentElement.classList.contains('docs-code-container')) return;
      if (pre.querySelector('code.language-mermaid') || pre.classList.contains('mermaid')) return;

      const wrapper = document.createElement('div');
      wrapper.className = 'docs-code-container';

      const copyBtn = document.createElement('button');
      copyBtn.type = 'button';
      copyBtn.className = 'docs-copy-btn';
      copyBtn.setAttribute('aria-label', 'Copy code to clipboard');
      copyBtn.innerHTML = `
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
        <span>Copy</span>
      `;

      let resetTimer = null;
      copyBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const codeEl = pre.querySelector('code') || pre;
        const textToCopy = codeEl.innerText || codeEl.textContent || '';
        
        try {
          await navigator.clipboard.writeText(textToCopy);
        } catch (err) {
          const ta = document.createElement('textarea');
          ta.value = textToCopy;
          document.body.appendChild(ta);
          ta.select();
          document.execCommand('copy');
          document.body.removeChild(ta);
        }

        copyBtn.classList.add('copied');
        copyBtn.innerHTML = `
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
          <span>Copied!</span>
        `;

        if (resetTimer) clearTimeout(resetTimer);
        resetTimer = setTimeout(() => {
          copyBtn.classList.remove('copied');
          copyBtn.innerHTML = `
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            <span>Copy</span>
          `;
        }, 1800);
      });

      pre.parentNode.insertBefore(wrapper, pre);
      wrapper.appendChild(pre);
      wrapper.appendChild(copyBtn);
    });
  }

  // ---------------------------------------------------------------------
  // GitHub-Style Markdown Callout Alert Enhancer
  // ---------------------------------------------------------------------
  function enhanceCallouts(containerEl) {
    const blockquotes = containerEl.querySelectorAll('blockquote');
    blockquotes.forEach((bq) => {
      const text = bq.textContent.trim();
      let type = 'note';
      let title = 'Note';
      let iconSvg = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';

      if (/^\[!NOTE\]/i.test(text) || /\*\*Note:\*\*/i.test(text)) {
        type = 'note';
        title = 'Technical Note';
      } else if (/^\[!TIP\]/i.test(text) || /\*\*Tip:\*\*/i.test(text) || /\*\*Best Practice:\*\*/i.test(text)) {
        type = 'tip';
        title = 'Best Practice';
        iconSvg = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>';
      } else if (/^\[!IMPORTANT\]/i.test(text) || /\*\*Important:\*\*/i.test(text) || /\*\*In 30 seconds:\*\*/i.test(text)) {
        type = 'important';
        title = 'Key Architectural Takeaway';
        iconSvg = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>';
      } else if (/^\[!WARNING\]/i.test(text) || /\*\*Warning:\*\*/i.test(text) || /\*\*Caution:\*\*/i.test(text)) {
        type = 'warning';
        title = 'Warning';
        iconSvg = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';
      } else {
        return; // standard blockquote
      }

      const wrapper = document.createElement('div');
      wrapper.className = `docs-callout ${type}`;
      wrapper.innerHTML = `
        <div class="docs-callout-header">
          ${iconSvg}
          <span>${title}</span>
        </div>
        <div class="docs-callout-body">
          ${bq.innerHTML.replace(/\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]/gi, '').replace(/\*\*(Note|Tip|Important|Warning|In 30 seconds):\*\*/gi, '')}
        </div>
      `;
      bq.replaceWith(wrapper);
    });
  }

  // ---------------------------------------------------------------------
  // Mermaid & Image Fullscreen
  // ---------------------------------------------------------------------
  async function renderMermaidDiagrams(containerEl) {
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

    if (!window.mermaid) return;

    try {
      window.mermaid.initialize({
        startOnLoad: false,
        theme: 'base',
        securityLevel: 'strict',
        fontFamily: '"Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        flowchart: {
          curve: 'basis',
          nodeSpacing: 50,
          rankSpacing: 60,
          htmlLabels: true,
          padding: 24,
          useMaxWidth: true,
        },
        themeVariables: {
          background: '#FFFFFF',
          primaryColor: '#FFFFFF',
          primaryTextColor: '#0F172A',
          primaryBorderColor: '#2563EB',
          secondaryColor: '#F8FAFC',
          tertiaryColor: '#F1F5F9',
          lineColor: '#475569',
          textColor: '#0F172A',
          mainBkg: '#FFFFFF',
          nodeTextColor: '#0F172A',
          clusterBkg: '#F8FAFC',
          clusterBorder: '#94A3B8',
          edgeLabelBackground: '#FFFFFF',
          actorBkg: '#EFF6FF',
          fontSize: '14px',
        }
      });
      await window.mermaid.run();
    } catch (err) {}
  }

  // ---------------------------------------------------------------------
  // Interactive Diagram Viewport & Fullscreen Pan/Zoom Canvas
  // ---------------------------------------------------------------------

  class InteractiveDiagramViewer {
    constructor() {
      this.modal = null;
      this.viewport = null;
      this.canvas = null;
      this.zoomPill = null;
      this.titleBadge = null;
      
      this.scale = 1.0;
      this.translateX = 0;
      this.translateY = 0;
      this.isDragging = false;
      this.dragStartX = 0;
      this.dragStartY = 0;
      this.initialTranslateX = 0;
      this.initialTranslateY = 0;
      
      this.touchStartDistance = 0;
      this.initialPinchScale = 1.0;
      
      this.currentMedia = null;
      this.initModal();
    }

    initModal() {
      if (document.getElementById('docs-fullscreen-modal')) {
        this.modal = document.getElementById('docs-fullscreen-modal');
        this.viewport = document.getElementById('docs-fullscreen-viewport');
        this.canvas = document.getElementById('docs-fullscreen-canvas');
        this.zoomPill = document.getElementById('docs-hud-zoom-pill');
        this.titleBadge = document.getElementById('docs-fullscreen-title');
        return;
      }

      const modalHTML = `
        <div id="docs-fullscreen-modal" class="docs-fullscreen-modal" role="dialog" aria-modal="true" aria-label="Diagram Viewer">
          <div class="docs-fullscreen-backdrop"></div>
          
          <header class="docs-fullscreen-header">
            <div class="docs-fullscreen-title-badge">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>
              <span id="docs-fullscreen-title">Interactive Diagram Canvas</span>
            </div>
            <button class="docs-fullscreen-close-btn" id="docs-fullscreen-close-btn" aria-label="Close fullscreen (Esc)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </header>

          <div class="docs-fullscreen-viewport" id="docs-fullscreen-viewport">
            <div class="docs-fullscreen-canvas" id="docs-fullscreen-canvas"></div>
          </div>

          <div class="docs-fullscreen-hud">
            <button class="docs-hud-btn" id="docs-hud-zoom-out" aria-label="Zoom Out (-)" title="Zoom Out (-)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="5" y1="12" x2="19" y2="12"/></svg>
            </button>
            <span class="docs-hud-zoom-pill" id="docs-hud-zoom-pill">100%</span>
            <button class="docs-hud-btn" id="docs-hud-zoom-in" aria-label="Zoom In (+)" title="Zoom In (+)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            </button>
            
            <div class="docs-hud-divider"></div>
            
            <button class="docs-hud-btn" id="docs-hud-fit" aria-label="Fit to Screen (F)" title="Fit to Screen (F)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>
              <span>Fit</span>
            </button>
            <button class="docs-hud-btn" id="docs-hud-reset" aria-label="Reset Zoom (0)" title="Reset (0)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
              <span>100%</span>
            </button>
            
            <div class="docs-hud-divider"></div>
            
            <div class="docs-hud-hint">
              <span>Drag to Pan</span>
              <span>·</span>
              <span>Wheel to Zoom</span>
            </div>
          </div>
        </div>
      `;

      document.body.insertAdjacentHTML('beforeend', modalHTML);

      this.modal = document.getElementById('docs-fullscreen-modal');
      this.viewport = document.getElementById('docs-fullscreen-viewport');
      this.canvas = document.getElementById('docs-fullscreen-canvas');
      this.zoomPill = document.getElementById('docs-hud-zoom-pill');
      this.titleBadge = document.getElementById('docs-fullscreen-title');

      this.bindEvents();
    }

    bindEvents() {
      // Close button & backdrop click
      document.getElementById('docs-fullscreen-close-btn').addEventListener('click', () => this.close());
      this.modal.querySelector('.docs-fullscreen-backdrop').addEventListener('click', () => this.close());

      // HUD Buttons
      document.getElementById('docs-hud-zoom-in').addEventListener('click', () => this.zoomStep(1.25));
      document.getElementById('docs-hud-zoom-out').addEventListener('click', () => this.zoomStep(0.8));
      document.getElementById('docs-hud-reset').addEventListener('click', () => this.resetView());
      document.getElementById('docs-hud-fit').addEventListener('click', () => this.fitToScreen());

      // Mouse Panning
      this.viewport.addEventListener('mousedown', (e) => {
        if (e.button !== 0) return; // Primary button only
        this.isDragging = true;
        this.dragStartX = e.clientX;
        this.dragStartY = e.clientY;
        this.initialTranslateX = this.translateX;
        this.initialTranslateY = this.translateY;
        this.viewport.classList.add('is-dragging');
        e.preventDefault();
      });

      window.addEventListener('mousemove', (e) => {
        if (!this.isDragging) return;
        const deltaX = e.clientX - this.dragStartX;
        const deltaY = e.clientY - this.dragStartY;
        this.translateX = this.initialTranslateX + deltaX;
        this.translateY = this.initialTranslateY + deltaY;
        this.applyTransform();
      });

      window.addEventListener('mouseup', () => {
        if (this.isDragging) {
          this.isDragging = false;
          this.viewport.classList.remove('is-dragging');
        }
      });

      // Focal-Point Wheel Zooming
      this.viewport.addEventListener('wheel', (e) => {
        e.preventDefault();
        const zoomFactor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
        const newScale = Math.min(Math.max(this.scale * zoomFactor, 0.15), 6.0);
        
        // Zoom centered on cursor
        const rect = this.viewport.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        this.translateX = mouseX - (mouseX - this.translateX) * (newScale / this.scale);
        this.translateY = mouseY - (mouseY - this.translateY) * (newScale / this.scale);
        this.scale = newScale;

        this.applyTransform();
      }, { passive: false });

      // Touch Panning & Pinch-to-Zoom
      this.viewport.addEventListener('touchstart', (e) => {
        if (e.touches.length === 1) {
          this.isDragging = true;
          this.dragStartX = e.touches[0].clientX;
          this.dragStartY = e.touches[0].clientY;
          this.initialTranslateX = this.translateX;
          this.initialTranslateY = this.translateY;
        } else if (e.touches.length === 2) {
          this.isDragging = false;
          this.touchStartDistance = Math.hypot(
            e.touches[0].clientX - e.touches[1].clientX,
            e.touches[0].clientY - e.touches[1].clientY
          );
          this.initialPinchScale = this.scale;
        }
      }, { passive: true });

      this.viewport.addEventListener('touchmove', (e) => {
        if (e.touches.length === 1 && this.isDragging) {
          const deltaX = e.touches[0].clientX - this.dragStartX;
          const deltaY = e.touches[0].clientY - this.dragStartY;
          this.translateX = this.initialTranslateX + deltaX;
          this.translateY = this.initialTranslateY + deltaY;
          this.applyTransform();
        } else if (e.touches.length === 2 && this.touchStartDistance > 0) {
          const currentDistance = Math.hypot(
            e.touches[0].clientX - e.touches[1].clientX,
            e.touches[0].clientY - e.touches[1].clientY
          );
          const factor = currentDistance / this.touchStartDistance;
          this.scale = Math.min(Math.max(this.initialPinchScale * factor, 0.15), 6.0);
          this.applyTransform();
        }
      }, { passive: true });

      this.viewport.addEventListener('touchend', () => {
        this.isDragging = false;
        this.touchStartDistance = 0;
      }, { passive: true });

      // Keyboard Controls
      window.addEventListener('keydown', (e) => {
        if (!this.modal.classList.contains('active')) return;

        if (e.key === 'Escape') {
          this.close();
        } else if (e.key === '+' || e.key === '=') {
          this.zoomStep(1.25);
        } else if (e.key === '-' || e.key === '_') {
          this.zoomStep(0.8);
        } else if (e.key === '0') {
          this.resetView();
        } else if (e.key === 'f' || e.key === 'F' || e.key === ' ') {
          e.preventDefault();
          this.fitToScreen();
        } else if (e.key === 'ArrowLeft') {
          this.translateX += 40;
          this.applyTransform();
        } else if (e.key === 'ArrowRight') {
          this.translateX -= 40;
          this.applyTransform();
        } else if (e.key === 'ArrowUp') {
          this.translateY += 40;
          this.applyTransform();
        } else if (e.key === 'ArrowDown') {
          this.translateY -= 40;
          this.applyTransform();
        }
      });
    }

    open(targetNode, title = 'Interactive Diagram Canvas') {
      this.currentMedia = targetNode;
      this.canvas.innerHTML = '';
      this.titleBadge.textContent = title;

      // Extract accurate natural dimensions
      let naturalWidth = 1000;
      let naturalHeight = 700;

      const viewBox = targetNode.getAttribute('viewBox');
      if (viewBox) {
        const parts = viewBox.trim().split(/[\s,]+/).map(parseFloat);
        if (parts.length === 4 && parts[2] > 0 && parts[3] > 0) {
          naturalWidth = parts[2];
          naturalHeight = parts[3];
        }
      } else if (targetNode.getBBox) {
        try {
          const bbox = targetNode.getBBox();
          if (bbox && bbox.width > 0 && bbox.height > 0) {
            naturalWidth = bbox.width;
            naturalHeight = bbox.height;
          }
        } catch (e) {}
      } else if (targetNode.naturalWidth && targetNode.naturalHeight) {
        naturalWidth = targetNode.naturalWidth;
        naturalHeight = targetNode.naturalHeight;
      } else if (targetNode.clientWidth && targetNode.clientHeight) {
        naturalWidth = targetNode.clientWidth;
        naturalHeight = targetNode.clientHeight;
      }

      const pad = 32;
      this.naturalWidth = naturalWidth + pad * 2;
      this.naturalHeight = naturalHeight + pad * 2;

      const clone = targetNode.cloneNode(true);
      if (clone.tagName && clone.tagName.toLowerCase() === 'svg') {
        clone.setAttribute('width', `${this.naturalWidth}`);
        clone.setAttribute('height', `${this.naturalHeight}`);
        clone.style.width = `${this.naturalWidth}px`;
        clone.style.height = `${this.naturalHeight}px`;
        clone.style.padding = `${pad}px`;
        clone.style.boxSizing = 'border-box';
        clone.style.maxWidth = 'none';
        clone.style.maxHeight = 'none';
        clone.style.minWidth = `${this.naturalWidth}px`;
        clone.style.minHeight = `${this.naturalHeight}px`;
        clone.style.display = 'block';
      } else if (clone.tagName && clone.tagName.toLowerCase() === 'img') {
        clone.style.width = `${this.naturalWidth}px`;
        clone.style.height = `${this.naturalHeight}px`;
        clone.style.padding = `${pad}px`;
        clone.style.boxSizing = 'border-box';
        clone.style.maxWidth = 'none';
        clone.style.display = 'block';
      }

      this.canvas.appendChild(clone);
      this.modal.classList.add('active');
      document.body.style.overflow = 'hidden';

      // Initial Fit to screen
      requestAnimationFrame(() => {
        this.fitToScreen();
      });
    }

    close() {
      this.modal.classList.remove('active');
      document.body.style.overflow = '';
      setTimeout(() => {
        if (!this.modal.classList.contains('active')) {
          this.canvas.innerHTML = '';
        }
      }, 300);
    }

    applyTransform() {
      this.canvas.style.transform = `translate3d(${this.translateX}px, ${this.translateY}px, 0) scale(${this.scale})`;
      if (this.zoomPill) {
        this.zoomPill.textContent = `${Math.round(this.scale * 100)}%`;
      }
    }

    zoomStep(factor) {
      const newScale = Math.min(Math.max(this.scale * factor, 0.15), 6.0);
      const rect = this.viewport.getBoundingClientRect();
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      this.translateX = centerX - (centerX - this.translateX) * (newScale / this.scale);
      this.translateY = centerY - (centerY - this.translateY) * (newScale / this.scale);
      this.scale = newScale;
      this.applyTransform();
    }

    resetView() {
      this.scale = 1.0;
      const viewportRect = this.viewport.getBoundingClientRect();
      this.translateX = (viewportRect.width - this.naturalWidth) / 2;
      this.translateY = (viewportRect.height - this.naturalHeight) / 2;
      this.applyTransform();
    }

    fitToScreen() {
      if (!this.naturalWidth || !this.naturalHeight) return;

      const viewportRect = this.viewport.getBoundingClientRect();
      const paddingX = 80;
      const paddingY = 80;
      const availWidth = Math.max(viewportRect.width - paddingX * 2, 100);
      const availHeight = Math.max(viewportRect.height - paddingY * 2, 100);

      const scaleX = availWidth / this.naturalWidth;
      const scaleY = availHeight / this.naturalHeight;
      this.scale = Math.min(scaleX, scaleY);
      if (isNaN(this.scale) || this.scale <= 0) this.scale = 1.0;

      const renderedWidth = this.naturalWidth * this.scale;
      const renderedHeight = this.naturalHeight * this.scale;
      this.translateX = (viewportRect.width - renderedWidth) / 2;
      this.translateY = (viewportRect.height - renderedHeight) / 2;

      this.applyTransform();
    }
  }

  // Global singleton viewer instance
  let _diagramViewer = null;

  function setupImageFullscreen(containerEl) {
    if (!_diagramViewer) {
      _diagramViewer = new InteractiveDiagramViewer();
    }

    // Wrap and enhance all rendered diagrams (.mermaid) and standalone SVG/images
    const diagramContainers = containerEl.querySelectorAll('.mermaid, pre.mermaid, .docs-img-wrapper');
    
    diagramContainers.forEach(container => {
      // Avoid duplicate card wraps
      let card = container.closest('.docs-diagram-card');
      if (!card) {
        card = document.createElement('div');
        card.className = 'docs-diagram-card';
        container.parentNode.insertBefore(card, container);
        card.appendChild(container);
      }

      // Check if expand button already exists
      if (card.querySelector('.docs-diagram-expand-btn')) return;

      const btn = document.createElement('button');
      btn.className = 'docs-diagram-expand-btn';
      btn.setAttribute('aria-label', 'Expand Diagram in Interactive Canvas');
      btn.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg>
        <span>Expand</span>
      `;

      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();

        // Extract heading or title context if available
        let title = 'System Architecture Diagram';
        const prevHeading = card.previousElementSibling;
        if (prevHeading && /^H[1-4]$/i.test(prevHeading.tagName)) {
          title = prevHeading.textContent.trim();
        }

        const targetSvg = card.querySelector('svg') || card.querySelector('img');
        if (targetSvg) {
          _diagramViewer.open(targetSvg, title);
        }
      });

      card.appendChild(btn);
    });
  }

  // ---------------------------------------------------------------------
  // Orchestration & Initialization
  // ---------------------------------------------------------------------
  async function renderPage(page) {
    const contentEl = document.getElementById('docs-content');
    const tocNavEl = document.getElementById('docs-toc-nav');
    if (!contentEl) return;

    contentEl.innerHTML = '<div class="docs-loading"><div class="spinner"></div><span>Loading documentation...</span></div>';
    if (tocNavEl) tocNavEl.innerHTML = '';
    window.scrollTo({ top: 0, behavior: 'auto' });

    let markdown;
    try {
      markdown = await loadDocumentationSource(page);
    } catch (err) {
      contentEl.innerHTML = '<div class="docs-error">Documentation could not be loaded. Please refresh the page.</div>';
      return;
    }

    try {
      const { metadata, content } = extractFrontmatter(markdown);
      let renderedHtml = renderMarkdownToHtml(content);
      if (Object.keys(metadata).length > 0) {
        let chipsHtml = '<div class="docs-meta-chips" style="display:flex;gap:8px;margin-bottom:1.5rem;flex-wrap:wrap;align-items:center;">';
        if (metadata.status) {
          chipsHtml += `<span class="badge" style="background:var(--brand-50);color:var(--brand-600);border:1px solid var(--brand-200);font-size:0.75rem;padding:2px 8px;border-radius:4px;font-weight:600;text-transform:uppercase;">Status: ${escapeHtml(metadata.status)}</span>`;
        }
        if (metadata.last_verified) {
          chipsHtml += `<span class="badge" style="background:var(--surface-sunken);color:var(--text-secondary);border:1px solid var(--border-default);font-size:0.75rem;padding:2px 8px;border-radius:4px;">Verified: ${escapeHtml(metadata.last_verified)}</span>`;
        }
        if (metadata.owner) {
          chipsHtml += `<span class="badge" style="background:var(--surface-sunken);color:var(--text-secondary);border:1px solid var(--border-default);font-size:0.75rem;padding:2px 8px;border-radius:4px;">Owner: ${escapeHtml(metadata.owner)}</span>`;
        }
        chipsHtml += '</div>';
        renderedHtml = chipsHtml + renderedHtml;
      }
      contentEl.innerHTML = renderedHtml;
    } catch (err) {
      contentEl.innerHTML = '<div class="docs-error">Documentation could not be rendered. Please refresh the page.</div>';
      return;
    }

    try {
      resolveDocLinks(contentEl);
      await renderMermaidDiagrams(contentEl);
      setupImageFullscreen(contentEl);
    } catch (err) {}

    try {
      const headings = assignHeadingIds(contentEl);
      if (tocNavEl) {
        buildTableOfContents(headings, tocNavEl);
        setupScrollSpy(headings, tocNavEl);
      }
      setupCodeCopyButtons(contentEl);
      enhanceCallouts(contentEl);
      renderBreadcrumbsAndPagination(page);

      // Deep link to section anchor if present
      const sectionAnchor = getSectionFromHash();
      if (sectionAnchor) {
        const target = document.getElementById(decodeURIComponent(sectionAnchor));
        if (target) {
          requestAnimationFrame(() => {
            const top = target.getBoundingClientRect().top + window.scrollY - SCROLL_OFFSET_PX;
            window.scrollTo({ top, behavior: 'smooth' });
          });
        }
      }
    } catch (err) {}
  }

  async function initDocsViewer() {
    configureMarked();
    buildLeftNavTree();

    const initialPageId = getPageIdFromHash();
    const initialPage = DOC_PAGES.find(p => p.id === initialPageId) || DOC_PAGES[0];
    _currentPageId = initialPage.id;
    updatePageNavActive();

    const titleEl = document.querySelector('.page-title-wrap h2');
    if (titleEl) titleEl.textContent = initialPage.title;

    await renderPage(initialPage);

    window.addEventListener('hashchange', async () => {
      const pageId = getPageIdFromHash();
      if (pageId !== _currentPageId) {
        await navigateToPage(pageId, getSectionFromHash());
      }
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    initDocsViewer();
  });
})();
