/**
 * api.js
 * Centralized fetch wrapper for Citeable UI.
 * Injects X-Analyst-Id on write requests, normalizes base paths to /api/v1/,
 * handles pagination parsing, and provides a shared notify() toast system.
 */

window.AreosAPI = {
 /**
 * Shared toast notification system (replaces native alert())
 * @param {string} message 
 * @param {string} type "success", "error", "info"
 */
 notify(message, type = "info") {
 const toast = document.createElement("div");
 toast.setAttribute("aria-live", "polite");
 toast.className = `toast toast-${type}`;
 
 // Basic styling for the toast, assuming index.css might not have these yet
    toast.style.cssText = `
      position: fixed;
      bottom: 24px;
      right: 24px;
      padding: 14px 20px;
      border-radius: 8px;
      color: #0F172A;
      font-weight: 600;
      font-size: 14px;
      z-index: 10000000;
      box-shadow: 0 10px 25px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.05);
      animation: slideIn 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      max-width: 400px;
      font-family: var(--font-main, sans-serif);
      border: 1px solid #E2E8F0;
      background: #FFFFFF;
    `;
    
    if (type === "error") {
      toast.style.backgroundColor = "#FFF1F2";
      toast.style.color = "#9F1239";
      toast.style.borderLeft = "4px solid #E11D48";
      toast.style.borderColor = "#FECDD3";
    } else if (type === "success") {
      toast.style.backgroundColor = "#ECFDF5";
      toast.style.color = "#065F46";
      toast.style.borderLeft = "4px solid #059669";
      toast.style.borderColor = "#A7F3D0";
    } else {
      toast.style.backgroundColor = "#EFF6FF";
      toast.style.color = "#1E40AF";
      toast.style.borderLeft = "4px solid #0A66C2";
      toast.style.borderColor = "#BFDBFE";
    }
 
 toast.textContent = message;
 document.body.appendChild(toast);
 
 setTimeout(() => {
 toast.style.opacity = "0";
 toast.style.transition = "opacity 0.3s ease-out";
 setTimeout(() => toast.remove(), 300);
 }, 4000);
 },

 /**
 * Centralized fetch wrapper compatible with native fetch().
 */
 async fetch(endpoint, options = {}) {
 let url = endpoint;
 if (url.includes("/api/") && !url.includes("/api/v1/")) {
 url = url.replace("/api/", "/api/v1/");
 } else if (!url.includes("/api/v1/") && !url.startsWith("http")) {
 url = url.startsWith("/") ? `/api/v1${url}` : `/api/v1/${url}`;
 }

 const authHeaders = typeof getAuthHeaders === 'function' ? getAuthHeaders() : {};

 const headers = {
 "Content-Type": "application/json",
 ...authHeaders,
 ...(options.headers || {})
 };

 const method = (options.method || "GET").toUpperCase();
 if (method !== "GET" && method !== "HEAD") {
 const analystId = window.AreosContext?.analystId;
 if (analystId) {
 headers["X-Analyst-Id"] = analystId;
 }
 }

 const config = {
 ...options,
 headers
 };

 return await window.fetch(url, config);
 }
};

// Add keyframes for toast animation if not exists
if (!document.getElementById("toast-styles")) {
 const style = document.createElement("style");
 style.id = "toast-styles";
 style.textContent = `
 @keyframes slideIn {
 from { transform: translateX(100%); opacity: 0; }
 to { transform: translateX(0); opacity: 1; }
 }
 `;
 document.head.appendChild(style);
}
