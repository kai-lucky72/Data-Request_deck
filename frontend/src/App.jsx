import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

const API = '/'
const routes = {
  client: [{ path: '/client', label: 'My requests' }],
  operator: [
    { path: '/operator/requests', label: 'Requests' },
    { path: '/operator/episodes', label: 'Episodes' },
    { path: '/operator/analytics', label: 'Analytics' },
  ],
  admin: [
    { path: '/admin/users', label: 'Users' },
    { path: '/admin/requests', label: 'Requests' },
    { path: '/admin/episodes', label: 'Episodes' },
    { path: '/admin/analytics', label: 'Analytics' },
  ],
}
const titleByPath = {
  '/client': 'My requests', '/operator/requests': 'Request queue', '/admin/requests': 'Request queue',
  '/operator/episodes': 'Episode library', '/admin/episodes': 'Episode library',
  '/operator/analytics': 'Analytics', '/admin/analytics': 'Analytics', '/admin/users': 'User management',
}

function readToken() { return sessionStorage.getItem('access_token') }
async function api(path, options = {}) {
  const headers = new Headers(options.headers || {})
  if (!(options.body instanceof FormData) && !(options.body instanceof URLSearchParams) && options.body) headers.set('Content-Type', 'application/json')
  if (readToken()) headers.set('Authorization', `Bearer ${readToken()}`)
  const response = await fetch(`${API}${path.replace(/^\//, '')}`, { ...options, headers })
  if (response.status === 204) return null
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`)
  return data
}
function go(path) { history.pushState({}, '', path); window.dispatchEvent(new PopStateEvent('popstate')) }
function fmtDate(value) { return value ? new Date(`${value.slice(0, 10)}T00:00:00`).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) : '—' }
function statusLabel(value) { return String(value || '').replaceAll('_', ' ') }

function App() {
  const [path, setPath] = useState(location.pathname)
  const [user, setUser] = useState(null)
  const [checking, setChecking] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    const pop = () => setPath(location.pathname)
    window.addEventListener('popstate', pop)
    return () => window.removeEventListener('popstate', pop)
  }, [])
  useEffect(() => {
    let active = true
    if (!readToken()) { setChecking(false); setUser(null); return () => { active = false } }
    api('/auth/me').then(profile => { if (active) setUser(profile) }).catch(() => {
      sessionStorage.removeItem('access_token'); if (active) setUser(null)
    }).finally(() => { if (active) setChecking(false) })
    return () => { active = false }
  }, [])
  const flash = (message) => { setNotice(message); window.setTimeout(() => setNotice(''), 3500) }
  const signOut = () => { sessionStorage.removeItem('access_token'); setUser(null); setError(''); go('/login') }

  useEffect(() => {
    if (checking) return
    if (!user && path !== '/login') { go('/login'); return }
    if (user && path === '/login') { go(homeFor(user.role)); return }
    if (!user) return
    const prefix = user.role === 'admin' ? '/admin' : user.role === 'operator' ? '/operator' : '/client'
    if (!path.startsWith(prefix)) go(homeFor(user.role))
  }, [checking, user, path])

  if (checking) return <div className="boot"><span className="spinner" />Loading your workspace…</div>
  if (!user) return <Login error={error} setError={setError} onLogin={profile => { setUser(profile); setError(''); go(homeFor(profile.role)) }} />
  const nav = routes[user.role] || []
  const content = path === '/client' && user.role === 'client'
    ? <ClientHome flash={flash} setError={setError} />
    : path.endsWith('/requests') && user.role !== 'client'
      ? <RequestQueue user={user} flash={flash} setError={setError} />
      : path.endsWith('/episodes') && user.role !== 'client'
        ? <Episodes flash={flash} setError={setError} />
        : path.endsWith('/analytics') && user.role !== 'client'
          ? <Analytics setError={setError} />
          : path === '/admin/users' && user.role === 'admin'
            ? <Users user={user} flash={flash} setError={setError} />
            : <ClientHome flash={flash} setError={setError} />

  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href={homeFor(user.role)} onClick={e => { e.preventDefault(); go(homeFor(user.role)) }}><span className="brand-mark">D</span><span>Dataset Desk<small>REQUEST MANAGEMENT</small></span></a>
      <div className="workspace-label">WORKSPACE</div>
      <nav>{nav.map(item => <a key={item.path} href={item.path} className={`nav-link ${path === item.path ? 'active' : ''}`} onClick={e => { e.preventDefault(); setError(''); go(item.path) }}><span className="nav-dot" />{item.label}</a>)}</nav>
      <div className="sidebar-bottom"><div className="secure-note"><span>●</span> Secure workspace</div><div className="profile"><div className="avatar">{user.name?.slice(0, 1)?.toUpperCase() || 'U'}</div><div className="profile-copy"><strong>{user.name}</strong><small>{user.role}</small></div><button className="icon-button" onClick={signOut} title="Sign out" aria-label="Sign out">↗</button></div></div>
    </aside>
    <main className="main-area"><header className="topbar"><div className="breadcrumbs">Workspace <span>/</span> <strong>{titleByPath[path] || 'Workspace'}</strong></div><div className="topbar-right"><span className="role-chip">{user.role}</span><span className="user-email">{user.email}</span></div></header>
      <div className="page-wrap"><div className="page-heading"><div><div className="eyebrow">{user.role === 'client' ? 'CLIENT PORTAL' : user.role === 'admin' ? 'ADMINISTRATION' : 'OPERATIONS'}</div><h1>{titleByPath[path] || 'Workspace'}</h1></div></div>
        {error && <div className="alert error"><span>!</span>{error}<button onClick={() => setError('')} aria-label="Dismiss">×</button></div>}
        {notice && <div className="alert success"><span>✓</span>{notice}</div>}
        {content}
      </div>
    </main>
  </div>
}
function homeFor(role) { return role === 'admin' ? '/admin/users' : role === 'operator' ? '/operator/requests' : '/client' }

function Login({ onLogin, error, setError }) {
  const [busy, setBusy] = useState(false)
  async function submit(e) {
    e.preventDefault(); setBusy(true); setError('')
    const form = new URLSearchParams(new FormData(e.currentTarget))
    try {
      const token = await api('/auth/login', { method: 'POST', body: form, headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })
      sessionStorage.setItem('access_token', token.access_token)
      const profile = await api('/auth/me')
      onLogin(profile)
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  return <div className="login-screen"><section className="login-art"><div className="art-logo"><span className="brand-mark">D</span> Dataset Desk</div><div className="art-content"><div className="eyebrow light">DATASET REQUEST MANAGEMENT</div><h1>Every dataset request,<br /><em>in its right place.</em></h1><p>A clear path from request to delivery for clients and operations teams.</p><div className="art-card"><span className="art-card-icon">✓</span><div><strong>One coordinated workspace</strong><small>Track status, assignments, and delivery progress.</small></div></div></div><div className="art-footer">Dataset Request Desk <span>•</span> Secure access</div></section>
    <section className="login-panel"><div className="login-box"><div className="eyebrow">WELCOME BACK</div><h2>Sign in to continue</h2><p className="muted">Use your account credentials to open your workspace.</p>{error && <div className="alert error"><span>!</span>{error}</div>}<form onSubmit={submit} className="form-stack"><label>Email address<input name="username" type="email" placeholder="you@company.com" autoComplete="username" required /></label><label>Password<input name="password" type="password" placeholder="Enter your password" autoComplete="current-password" required /></label><button className="button primary full" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}<span>→</span></button></form><div className="login-foot">Need access? Contact your workspace administrator.</div></div></section></div>
}

function useLoad(loader, deps = []) {
  const [data, setData] = useState(null); const [loading, setLoading] = useState(true); const [error, setError] = useState('')
  const reload = useCallback(async () => { setLoading(true); setError(''); try { setData(await loader()) } catch (e) { setError(e.message) } finally { setLoading(false) } }, deps)
  useEffect(() => { reload() }, [reload])
  return { data, loading, error, reload }
}
function useLiveUpdates(onUpdate, interestedEvents) {
  const callback = useRef(onUpdate)
  callback.current = onUpdate
  const eventKey = interestedEvents.join(',')
  useEffect(() => {
    if (!readToken()) return undefined
    let stopped = false
    let controller
    let retryTimer
    let retryResolve
    let refreshTimer
    const interested = new Set(eventKey.split(','))
    const connect = async () => {
      let delay = 1000
      while (!stopped) {
        controller = new AbortController()
        try {
          const response = await fetch('/events', {
            headers: { Authorization: `Bearer ${readToken()}`, Accept: 'text/event-stream' },
            cache: 'no-store',
            signal: controller.signal,
          })
          if (response.status === 401 || response.status === 403) break
          if (!response.ok || !response.body) throw new Error(`Live updates unavailable (${response.status})`)
          delay = 1000
          const reader = response.body.getReader()
          const decoder = new TextDecoder()
          let buffer = ''
          while (!stopped) {
            const { value, done } = await reader.read()
            if (done) break
            buffer += decoder.decode(value, { stream: true }).replaceAll('\r\n', '\n')
            let boundary
            while ((boundary = buffer.indexOf('\n\n')) >= 0) {
              const frame = buffer.slice(0, boundary)
              buffer = buffer.slice(boundary + 2)
              const data = frame.split('\n').filter(line => line.startsWith('data:')).map(line => line.slice(5).trim()).join('\n')
              if (!data) continue
              try {
                const event = JSON.parse(data)
                if (interested.has(event.type)) {
                  window.clearTimeout(refreshTimer)
                  refreshTimer = window.setTimeout(() => callback.current(), 180)
                }
              } catch { /* Ignore malformed frames and keep the connection alive. */ }
            }
          }
        } catch (error) {
          if (stopped || error.name === 'AbortError') break
        }
        if (!stopped) {
          await new Promise(resolve => {
            retryResolve = resolve
            retryTimer = window.setTimeout(resolve, delay)
          })
          delay = Math.min(delay * 2, 15000)
        }
      }
    }
    connect()
    return () => {
      stopped = true
      controller?.abort()
      window.clearTimeout(retryTimer)
      window.clearTimeout(refreshTimer)
      retryResolve?.()
    }
  }, [eventKey])
}
function InlineLoad({ loading, error, empty, isEmpty = false, children }) { if (loading) return <div className="inline-state"><span className="spinner" />Loading…</div>; if (error) return <div className="inline-state error-text">{error}</div>; if (isEmpty && empty) return <div className="empty-state"><span className="empty-icon">⌁</span><strong>Nothing here yet</strong><p>{empty}</p></div>; return children }
function Status({ value }) { return <span className={`status status-${value}`}>{statusLabel(value)}</span> }

function ClientHome({ flash, setError }) {
  const [showForm, setShowForm] = useState(false)
  const { data: requests, loading, error, reload } = useLoad(() => api('/requests?limit=100'))
  useLiveUpdates(reload, ['requests_changed'])
  async function create(e) {
    e.preventDefault(); const form = new FormData(e.currentTarget)
    try { await api('/requests', { method: 'POST', body: JSON.stringify({ task_name: form.get('task_name'), episodes_requested: Number(form.get('episodes_requested')), deadline: form.get('deadline'), notes: form.get('notes') || null }) }); setShowForm(false); e.currentTarget?.reset?.(); await reload(); flash('Your dataset request has been submitted.') } catch (err) { setError(err.message) }
  }
  async function decide(request, status) {
    try { await api(`/requests/${request.id}/status`, { method: 'PATCH', body: JSON.stringify({ status, note: status === 'accepted' ? 'Accepted by client' : 'Rejected by client' }) }); await reload(); flash(`Request #${request.id} ${status}.`) } catch (err) { setError(err.message) }
  }
  const rows = requests || []
  return <>
    <section className="welcome-banner"><div><div className="eyebrow light">YOUR DATA, IN MOTION</div><h2>Good to see you.</h2><p>Follow every request from submission through delivery.</p></div><div className="banner-stat"><span>{rows.length}</span><small>TOTAL REQUESTS</small></div></section>
    <div className="section-head"><div><h2>Your requests</h2><p>Review current status and respond to completed deliveries.</p></div><button className="button primary" onClick={() => setShowForm(v => !v)}>{showForm ? 'Close form' : '+ New request'}</button></div>
    {showForm && <form className="panel request-form" onSubmit={create}><div className="panel-title"><div><h3>Request a dataset</h3><p>Tell the operations team what you need.</p></div><span className="step-badge">NEW</span></div><div className="form-grid"><label>Task name<input name="task_name" placeholder="e.g. Object sorting" required maxLength="255" /></label><label>Episodes requested<input name="episodes_requested" type="number" min="1" placeholder="100" required /></label><label>Needed by<input name="deadline" type="date" min={new Date().toISOString().slice(0, 10)} required /></label><label className="span-2">Notes <span className="optional">(optional)</span><textarea name="notes" rows="3" placeholder="Add any details that may help fulfil this request" /></label></div><div className="form-actions"><button className="button primary">Submit request <span>→</span></button></div></form>}
    <InlineLoad loading={loading} error={error} empty="Create your first request to get started." isEmpty={rows.length === 0}><div className="request-list">{rows.map(request => <article className="panel request-card" key={request.id}><div className="request-main"><div className="request-icon">{request.task_name?.slice(0, 1)?.toUpperCase()}</div><div className="request-title"><div className="request-name-row"><h3>{request.task_name}</h3><Status value={request.status} /></div><div className="request-meta">Request #{request.id} <span>·</span> Submitted {fmtDate(request.created_at)}</div></div></div><div className="request-details"><div><small>EPISODES</small><strong>{request.assigned_count} <span>/ {request.episodes_requested}</span></strong><div className="progress"><i style={{ width: `${Math.min(100, request.assigned_count / request.episodes_requested * 100)}%` }} /></div></div><div><small>NEEDED BY</small><strong>{fmtDate(request.deadline)}</strong></div><div className="client-actions">{request.status === 'delivered' ? <><button className="button primary small" onClick={() => decide(request, 'accepted')}>Accept delivery</button><button className="button quiet small" onClick={() => decide(request, 'rejected')}>Request changes</button></> : <span className="updated-label">Updated {fmtDate(request.updated_at)}</span>}</div></div></article>)}</div></InlineLoad>
  </>
}

function RequestQueue({ user, flash, setError }) {
  const [filter, setFilter] = useState('all')
  const { data, loading, error, reload } = useLoad(() => api('/requests?limit=100'))
  useLiveUpdates(reload, ['requests_changed'])
  const requests = useMemo(() => (data || []).filter(r => filter === 'all' || r.status === filter), [data, filter])
  async function changeStatus(request, status) {
    try { await api(`/requests/${request.id}/status`, { method: 'PATCH', body: JSON.stringify({ status, note: `Updated by ${user.name}` }) }); await reload(); flash(`Request #${request.id} moved to ${statusLabel(status)}.`) } catch (e) { setError(e.message) }
  }
  const next = { submitted: ['in_progress'], in_progress: ['delivered'], rejected: ['in_progress'] }
  return <><div className="summary-strip"><div><span className="summary-icon blue">▤</span><div><strong>{data?.length || 0}</strong><small>ALL REQUESTS</small></div></div><div><span className="summary-icon amber">◷</span><div><strong>{(data || []).filter(r => ['submitted', 'in_progress'].includes(r.status)).length}</strong><small>IN PROGRESS</small></div></div><div><span className="summary-icon green">✓</span><div><strong>{(data || []).filter(r => r.status === 'delivered').length}</strong><small>DELIVERED</small></div></div></div><div className="section-head"><div><h2>All requests</h2><p>Manage the queue and keep each request moving.</p></div><div className="select-wrap"><select value={filter} onChange={e => setFilter(e.target.value)}><option value="all">All statuses</option>{['submitted', 'in_progress', 'delivered', 'accepted', 'rejected'].map(s => <option key={s} value={s}>{statusLabel(s)}</option>)}</select></div></div><InlineLoad loading={loading} error={error} empty="New client requests will appear here." isEmpty={requests.length === 0}><div className="table-panel"><div className="table-scroll"><table><thead><tr><th>REQUEST</th><th>CLIENT</th><th>EPISODES</th><th>DEADLINE</th><th>STATUS</th><th>ACTIONS</th></tr></thead><tbody>{requests.map(r => <tr key={r.id}><td><strong>{r.task_name}</strong><small className="cell-sub">Request #{r.id} · {fmtDate(r.created_at)}</small></td><td>{r.client_name || `Client #${r.client_id}`}</td><td><strong>{r.assigned_count}</strong><span className="muted"> / {r.episodes_requested}</span></td><td>{fmtDate(r.deadline)}</td><td><Status value={r.status} /></td><td><div className="row-actions">{(next[r.status] || []).map(s => <button className="button small secondary" key={s} onClick={() => changeStatus(r, s)}>{s === 'in_progress' ? 'Start / Reopen' : 'Mark delivered'}</button>)}{['submitted', 'in_progress', 'rejected'].includes(r.status) && <a className="text-link" href={`${user.role === 'admin' ? '/admin' : '/operator'}/episodes?request=${r.id}`} onClick={e => { e.preventDefault(); sessionStorage.setItem('target_request', String(r.id)); go(user.role === 'admin' ? '/admin/episodes' : '/operator/episodes') }}>Assign episodes</a>}</div></td></tr>)}</tbody></table></div></div></InlineLoad></>
}

function Episodes({ flash, setError }) {
  const [task, setTask] = useState(''); const [quality, setQuality] = useState(''); const [search, setSearch] = useState({ task: '', quality: '' }); const [target, setTarget] = useState(sessionStorage.getItem('target_request') || ''); const [uploading, setUploading] = useState(false); const [report, setReport] = useState(null)
  const load = useCallback(() => { const q = new URLSearchParams({ available_only: 'true', limit: '200' }); if (search.task) q.set('task_name', search.task); if (search.quality) q.set('quality', search.quality); return api(`/episodes?${q}`) }, [search])
  const { data: episodes, loading, error, reload } = useLoad(load, [load])
  useLiveUpdates(reload, ['episodes_changed'])
  async function assign(episode) {
    if (!target || Number(target) < 1) { setError('Enter a request ID before assigning an episode.'); return }
    try { await api(`/episodes/requests/${target}/assignments`, { method: 'POST', body: JSON.stringify({ episode_id: episode.id }) }); await reload(); flash(`Episode ${episode.episode_id} assigned to request #${target}.`) } catch (e) { setError(e.message) }
  }
  async function importFile(e) {
    const file = e.currentTarget.files?.[0]; if (!file) return
    const body = new FormData(); body.append('file', file); setUploading(true); setReport(null)
    try { const result = await api('/episodes/import', { method: 'POST', body }); setReport(result); await reload(); flash(`Import complete: ${result.imported} added, ${result.skipped} skipped.`) } catch (err) { setError(err.message) } finally { setUploading(false); e.target.value = '' }
  }
  return <><div className="section-head"><div><h2>Available episodes</h2><p>Filter the catalog, then assign episodes to an open request.</p></div><label className="button secondary upload-button">{uploading ? 'Importing…' : '↑ Import CSV'}<input type="file" accept=".csv,text/csv" onChange={importFile} disabled={uploading} /></label></div>{report && <div className="import-report"><strong>Import finished</strong><span>{report.imported} imported</span><span>{report.skipped} skipped</span>{report.issues?.slice(0, 3).map((issue, i) => <small key={i}>Row {issue.row}: {issue.reason}</small>)}</div>}<div className="filter-panel"><label>Task name<input value={task} onChange={e => setTask(e.target.value)} onKeyDown={e => e.key === 'Enter' && setSearch({ task, quality })} placeholder="Filter by task" /></label><label>Quality<select value={quality} onChange={e => { setQuality(e.target.value); setSearch({ task, quality: e.target.value }) }}><option value="">All qualities</option><option value="good">Good</option><option value="usable">Usable</option><option value="bad">Bad</option></select></label><button className="button secondary" onClick={() => setSearch({ task, quality })}>Apply filters</button><div className="filter-spacer" /><label className="request-target">Assign to request<input type="number" min="1" value={target} onChange={e => { setTarget(e.target.value); sessionStorage.setItem('target_request', e.target.value) }} placeholder="Request ID" /></label></div><InlineLoad loading={loading} error={error} empty="No available episodes match these filters. Import a CSV or adjust the search." isEmpty={(episodes || []).length === 0}><div className="table-panel"><div className="table-scroll"><table><thead><tr><th>EPISODE</th><th>TASK</th><th>ROBOT</th><th>RECORDED</th><th>DURATION</th><th>QUALITY</th><th /></tr></thead><tbody>{(episodes || []).map(ep => <tr key={ep.id}><td><strong>{ep.episode_id}</strong></td><td>{ep.task_name}</td><td>{ep.robot_id}</td><td>{new Date(ep.recorded_at).toLocaleDateString()}</td><td>{ep.duration_seconds}s</td><td><span className={`quality quality-${ep.quality}`}>{ep.quality}</span></td><td><button className="button small secondary" disabled={!target} onClick={() => assign(ep)}>Assign</button></td></tr>)}</tbody></table></div></div></InlineLoad></>
}

function Analytics({ setError }) {
  const today = new Date().toISOString().slice(0, 10); const first = new Date(); first.setDate(first.getDate() - 30)
  const [dates, setDates] = useState({ start_date: first.toISOString().slice(0, 10), end_date: today, robot_id: '' }); const [query, setQuery] = useState(dates); const [offset, setOffset] = useState(0)
  const load = useCallback(() => { const p = new URLSearchParams({ ...query, limit: '20', offset: String(offset) }); if (!query.robot_id) p.delete('robot_id'); return api(`/analytics?${p}`) }, [query, offset])
  const { data, loading, error, reload } = useLoad(load, [load])
  useLiveUpdates(reload, ['requests_changed', 'episodes_changed'])
  async function apply(e) { e.preventDefault(); if (dates.end_date < dates.start_date) { setError('End date must be on or after start date.'); return }; setOffset(0); setQuery(dates) }
  const totalRequests = Object.values(data?.requests_by_status || {}).reduce((a, b) => a + b, 0)
  return <><form className="filter-panel analytics-filters" onSubmit={apply}><label>From<input type="date" value={dates.start_date} onChange={e => setDates({ ...dates, start_date: e.target.value })} required /></label><label>To<input type="date" value={dates.end_date} onChange={e => setDates({ ...dates, end_date: e.target.value })} required /></label><label>Robot ID <span className="optional">(optional)</span><input value={dates.robot_id} onChange={e => setDates({ ...dates, robot_id: e.target.value })} placeholder="All robots" /></label><button className="button primary">Update report</button></form><InlineLoad loading={loading} error={error} empty={null}>{data && <><div className="metric-grid"><Metric label="Requests in range" value={totalRequests} tone="blue" /><Metric label="Episode groups" value={data.total_episode_day_robot_groups ?? data.episodes_per_day_per_robot?.length ?? 0} tone="purple" /><Metric label="Median delivery" value={data.median_submitted_to_delivered_seconds == null ? '—' : `${Math.round(data.median_submitted_to_delivered_seconds / 3600)}h`} tone="green" /></div><div className="analytics-grid"><section className="panel"><div className="panel-title"><div><h3>Requests by status</h3><p>Requests created in the selected date range.</p></div></div><div className="status-breakdown">{Object.entries(data.requests_by_status || {}).length ? Object.entries(data.requests_by_status).map(([s, n]) => <div key={s}><span><Status value={s} /></span><strong>{n}</strong><i><b style={{ width: `${totalRequests ? n / totalRequests * 100 : 0}%` }} /></i></div>) : <p className="muted">No requests in this period.</p>}</div></section><section className="panel"><div className="panel-title"><div><h3>Top good episode tasks</h3><p>Most frequent tasks with good quality.</p></div></div>{data.top_5_good_episode_tasks?.length ? <div className="task-rank">{data.top_5_good_episode_tasks.map((task, i) => <div key={task.task_name}><span className="rank">0{i + 1}</span><strong>{task.task_name}</strong><span className="rank-count">{task.count}</span></div>)}</div> : <p className="muted">No good quality episodes in this period.</p>}</section></div><section className="panel analytics-table"><div className="panel-title"><div><h3>Episode activity</h3><p>Episodes recorded by day and robot.</p></div></div><div className="table-scroll"><table><thead><tr><th>DATE</th><th>ROBOT</th><th>EPISODES</th></tr></thead><tbody>{data.episodes_per_day_per_robot?.map((item, i) => <tr key={`${item.date}-${item.robot_id}-${i}`}><td>{fmtDate(item.date)}</td><td>{item.robot_id}</td><td><strong>{item.count}</strong></td></tr>)}</tbody></table>{data.episodes_per_day_per_robot?.length === 0 && <p className="muted table-empty">No episode data in this period.</p>}</div>{(data.total_episode_day_robot_groups || 0) > 20 && <div className="pager"><button className="button small secondary" disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 20))}>Previous</button><span>{offset + 1}–{Math.min(offset + 20, data.total_episode_day_robot_groups)} of {data.total_episode_day_robot_groups}</span><button className="button small secondary" disabled={offset + 20 >= data.total_episode_day_robot_groups} onClick={() => setOffset(offset + 20)}>Next</button></div>}</section></>}</InlineLoad></>
}
function Metric({ label, value, tone }) { return <div className="metric-card"><span className={`metric-mark ${tone}`} /><div><small>{label.toUpperCase()}</small><strong>{value}</strong></div></div> }

