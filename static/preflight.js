'use strict';
const statusNode = document.getElementById('server-status');
const refreshButton = document.getElementById('refresh');
const agentsNode = document.getElementById('agents');
function detail(list, name, value) {
    const term = document.createElement('dt');
    term.textContent = name;
    const description = document.createElement('dd');
    description.textContent = value;
    list.append(term, description);
}
// A chip is only 'good' when a check positively proved it; unknown stays neutral.
function chip(parent, label, value, tone = 'unknown') {
    const node = document.createElement('span');
    node.className = `pf-chip pf-chip--${tone}`;
    node.textContent = `${label}: ${value}`;
    parent.append(node);
    return node;
}
function emptyState(text, hint) {
    const box = document.createElement('div');
    box.className = 'pf-empty';
    const title = document.createElement('p');
    title.textContent = text;
    box.append(title);
    if (hint) {
        const more = document.createElement('p');
        more.className = 'pf-dim';
        more.textContent = hint;
        box.append(more);
    }
    return box;
}
// A CLI launched through an interpreter (an MCP-safe wrapper script) resolves to
// that interpreter, not the client program itself.
const WRAPPER_COMMANDS = new Set(['python', 'python3', 'pythonw', 'py', 'node', 'pwsh', 'powershell', 'cmd', 'bash', 'sh']);
function isWrapper(path) {
    const base = String(path || '').split(/[\\/]/).pop().toLowerCase().replace(/\.exe$/, '');
    return WRAPPER_COMMANDS.has(base);
}
function agentRow(agent) {
    const card = document.createElement('article');
    card.className = 'pf-agent';
    const head = document.createElement('div');
    head.className = 'pf-agent-head';
    const title = document.createElement('h3');
    title.textContent = agent.label || agent.name;
    const kind = document.createElement('span');
    kind.className = 'pf-kind';
    kind.textContent = agent.client_type === 'api' ? 'API' : 'CLI';
    head.append(title, kind);
    const chips = document.createElement('div');
    chips.className = 'pf-chips';
    const wrapper = agent.client_type !== 'api' && agent.executable_found && isWrapper(agent.executable);
    if (agent.client_type === 'api') chip(chips, 'Program', 'not needed', 'neutral');
    else if (wrapper) chip(chips, 'Launch command', 'found (wrapper)', 'good');
    else if (agent.executable_found) chip(chips, 'Program', 'found', 'good');
    else chip(chips, 'Program', 'not found on PATH', 'bad');
    chip(chips, 'Version', agent.version || 'unknown');
    chip(chips, 'Sign-in', agent.authentication || 'unknown');
    chip(chips, 'Ready', agent.ready ? 'yes' : 'not verified', agent.ready ? 'good' : 'unknown');
    const more = document.createElement('details');
    more.className = 'pf-agent-more';
    const summary = document.createElement('summary');
    summary.textContent = 'Details';
    const list = document.createElement('dl');
    if (wrapper) {
        detail(list, 'Launch command (wrapper)', agent.executable);
        detail(list, 'Client', `${agent.label || agent.name} (${agent.name})`);
    } else detail(list, 'Executable', agent.client_type === 'api' ? 'API agent · no executable required' :
        (agent.executable_found ? agent.executable : 'Not found on PATH'));
    detail(list, 'Version', agent.version || 'Unknown');
    detail(list, 'Startup', agent.startup_checked ? 'Checked' : 'Not checked');
    detail(list, 'Authentication', agent.authentication);
    detail(list, 'Adapter connection', agent.adapter_connected);
    detail(list, 'Ready', agent.ready ? 'Yes' : 'Not verified');
    more.append(summary, list);
    card.append(head, chips, more);
    return card;
}
async function refreshChecks() {
    refreshButton.disabled = true;
    statusNode.className = 'pf-server';
    statusNode.textContent = 'Checking connection…';
    if (!agentsNode.children.length) agentsNode.replaceChildren(emptyState('Looking for configured agents…'));
    try {
        const response = await fetch('/api/preflight', {
            headers: {'x-session-token': window.__SESSION_TOKEN__},
            cache: 'no-store', signal: AbortSignal.timeout(10000),
        });
        if (!response.ok) throw new Error(`Server returned ${response.status}. Reload this page to refresh your session.`);
        const snapshot = await response.json();
        agentsNode.replaceChildren(...snapshot.agents.map(agentRow));
        const missing = snapshot.agents.filter(a => a.client_type !== 'api' && !a.executable_found).length;
        const summary = document.getElementById('agents-summary');
        if (summary) summary.textContent = !snapshot.agents.length ? 'No agents configured' :
            `Available agents: ${snapshot.agents.length}` + (missing ? ` · ${missing} not found` : '');
        if (!snapshot.agents.length) agentsNode.replaceChildren(emptyState('No agents configured yet.',
            'Add them under [agents] in config.toml (or config.local.toml), restart the server, then press Refresh checks.'));
        statusNode.textContent = 'Local server running';
        statusNode.className = 'pf-server success';
        document.getElementById('checked-at').textContent = `Checked ${new Date(snapshot.checked_at).toLocaleTimeString()}`;
    } catch (error) {
        statusNode.className = 'pf-server error';
        statusNode.textContent = 'Server checks failed';
        agentsNode.replaceChildren(emptyState(`Checks failed. ${error.message}`, 'Press Refresh checks to try again.'));
    } finally { refreshButton.disabled = false; }
}
refreshButton.addEventListener('click', refreshChecks);
refreshChecks();
