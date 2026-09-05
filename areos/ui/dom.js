// dom.js — Safe DOM manipulation utilities for Citeable UI
// Replaces unsafe .innerHTML for dynamic data.
// Static developer-authored HTML (templates, SVGs) may still use .innerHTML.

/**
 * Escape HTML entities to prevent XSS when inserting into innerHTML contexts.
 * Use this for ANY dynamic data that will be placed in HTML.
 */
function escapeHtml(unsafe) {
 if (unsafe === null || unsafe === undefined) return '';
 return String(unsafe)
 .replace(/&/g, '&amp;')
 .replace(/</g, '&lt;')
 .replace(/>/g, '&gt;')
 .replace(/"/g, '&quot;')
 .replace(/'/g, '&#039;');
}

/**
 * Create a text node safely (no HTML interpretation).
 */
function safeText(text) {
 return document.createTextNode(text || '');
}

/**
 * Create an element with safe text content.
 */
function el(tag, textContent, attrs) {
 const elem = document.createElement(tag);
 if (textContent !== undefined && textContent !== null) {
 elem.textContent = String(textContent);
 }
 if (attrs) {
 for (const [key, value] of Object.entries(attrs)) {
 if (key === 'className') {
 elem.className = value;
 } else if (key === 'style' && typeof value === 'object') {
 Object.assign(elem.style, value);
 } else if (key.startsWith('on')) {
 elem.addEventListener(key.slice(2).toLowerCase(), value);
 } else {
 elem.setAttribute(key, value);
 }
 }
 }
 return elem;
}

/**
 * Safely set text content of an element by ID.
 */
function setText(elementId, text) {
 const elem = document.getElementById(elementId);
 if (elem) {
 elem.textContent = text || '';
 }
}

/**
 * Validate a URL to prevent javascript: protocol XSS.
 * Returns the URL if safe, or '#' if potentially malicious.
 */
function safeUrl(url) {
  if (!url) return '#';
  try {
    const parsed = new URL(url, window.location.origin);
    if (parsed.protocol === 'javascript:' || parsed.protocol === 'data:') {
      return '#';
    }
    return escapeHtml(url);
  } catch {
    return escapeHtml(url); // relative URLs are OK
  }
}

/* ==========================================================================
 makeDialogAccessible(el, opts) — UI/UX Audit fix.

 The app's modals/drawer/command-palette are all custom-built, not native
 <dialog>, so they don't get accessibility behavior for free. Previously
 there were zero aria- attributes or focus handling anywhere in the app:
 a keyboard/screen-reader user could tab straight through a "closed" page
 behind an open modal.

 This gives any dialog-like container, in one call:
 - role="dialog" + aria-modal="true" (+ aria-labelledby if a title id is given)
 - focus moved to the first focusable element inside it when opened
 - Tab/Shift+Tab trapped inside it while open
 - Escape triggers onClose
 - focus returned to whatever triggered it, on close

 Usage:
 const dialog = makeDialogAccessible(document.getElementById('editor-modal'), {
 titleId: 'editor-title',
 onClose: () => editorModal.classList.remove('active'),
 });
 dialog.open(); // call when you show the modal
 dialog.close(); // call when you hide the modal (or just call onClose's own hide logic)
 ========================================================================== */
function makeDialogAccessible(container, opts) {
	opts = opts || {};
	container.setAttribute('role', opts.role || 'dialog');
	container.setAttribute('aria-modal', 'true');
	if (opts.titleId) container.setAttribute('aria-labelledby', opts.titleId);
	else if (opts.label) container.setAttribute('aria-label', opts.label);

	const FOCUSABLE = 'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';
	let lastFocused = null;

	function trap(e) {
		if (e.key === 'Escape') {
			e.preventDefault();
			if (opts.onClose) opts.onClose();
			return;
		}
		if (e.key !== 'Tab') return;

		// DEC-03: Skip modal focus-trapping when position is static or on mobile viewports (< 768px)
		const isStatic = typeof window !== 'undefined' && window.getComputedStyle ? window.getComputedStyle(container).position === 'static' : false;
		const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;
		if (isStatic || isMobile) return;

		const focusable = Array.from(container.querySelectorAll(FOCUSABLE)).filter(
			(elx) => elx.offsetParent !== null || (elx.getClientRects && elx.getClientRects().length > 0)
		);
		if (focusable.length === 0) return;
		const first = focusable[0];
		const last = focusable[focusable.length - 1];
		if (e.shiftKey && document.activeElement === first) {
			e.preventDefault();
			last.focus();
		} else if (!e.shiftKey && document.activeElement === last) {
			e.preventDefault();
			first.focus();
		}
	}

	return {
		open() {
			lastFocused = document.activeElement;
			container.addEventListener('keydown', trap);
			const isStatic = typeof window !== 'undefined' && window.getComputedStyle ? window.getComputedStyle(container).position === 'static' : false;
			const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;
			if (!isStatic && !isMobile) {
				const focusable = container.querySelector(FOCUSABLE);
				if (focusable) focusable.focus({ preventScroll: true });
			}
		},
		close() {
			container.removeEventListener('keydown', trap);
			if (lastFocused && typeof lastFocused.focus === 'function') lastFocused.focus({ preventScroll: true });
			lastFocused = null;
		},
	};
}
