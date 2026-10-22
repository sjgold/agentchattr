'use strict';
(() => {
    const status = document.getElementById('api-seat-status');
    const packageSelect = document.getElementById('api-package-select');
    const packageId = document.getElementById('api-package-id');
    const packageName = document.getElementById('api-package-name');
    const editors = document.getElementById('api-seat-editors');
    const runtime = document.getElementById('api-seat-runtime');
    const form = document.getElementById('api-package-form');
    const teamLaunch = document.getElementById('team-launch');
    const teamChat = document.getElementById('team-chat');
    const teamStatus = document.getElementById('team-launch-status');
    const reloadTeam = document.getElementById('api-package-reload');
    let snapshot = {providers: [], packages: [], runtime: {}};
    let draftDirty = false;
    let selectionDirty = false;
    let teamPending = false;
    let rememberedLoaded = false;
    let checksAvailable = false;
    let loadedRevision = null;
    const omitted = new Set();
    let pollsLeft = 0;
    let timer;
    const pending = new Set();

    function remember(id) {
        try {
            if (id) localStorage.setItem('agentchattr.lastPackage', id);
            else localStorage.removeItem('agentchattr.lastPackage');
        } catch (_) { /* Browser storage can be disabled; server packages remain available. */ }
    }
    function renderTeam() {
        const id = packageSelect.value;
        const saved = snapshot.packages.find(p => p.id === id);
        const state = snapshot.package_launches?.[id];
        const stale = !!saved && loadedRevision !== snapshot.package_revisions?.[id];
        const exclusionsChanged = !!state?.selection_id && (omitted.size !== state.omitted_seats.length ||
            state.omitted_seats.some(seat => !omitted.has(seat)));
        teamLaunch.disabled = !checksAvailable || !saved || draftDirty || stale || teamPending;
        teamChat.disabled = !checksAvailable || !saved || draftDirty || stale || selectionDirty || exclusionsChanged || teamPending || !state?.ready;
        reloadTeam.disabled = !saved || teamPending;
        if (!saved) teamStatus.textContent = 'Save or select your team to launch it.';
        else if (stale) teamStatus.textContent = 'This saved team changed. Reload saved team to review its current settings.';
        else if (draftDirty) teamStatus.textContent = 'Save your edits before launching or continuing to chat.';
        else if (selectionDirty || exclusionsChanged) teamStatus.textContent = 'Launch the team to apply these seat choices.';
        else if (state?.error) teamStatus.textContent = state.error;
        else if (!state?.selection_id) teamStatus.textContent = 'Your team is saved. Launch it when you are ready.';
        else {
            const seats = Object.values(state.seats);
            const count = seats.filter(seat => seat.state === 'ready').length;
            teamStatus.textContent = state.ready ? `${count} of ${seats.length} selected seats ready for chat. Provider/client authentication remains separate.` :
                `${count} of ${seats.length} selected seats ready. Retry, explicitly restart, or leave out a seat for this launch.`;
        }
    }
    function markDraft() { draftDirty = true; renderTeam(); }

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
        legend.textContent = 'Agent seat';
        const fields = document.createElement('div');
        fields.className = 'seat-fields';
        const id = input(fields, 'Seat ID', seat.id, true);
        id.pattern = '[a-z][a-z0-9-]{0,47}';
        id.maxLength = 48;
        const name = input(fields, 'Display name', seat.name, true);
        name.maxLength = 100;
        const adapter = field(fields, 'Client adapter', document.createElement('select'));
        option(adapter, 'openai-compatible', 'Direct API');
        option(adapter, 'cli', 'Interactive CLI');
        adapter.value = seat.adapter || 'openai-compatible';
        const provider = field(fields, 'Configured template', document.createElement('select'));
        provider.required = true;
        function templates() {
            provider.replaceChildren();
            option(provider, '', 'Select a configured template');
            for (const item of snapshot.providers) {
                if (!item.error && item.adapter === adapter.value) option(provider, item.id, item.name);
            }
        }
        templates();
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
        const effects = document.createElement('p');
        fields.append(effects);
        function capabilities(reset) {
            const selected = snapshot.providers.find(p => p.id === provider.value);
            suggestions.replaceChildren();
            const models = new Set([...(selected?.models || []), selected?.default_model].filter(Boolean));
            for (const modelId of models) option(suggestions, modelId, modelId);
            reasoning.replaceChildren();
            option(reasoning, '', 'Provider default · no reasoning override');
            for (const effort of selected?.reasoning_efforts || []) option(reasoning, effort, effort);
            if (!reset && seat.reasoning) reasoning.value = seat.reasoning;
            const cli = adapter.value === 'cli';
            secret.disabled = cli;
            if (reset || cli) secret.value = selected?.secret_ref || '';
            model.disabled = cli && !selected?.supports_model;
            if (model.disabled || reset) model.value = '';
            effects.textContent = cli ? (selected?.configuration_effects || 'Select a CLI template to see its launch configuration changes.') : '';
        }
        adapter.addEventListener('change', () => { templates(); capabilities(true); });
        provider.addEventListener('change', () => capabilities(true));
        capabilities(false);
        editor.append(legend, fields);
        button(editor, 'Remove from package', () => { editor.remove(); markDraft(); });
        editor.readSeat = () => ({id: id.value, name: name.value, provider: provider.value,
            model: model.value || null, reasoning: reasoning.value || null,
            secret_ref: secret.value, adapter: adapter.value, launch_profile: 'standard'});
        editors.append(editor);
    }
    function editPackage(id) {
        const selected = snapshot.packages.find(p => p.id === id);
        packageSelect.value = selected?.id || '';
        loadedRevision = snapshot.package_revisions?.[id] || null;
        draftDirty = false;
        selectionDirty = false;
        omitted.clear();
        (snapshot.package_launches?.[id]?.omitted_seats || []).forEach(seat => omitted.add(seat));
        remember(selected?.id || '');
        packageId.value = selected?.id || '';
        packageName.value = selected?.name || '';
        editors.replaceChildren();
        if (selected) selected.seats.forEach(addEditor);
        else addEditor();
        renderRuntime();
        renderTeam();
    }
    function renderRuntime() {
        runtime.replaceChildren();
        for (const pkg of snapshot.packages.filter(p => p.id === packageSelect.value)) for (const seat of pkg.seats) {
            const key = `${pkg.id}/${seat.id}`;
            const state = snapshot.package_launches?.[pkg.id]?.seats[seat.id] || snapshot.runtime[key] || {state: 'not_started'};
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
            if (seat.adapter === 'cli') {
                detail(list, 'Executable', state.executable || 'Not checked at launch');
                detail(list, 'Client started', state.startup_checked ? 'Yes' : 'Not checked');
                detail(list, 'Client version', state.version || 'Unknown');
                detail(list, 'Child exit code', state.child_exit_code ?? (state.state === 'stopped' ? 'Unknown after stop' : 'Still running or not started'));
            }
            detail(list, 'Readiness', state.state === 'ready' ? (seat.adapter === 'cli' ?
                'Mention injection ready; CLI login, MCP tool use and model confirmation remain unverified' :
                'Chat dispatch ready; provider verified only after a successful response') : 'Not ready');
            if (state.error) detail(list, 'Action needed', state.error);
            card.append(title, list);
            const exclusion = document.createElement('label');
            exclusion.className = 'seat-omission';
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.checked = omitted.has(seat.id);
            checkbox.disabled = teamPending;
            checkbox.addEventListener('change', () => {
                if (checkbox.checked) omitted.add(seat.id);
                else omitted.delete(seat.id);
                selectionDirty = true;
                renderTeam();
            });
            exclusion.append(checkbox, document.createTextNode('Leave out of this launch'));
            card.append(exclusion);
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
            checksAvailable = true;
            if (packages) {
                const selected = packageSelect.value;
                packageSelect.replaceChildren();
                option(packageSelect, '', 'New package');
                snapshot.packages.forEach(p => option(packageSelect, p.id, p.name));
                packageSelect.value = selected;
            }
            if (!rememberedLoaded) {
                rememberedLoaded = true;
                let remembered;
                try { remembered = localStorage.getItem('agentchattr.lastPackage'); } catch (_) { remembered = null; }
                if (snapshot.packages.some(pkg => pkg.id === remembered)) editPackage(remembered);
            }
            renderRuntime();
            renderTeam();
            if (!editors.children.length) addEditor();
            if (!snapshot.providers.some(p => !p.error)) message('No usable agent templates. Configure an API provider or CLI client first.', true);
            if (pollsLeft-- > 0) timer = setTimeout(() => refresh(false), 1000);
        } catch (error) {
            checksAvailable = false;
            renderTeam();
            message(`Agent seats unavailable. ${error.message}`, true);
        }
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
            editPackage(packageData.id);
        } catch (error) { message(error.message, true); }
    });
    packageSelect.addEventListener('change', () => editPackage(packageSelect.value));
    document.getElementById('api-package-new').addEventListener('click', () => { packageSelect.value = ''; editPackage(''); });
    document.getElementById('api-seat-add').addEventListener('click', () => { addEditor(); markDraft(); });
    form.addEventListener('input', markDraft);
    form.addEventListener('change', markDraft);
    reloadTeam.addEventListener('click', async () => {
        const id = packageSelect.value;
        await refresh(false);
        editPackage(id);
    });
    teamLaunch.addEventListener('click', async () => {
        if (teamLaunch.disabled) return;
        const id = packageSelect.value;
        teamPending = true;
        renderTeam();
        try {
            const result = await request(`/api/preflight/packages/${encodeURIComponent(id)}/launch`, {
                revision: loadedRevision, omitted_seats: [...omitted]});
            snapshot.package_launches[id] = result;
            selectionDirty = false;
            message('Team launch recorded. Your saved package has not changed.');
        } catch (error) { message(error.message, true); }
        finally {
            teamPending = false;
            pollsLeft = 30;
            await refresh(false);
        }
    });
    teamChat.addEventListener('click', async () => {
        if (teamChat.disabled) return;
        const id = packageSelect.value;
        const state = snapshot.package_launches[id];
        teamPending = true;
        renderTeam();
        try {
            const result = await request(`/api/preflight/packages/${encodeURIComponent(id)}/chat`, {selection_id: state.selection_id});
            window.location.assign(result.url);
        } catch (error) { message(error.message, true); }
        finally { teamPending = false; await refresh(false); }
    });
    document.getElementById('refresh').addEventListener('click', () => refresh());
    refresh();
})();
