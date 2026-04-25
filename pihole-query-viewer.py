#!/usr/bin/env python3
"""
Pi-hole Dual Query Viewer
Merges query logs from two Pi-hole v6 instances into a single filterable web view.
Usage: python3 pihole-query-viewer.py
Then open http://localhost:8088 in your browser.
"""

import json
import ssl
import urllib.request
import urllib.parse
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

# === CONFIGURATION ===
# Copy viewer-config.example.json to viewer-config.json and fill in your passwords.
import os as _os
_config_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "viewer-config.json")
if not _os.path.exists(_config_path):
    print(f"ERROR: Config file not found: {_config_path}")
    print("Copy viewer-config.example.json to viewer-config.json and fill in your passwords.")
    exit(1)
with open(_config_path) as _f:
    _cfg = json.load(_f)
PIHOLE_1 = _cfg["pihole_1"]
PIHOLE_2 = _cfg["pihole_2"]
LISTEN_PORT = _cfg.get("listen_port", 8088)
# === END CONFIGURATION ===

sessions = {}
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


def api_request(base_url, path, method="GET", data=None, sid=None):
    url = f"{base_url}/api{path}"
    headers = {"Content-Type": "application/json"}
    if sid:
        headers["sid"] = sid
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=10, context=ssl_ctx)
        return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}


def authenticate(pihole):
    key = pihole["url"]
    if key in sessions:
        return sessions[key]
    result = api_request(pihole["url"], "/auth", method="POST", data={"password": pihole["password"]})
    if result.get("session", {}).get("valid"):
        sid = result["session"]["sid"]
        sessions[key] = sid
        return sid
    return None


