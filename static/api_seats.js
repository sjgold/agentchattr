'use strict';
(() => {
    const status = document.getElementById('api-seat-status');
    const packageSelect = document.getElementById('api-package-select');
    const packageId = document.getElementById('api-package-id');
    const packageName = document.getElementById('api-package-name');
    const editors = document.getElementById('api-seat-editors');
    const runtime = document.getElementById('api-seat-runtime');
    const form = document.getElementById('api-package-form');
    let snapshot = {providers: [], packages: [], runtime: {}};
    let pollsLeft = 0;
    let timer;
    const pending = new Set();

    function message(text, error = false) {
        status.textContent = text;
        status.className = error ? 'error' : '';
    }
    async function request(path, body) {
        const options = {headers: {'x-session-token': window.__SESSION_TOKEN__},
            cache: 'no-store', signal: AbortSignal.timeout(10000)};
        if (body !== undefined) {
            options.method = 'POST';
            options.headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(body);
        }
        const response = await fetch(path, options);
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `Server returned ${response.status}`);
        return data;
    }
    function option(select, value, name) {
        const node = document.createElement('option');
        node.value = value;
        node.textContent = name;
        select.append(node);
    }
    function field(parent, name, control) {
        const label = document.createElement('label');
        label.append(document.createTextNode(name), control);
        parent.append(label);
        return control;
    }
    function input(parent, label, value, required = false) {
        const node = document.createElement('input');
        node.value = value || '';
        node.required = required;
        node.maxLength = 256;
        return field(parent, label, node);
    }
    function button(parent, label, action) {
        const node = document.createElement('button');
        node.type = 'button';
        node.textContent = label;
        node.addEventListener('click', action);
        parent.append(node);
        return node;
    }
    function addEditor(seat = {}) {
        const editor = document.createElement('fieldset');
        const legend = document.createElement('legend');
        legend.textContent = 'API seat';
        const fields = document.createElement('div');
        fields.className = 'seat-fields';
        const id = input(fields, 'Seat ID', seat.id, true);
        id.pattern = '[a-z][a-z0-9-]{0,47}';
        id.maxLength = 48;
        const name = input(fields, 'Display name', seat.name, true);
        name.maxLength = 100;
        const provider = field(fields, 'Provider template', document.createElement('select'));
        provider.required = true;
        option(provider, '', 'Select a provider');
        for (const item of snapshot.providers) {
            if (!item.error) option(provider, item.id, item.name);
        }
        provider.value = seat.provider || '';
        const model = input(fields, 'Model ID · blank uses Provider default; manual IDs unverified', seat.model);
        const suggestions = document.createElement('datalist');
        suggestions.id = `models-${crypto.randomUUID()}`;
        model.setAttribute('list', suggestions.id);
        fields.append(suggestions);
        const reasoning = field(fields, 'Reasoning effort', document.createElement('select'));
        const secret = input(fields, 'Credential environment-variable reference · never the key itself', seat.secret_ref);
        secret.maxLength = 128;
        secret.pattern = '[A-Za-z_][A-Za-z0-9_]{0,127}';
        function capabilities(reset) {
            const selected = snapshot.providers.find(p => p.id === provider.value);
            suggestions.replaceChildren();
            const models = new Set([...(selected?.models || []), selected?.default_model].filter(Boolean));
            for (const modelId of models) option(suggestions, modelId, modelId);
            reasoning.replaceChildren();
            option(reasoning, '', 'Provider default · no reasoning override');
            for (const effort of selected?.reasoning_efforts || []) option(reasoning, effort, effort);
            if (!reset && seat.reasoning) reasoning.value = seat.reasoning;
            if (reset) secret.value = selected?.secret_ref || '';
        }
        provider.addEventListener('change', () => capabilities(true));
        capabilities(false);
        editor.append(legend, fields);
        button(editor, 'Remove from package', () => editor.remove());
        editor.readSeat = () => ({id: id.value, name: name.value, provider: provider.value,
            model: model.value || null, reasoning: reasoning.value || null,
            secret_ref: secret.value, adapter: 'openai-compatible', launch_profile: 'standard'});
        editors.append(editor);
    }
    function editPackage(id) {
        const selected = snapshot.packages.find(p => p.id === id);
        packageId.value = selected?.id || '';
        packageName.value = selected?.name || '';
        editors.replaceChildren();
        if (selected) selected.seats.forEach(addEditor);
        else addEditor();
    }
    function renderRuntime() {
        runtime.replaceChildren();
        for (const pkg of snapshot.packages) for (const seat of pkg.seats) {
            const key = `${pkg.id}/${seat.id}`;
            const state = snapshot.runtime[key] || {state: 'not_started'};
            const card = document.createElement('article');
            const title = document.createElement('h3');
            title.textContent = `${pkg.name} · ${seat.name}`;
            const list = document.createElement('dl');
            detail(list, 'State', state.state.replaceAll('_', ' '));
            detail(list, 'Chat name', state.name ? `@${state.name}` : 'Not connected');
            detail(list, 'Saved next-launch model', seat.model || 'Provider default');
            detail(list, 'Running requested model', state.attempt ? (state.requested_model || 'Provider default') : 'Not launched');
            detail(list, 'Provider-confirmed model · last successful response', state.confirmed_model || 'Unknown');
            detail(list, 'Provider authentication', state.authentication || 'unknown');
            detail(list, 'Chat adapter', state.adapter_connected ? 'Connected' : 'Not connected');
            detail(list, 'Last adapter check', state.last_adapter_check ? new Date(state.last_adapter_check * 1000).toLocaleString() : 'Not checked');
            detail(list, 'Readiness', state.state === 'ready' ? 'Chat dispatch ready; provider verified only after a successful response' : 'Not ready');
            if (state.error) detail(list, 'Action needed', state.error);
            card.append(title, list);
            const actions = document.createElement('div');
            actions.className = 'actions';
            for (const [label, action, body] of [['Launch / reuse', 'launch', {}],
                ['Restart / retry this seat', 'launch', {restart: true}], ['Stop this seat', 'stop', {}]]) {
                const control = button(actions, label, async () => {
                    if (pending.has(key)) return;
                    pending.add(key);
                    control.disabled = true;
                    try {
                        const path = `/api/preflight/seats/${encodeURIComponent(pkg.id)}/${encodeURIComponent(seat.id)}/${action}`;
                        await request(path, body);
                        message('Seat action recorded. No provider verification request was sent.');
                        pollsLeft = 20;
                        await refresh(false);
                    } catch (error) { message(error.message, true); }
                    finally { pending.delete(key); control.disabled = false; }
                });
                control.disabled = pending.has(key);
            }
            card.append(actions);
            runtime.append(card);
        }
    }
    async function refresh(packages = true) {
        clearTimeout(timer);
        try {
            snapshot = await request('/api/preflight/seats');
            if (packages) {
                const selected = packageSelect.value;
                packageSelect.replaceChildren();
                option(packageSelect, '', 'New package');
                snapshot.packages.forEach(p => option(packageSelect, p.id, p.name));
                packageSelect.value = selected;
            }
            renderRuntime();
            if (!editors.children.length) addEditor();
            if (!snapshot.providers.some(p => !p.error)) message('No usable API provider templates. Configure an API agent endpoint first.', true);
            if (pollsLeft-- > 0) timer = setTimeout(() => refresh(false), 1000);
        } catch (error) { message(`API seats unavailable. ${error.message}`, true); }
    }
    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (!form.reportValidity()) return;
        const packageData = {id: packageId.value, name: packageName.value,
            seats: [...editors.children].map(editor => editor.readSeat())};
        try {
            await request('/api/preflight/packages', packageData);
            message('Package saved. Running seats keep their settings until explicitly restarted.');
            await refresh();
            packageSelect.value = packageData.id;
        } catch (error) { message(error.message, true); }
    });
    packageSelect.addEventListener('change', () => editPackage(packageSelect.value));
    document.getElementById('api-package-new').addEventListener('click', () => { packageSelect.value = ''; editPackage(''); });
    document.getElementById('api-seat-add').addEventListener('click', () => addEditor());
    document.getElementById('refresh').addEventListener('click', () => refresh());
    refresh();
})();
