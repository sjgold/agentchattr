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
async function refreshChecks() {
    refreshButton.disabled = true;
    statusNode.className = '';
    statusNode.textContent = 'Checking connection…';
    try {
        const response = await fetch('/api/preflight', {
            headers: {'x-session-token': window.__SESSION_TOKEN__},
            cache: 'no-store', signal: AbortSignal.timeout(10000),
        });
        if (!response.ok) throw new Error(`Server returned ${response.status}. Reload this page to refresh your session.`);
        const snapshot = await response.json();
        agentsNode.replaceChildren();
        for (const agent of snapshot.agents) {
            const card = document.createElement('article');
            const title = document.createElement('h3');
            title.textContent = agent.label || agent.name;
            const list = document.createElement('dl');
            detail(list, 'Executable', agent.client_type === 'api' ? 'API agent · no executable required' :
                (agent.executable_found ? agent.executable : 'Not found on PATH'));
            detail(list, 'Version', agent.version || 'Unknown');
            detail(list, 'Startup', agent.startup_checked ? 'Checked' : 'Not checked');
            detail(list, 'Authentication', agent.authentication);
            detail(list, 'Adapter connection', agent.adapter_connected);
            detail(list, 'Ready', agent.ready ? 'Yes' : 'Not verified');
            card.append(title, list);
            agentsNode.append(card);
        }
        if (!snapshot.agents.length) agentsNode.textContent = 'No agents configured.';
        statusNode.textContent = 'Local web server available';
        statusNode.className = 'success';
        document.getElementById('checked-at').textContent = `Last checked: ${new Date(snapshot.checked_at).toLocaleString()}`;
    } catch (error) {
        statusNode.className = 'error';
        statusNode.textContent = `Checks failed. ${error.message} Use Refresh checks to retry.`;
        agentsNode.replaceChildren();
    } finally { refreshButton.disabled = false; }
}
refreshButton.addEventListener('click', refreshChecks);
refreshChecks();
