const API = {
  token: sessionStorage.getItem('token'),

  async call(path, options = {}) {
    const headers = { ...(options.headers || {}) };
    if (this.token) headers.Authorization = `Bearer ${this.token}`;
    if (options.body && !(options.body instanceof FormData) && !(options.body instanceof URLSearchParams)) {
      headers['Content-Type'] = 'application/json';
    }
    const res = await fetch(path, { ...options, headers });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (${res.status})`);
    }
    return res.status === 204 ? null : res.json();
  },

  logout() {
    this.token = null;
    sessionStorage.removeItem('token');
    window.location.href = '/';
  },

  requireAuth() {
    if (!this.token) window.location.href = '/';
  },

  async me() {
    return this.call('/auth/me');
  }
};

function showMessage(text, type = '') {
  const el = document.querySelector('#message');
  if (!el) return;
  el.textContent = text;
  el.className = type;
}

function statusBadge(status) {
  return `<span class="badge ${status}">${status.replace('_', ' ')}</span>`;
}

function progressBar(assigned, requested) {
  const pct = Math.min(100, Math.round((assigned / requested) * 100));
  return `<div class="progress-bar"><div style="width:${pct}%"></div></div><small>${assigned}/${requested} episodes</small>`;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str ?? '';
  return div.innerHTML;
}
