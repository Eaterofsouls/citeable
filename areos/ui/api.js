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
 toast.className = `toast toast-${type}`;
 
 // Basic styling for the toast, assuming index.css might not have these yet
 toast.style.cssText = `
 position: fixed;
 bottom: 24px;
 right: 24px;
 padding: 16px 24px;
 border-radius: 8px;
 color: #fff;
 font-weight: 500;
 z-index: 10000;
 box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
 animation: slideIn 0.3s ease-out forwards;
 max-width: 400px;
 `;
 
 if (type === "error") toast.style.backgroundColor = "#ef4444";
 else if (type === "success") toast.style.backgroundColor = "#10b981";
 else toast.style.backgroundColor = "#3b82f6";
 
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
 console.log("OUTGOING HEADERS:", headers);

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
