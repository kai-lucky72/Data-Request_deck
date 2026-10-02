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
    if (!this.token) {
      window.location.replace('/');
      return false;
    }
    return true;
  },

  requireRole(...roles) {
    if (!this.requireAuth()) return Promise.resolve(null);
    return this.me().then(user => {
      if (!roles.includes(user.role)) {
        window.location.href = user.role === 'client' ? '/client.html' : user.role === 'admin' ? '/admin.html' : '/operator.html';
        return null;
      }
      document.body.classList.remove('auth-pending');
      return user;
    }).catch(() => {
      window.location.href = '/';
      return null;
    });
  },

  requireWorkspaceRole() {
    const adminPath = window.location.pathname.startsWith('/admin/');
    const role = adminPath ? 'admin' : 'operator';
    return this.requireRole(role).then(user => {
      if (!user) return null;
      const base = adminPath ? '/admin' : '';
      const pageLinks = [
        ['Requests', `${base}/requests.html`],
        ['Episodes', `${base}/episodes.html`],
        ['Analytics', `${base}/analytics.html`],
      ];
      const currentPage = pageLinks.find(([, href]) => href === window.location.pathname)?.[0];
      if (currentPage) document.title = `${currentPage} · ${adminPath ? 'Admin workspace' : 'Operations'}`;
      const nav = document.querySelector('nav');
      if (nav) {
        nav.querySelectorAll('a[data-workspace-link]').forEach(link => {
          const page = link.dataset.workspaceLink;
          link.href = pageLinks.find(([label]) => label.toLowerCase() === page)?.[1] || link.href;
        });
        const brand = nav.querySelector('[data-brand]');
        if (brand) brand.textContent = adminPath ? 'Dataset Request Desk · Admin' : 'Operations';
        const usersLink = nav.querySelector('[data-admin-link]');
        if (usersLink) usersLink.hidden = !adminPath;
      }
      return user;
    });
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

function showError(err) {
  showMessage(err?.message || 'Something went wrong. Please try again.', 'error');
}

function statusBadge(status) {
  const safeStatus = String(status || 'unknown');
  return `<span class="badge ${escapeHtml(safeStatus)}">${escapeHtml(safeStatus.replaceAll('_', ' '))}</span>`;
}

function progressBar(assigned, requested) {
  const total = Math.max(0, Number(requested) || 0);
  const count = Math.max(0, Number(assigned) || 0);
  const pct = total ? Math.min(100, Math.round((count / total) * 100)) : 0;
  return `<div class="progress-bar" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"><div style="width:${pct}%"></div></div><small>${count}/${total} episodes</small>`;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str ?? '';
  return div.innerHTML;
}

function createLoadMoreButton(container, fetchNextPage) {
  const btn = document.createElement('button');
  btn.textContent = 'Load more';
  btn.className = 'secondary';
  btn.dataset.pagination = 'true';
  btn.onclick = async () => {
    btn.disabled = true;
    btn.textContent = 'Loading…';
    try {
      const more = await fetchNextPage();
      if (more) {
        btn.disabled = false;
        btn.textContent = 'Load more';
      } else {
        btn.remove();
      }
    } catch (err) {
      showMessage(err.message, 'error');
      btn.disabled = false;
      btn.textContent = 'Load more';
    }
  };
  container.append(btn);
  return btn;
}