def fetch_queries(pihole, params=""):
    sid = authenticate(pihole)
    if not sid:
        return []
    result = api_request(pihole["url"], f"/queries?{params}", sid=sid)
    if "error" in result:
        # Session expired, re-authenticate
        sessions.pop(pihole["url"], None)
        sid = authenticate(pihole)
        if not sid:
            return []
        result = api_request(pihole["url"], f"/queries?{params}", sid=sid)
    queries = result.get("queries", [])
    for q in queries:
        q["_source"] = pihole["name"]
    return queries


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Pi-hole Dual Query Viewer</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: #1a1a2e; color: #e0e0e0; }
.header { background: #16213e; padding: 16px 24px; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.header h1 { font-size: 18px; color: #4ecca3; white-space: nowrap; }
.controls { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
input, select, button { padding: 6px 12px; border: 1px solid #333; border-radius: 4px; background: #0f3460; color: #e0e0e0; font-size: 13px; }
button { cursor: pointer; background: #4ecca3; color: #1a1a2e; font-weight: 600; border: none; }
button:hover { background: #3baa8a; }
.stats { padding: 8px 24px; background: #16213e; border-top: 1px solid #333; font-size: 12px; color: #888; display: flex; gap: 16px; }
.stats span { color: #4ecca3; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
thead { position: sticky; top: 0; background: #16213e; z-index: 1; }
th { padding: 8px 12px; text-align: left; color: #4ecca3; border-bottom: 2px solid #333; cursor: pointer; user-select: none; white-space: nowrap; }
th:hover { color: #fff; }
td { padding: 6px 12px; border-bottom: 1px solid #222; white-space: nowrap; max-width: 400px; overflow: hidden; text-overflow: ellipsis; }
tr:hover { background: #16213e; }
.allowed { color: #4ecca3; }
.blocked { color: #e74c3c; }
.source-primary { color: #9b59b6; }
.source-secondary { color: #e67e22; }
.table-wrap { overflow: auto; height: calc(100vh - 110px); }
.loading { text-align: center; padding: 40px; color: #888; }
#autoRefresh { accent-color: #4ecca3; }
label { font-size: 13px; cursor: pointer; display: flex; align-items: center; gap: 4px; }
</style>
</head>
<body>
<div class="header">
    <h1>Pi-hole Query Viewer</h1>
    <div class="controls">
        <input type="text" id="filterDomain" placeholder="Filter domain..." style="width:200px">
        <select id="filterStatus">
            <option value="">All</option>
            <option value="allowed">Allowed</option>
            <option value="blocked">Blocked</option>
        </select>
        <select id="filterSource">
            <option value="">Both Pi-holes</option>
            <option value="Primary">Primary</option>
            <option value="Secondary">Secondary</option>
        </select>
        <select id="filterType">
            <option value="">All types</option>
            <option value="A">A</option>
            <option value="AAAA">AAAA</option>
            <option value="HTTPS">HTTPS</option>
            <option value="SRV">SRV</option>
            <option value="SOA">SOA</option>
            <option value="PTR">PTR</option>
            <option value="TXT">TXT</option>
            <option value="MX">MX</option>
        </select>
        <select id="filterUpstream">
            <option value="">All upstreams</option>
        </select>
        <select id="queryCount">
            <option value="100">100 queries</option>
            <option value="250">250 queries</option>
            <option value="500" selected>500 queries</option>
            <option value="1000">1000 queries</option>
        </select>
        <button onclick="refresh()">Refresh</button>
        <label><input type="checkbox" id="autoRefresh"> Auto (30s)</label>
    </div>
</div>
<div class="stats" id="stats"></div>
<div class="table-wrap">
    <table>
        <thead>
            <tr>
                <th onclick="sortBy('time')">Time</th>
                <th onclick="sortBy('_source')">Source</th>
                <th onclick="sortBy('type')">Type</th>
                <th onclick="sortBy('domain')">Domain</th>
                <th onclick="sortBy('status')">Status</th>
                <th onclick="sortBy('upstream')">Upstream</th>
                <th onclick="sortBy('reply_type')">Reply</th>
                <th onclick="sortBy('client_name')">Client</th>
                <th onclick="sortBy('reply_time')">Time (ms)</th>
            </tr>
        </thead>
        <tbody id="tbody"></tbody>
    </table>
</div>
<script>
let allQueries = [];
let sortCol = 'time';
let sortAsc = false;
let autoTimer = null;

const BLOCKED_STATUSES = ['GRAVITY','REGEX','DENYLIST','EXTERNAL_BLOCKED','SPECIAL_DOMAIN','DBBUSY','BLOCKED'];
function isBlocked(s) { return BLOCKED_STATUSES.some(b => (s || '').toUpperCase().includes(b)); }

function formatTime(ts) {
    if (!ts) return '';
    const d = new Date(ts * 1000);
    return d.toLocaleTimeString('de-DE', {hour:'2-digit',minute:'2-digit',second:'2-digit'})
         + ' ' + d.toLocaleDateString('de-DE', {day:'2-digit',month:'2-digit'});
}

function flatten(q) {
    return {
        id: q.id,
        time: q.time,
        type: q.type || '',
        domain: q.domain || '',
        status: q.status || '',
        upstream: q.upstream || '',
        reply_type: (q.reply && q.reply.type) || '',
        reply_time: (q.reply && q.reply.time) || 0,
        client_ip: (q.client && q.client.ip) || '',
        client_name: (q.client && q.client.name) || (q.client && q.client.ip) || '',
        dnssec: q.dnssec || '',
        cname: q.cname || '',
        _source: q._source || ''
    };
}

async function refresh() {
    const count = document.getElementById('queryCount').value;
    document.getElementById('tbody').innerHTML = '<tr><td colspan="9" class="loading">Loading...</td></tr>';
    try {
        const resp = await fetch('/api/queries?length=' + count);
        const data = await resp.json();
        allQueries = (data.queries || []).map(flatten);
        updateUpstreamFilter();
        render();
    } catch(e) {
        document.getElementById('tbody').innerHTML = '<tr><td colspan="9" class="loading">Error: ' + e + '</td></tr>';
    }
}

function updateUpstreamFilter() {
    const sel = document.getElementById('filterUpstream');
    const current = sel.value;
    const upstreams = [...new Set(allQueries.map(q => q.upstream).filter(u => u))].sort();
    sel.innerHTML = '<option value="">All upstreams</option>' +
        upstreams.map(u => '<option value="' + u + '"' + (u === current ? ' selected' : '') + '>' + u + '</option>').join('');
}

function render() {
    const domainFilter = document.getElementById('filterDomain').value.toLowerCase();
    const statusFilter = document.getElementById('filterStatus').value;
    const sourceFilter = document.getElementById('filterSource').value;
    const typeFilter = document.getElementById('filterType').value;
    const upstreamFilter = document.getElementById('filterUpstream').value;

    let filtered = allQueries.filter(q => {
        if (domainFilter && !q.domain.toLowerCase().includes(domainFilter)) return false;
        if (statusFilter === 'blocked' && !isBlocked(q.status)) return false;
        if (statusFilter === 'allowed' && isBlocked(q.status)) return false;
        if (sourceFilter && q._source !== sourceFilter) return false;
        if (typeFilter && q.type !== typeFilter) return false;
        if (upstreamFilter && q.upstream !== upstreamFilter) return false;
        return true;
    });

    filtered.sort((a, b) => {
        let va = a[sortCol] ?? '', vb = b[sortCol] ?? '';
        if (sortCol === 'time' || sortCol === 'reply_time') { va = Number(va) || 0; vb = Number(vb) || 0; }
        else { va = String(va).toLowerCase(); vb = String(vb).toLowerCase(); }
        if (va < vb) return sortAsc ? -1 : 1;
        if (va > vb) return sortAsc ? 1 : -1;
        return 0;
    });

    const total = allQueries.length;
    const blocked = allQueries.filter(q => isBlocked(q.status)).length;
    const allowed = total - blocked;
    const primary = allQueries.filter(q => q._source === 'Primary').length;
    const secondary = allQueries.filter(q => q._source === 'Secondary').length;
    document.getElementById('stats').innerHTML =
        'Total: <span>' + total + '</span> | Shown: <span>' + filtered.length + '</span> | Allowed: <span>' + allowed + '</span> | Blocked: <span class="blocked">' + blocked + '</span> | Primary: <span>' + primary + '</span> | Secondary: <span>' + secondary + '</span>';

    const html = filtered.map(q => {
        const srcClass = q._source === 'Primary' ? 'source-primary' : 'source-secondary';
        return '<tr>' +
            '<td>' + formatTime(q.time) + '</td>' +
            '<td class="' + srcClass + '">' + q._source + '</td>' +
            '<td>' + q.type + '</td>' +
            '<td title="' + q.domain + '">' + q.domain + '</td>' +
            '<td class="' + (isBlocked(q.status) ? 'blocked' : 'allowed') + '">' + q.status + '</td>' +
            '<td>' + q.upstream + '</td>' +
            '<td>' + q.reply_type + '</td>' +
            '<td title="' + q.client_ip + '">' + q.client_name + '</td>' +
            '<td>' + (q.reply_time > 0 ? (q.reply_time * 1000).toFixed(1) : '') + '</td>' +
        '</tr>';
    }).join('');
    document.getElementById('tbody').innerHTML = html || '<tr><td colspan="9" class="loading">No queries match filters</td></tr>';
}

function sortBy(col) {
    if (sortCol === col) sortAsc = !sortAsc;
    else { sortCol = col; sortAsc = col === 'domain'; }
    render();
}

document.getElementById('filterDomain').addEventListener('input', render);
document.getElementById('filterStatus').addEventListener('change', render);
document.getElementById('filterSource').addEventListener('change', render);
document.getElementById('filterType').addEventListener('change', render);
document.getElementById('filterUpstream').addEventListener('change', render);

document.getElementById('autoRefresh').addEventListener('change', function() {
    if (this.checked) { autoTimer = setInterval(refresh, 30000); }
    else { clearInterval(autoTimer); autoTimer = null; }
});

refresh();
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode())

        elif self.path.startswith("/api/queries"):
            query_string = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query_string)
            length = params.get("length", ["500"])[0]

            api_params = f"length={length}"
            queries_1 = fetch_queries(PIHOLE_1, api_params)
            queries_2 = fetch_queries(PIHOLE_2, api_params)

            merged = queries_1 + queries_2
            merged.sort(key=lambda q: q.get("time", 0), reverse=True)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"queries": merged}).encode())

        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    if not PIHOLE_1["password"] or not PIHOLE_2["password"]:
        print("ERROR: Set Pi-hole web passwords in the script configuration!")
        print("Edit pihole-query-viewer.py and fill in PIHOLE_1['password'] and PIHOLE_2['password']")
        exit(1)

    print(f"Pi-hole Dual Query Viewer")
    print(f"  Primary:   {PIHOLE_1['url']}")
    print(f"  Secondary: {PIHOLE_2['url']}")
    print(f"  Open http://localhost:{LISTEN_PORT} in your browser")
    server = HTTPServer(("0.0.0.0", LISTEN_PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