function Users({ user, flash, setError }) {
  const [creating, setCreating] = useState(false); const { data, loading, error, reload } = useLoad(() => api('/users'))
  async function create(e) { e.preventDefault(); const f = new FormData(e.currentTarget); try { await api('/users', { method: 'POST', body: JSON.stringify({ email: f.get('email'), name: f.get('name'), role: f.get('role'), organisation: f.get('organisation') || null, password: f.get('password') }) }); setCreating(false); await reload(); flash('Account created.') } catch (err) { setError(err.message) } }
  async function active(person) { try { await api(`/users/${person.id}/active?active=${!person.is_active}`, { method: 'PATCH' }); await reload(); flash(`${person.name} ${person.is_active ? 'deactivated' : 'activated'}.`) } catch (e) { setError(e.message) } }
  async function role(person, value) { try { await api(`/users/${person.id}/role`, { method: 'PATCH', body: JSON.stringify({ role: value }) }); await reload(); flash(`${person.name}'s role updated.`) } catch (e) { setError(e.message) } }
  return <><div className="section-head"><div><h2>Workspace accounts</h2><p>Create and maintain client and operations access.</p></div><button className="button primary" onClick={() => setCreating(v => !v)}>{creating ? 'Cancel' : '+ Add user'}</button></div>{creating && <form className="panel request-form" onSubmit={create}><div className="panel-title"><div><h3>Create account</h3><p>New users can sign in as soon as their account is created.</p></div></div><div className="form-grid"><label>Full name<input name="name" required /></label><label>Email<input type="email" name="email" required /></label><label>Role<select name="role"><option value="client">Client</option><option value="operator">Operator</option><option value="admin">Admin</option></select></label><label>Organisation <span className="optional">(optional)</span><input name="organisation" /></label><label>Password<input type="password" name="password" minLength="8" required /></label></div><div className="form-actions"><button className="button primary">Create account</button></div></form>}<InlineLoad loading={loading} error={error} empty="There are no accounts yet." isEmpty={(data || []).length === 0}><div className="table-panel"><div className="table-scroll"><table><thead><tr><th>USER</th><th>ORGANISATION</th><th>ROLE</th><th>STATUS</th><th>ACCOUNT</th></tr></thead><tbody>{(data || []).map(p => <tr key={p.id}><td><div className="user-cell"><span className="avatar small-avatar">{p.name.slice(0, 1).toUpperCase()}</span><span><strong>{p.name}</strong><small className="cell-sub">{p.email}</small></span></div></td><td>{p.organisation || '—'}</td><td>{p.id === user.id ? <Status value={p.role} /> : <select className="inline-select" value={p.role} onChange={e => role(p, e.target.value)}><option value="client">Client</option><option value="operator">Operator</option><option value="admin">Admin</option></select>}</td><td><span className={`active-dot ${p.is_active ? 'on' : ''}`} />{p.is_active ? 'Active' : 'Inactive'}</td><td><button className="text-link" disabled={p.id === user.id} onClick={() => active(p)}>{p.id === user.id ? 'Current account' : p.is_active ? 'Deactivate' : 'Activate'}</button></td></tr>)}</tbody></table></div></div></InlineLoad></>
}

export default App
