'use strict';
(() => {
    const status = document.getElementById('api-seat-status');
    const packageSelect = document.getElementById('api-package-select');
    const packageId = document.getElementById('api-package-id');
    const packageName = document.getElementById('api-package-name');
    const editors = document.getElementById('api-seat-editors');
    const form = document.getElementById('api-package-form');
    const teamGo = document.getElementById('team-go');
    const teamLaunch = document.getElementById('team-launch');
    const teamChat = document.getElementById('team-chat');
    const teamStatus = document.getElementById('team-launch-status');
    const reloadTeam = document.getElementById('api-package-reload');
    // Launch-and-go polls package status once a second; past this it stops and says so.
    const GO_DEADLINE_MS = 90000;
    let snapshot = {providers: [], packages: [], runtime: {}};
    let draftDirty = false;
    let selectionDirty = false;
    let teamPending = false;
    let goProgress = null;
    let rememberedLoaded = false;
    let checksAvailable = false;
    let loadedRevision = null;
    let packageIdTouched = false;
    const omitted = new Set();
    const modelRefreshPending = new Set();
    const modelRefreshErrors = new Map();
    let modelCatalogRequestVersion = 0;
    let modelCatalogRefreshStarted = false;
    let modelCatalogPollTimer = null;
    let modelCatalogPolls = 0;
    let pollsLeft = 0;
    let timer;
    const pending = new Set();
    const STATE_LABELS = {not_started: 'Not launched', starting: 'Starting…', ready: 'Ready for chat',
        action_required: 'Needs attention', blocked: 'Blocked', failed: 'Failed', stopped: 'Stopped', exited: 'Not running (launch again)', unverified: 'Unverified'};
    const PROBLEM_STATES = ['action_required', 'blocked', 'failed'];

    function remember(id) {
        try {
            if (id) localStorage.setItem('agentchattr.lastPackage', id);
            else localStorage.removeItem('agentchattr.lastPackage');
        } catch (_) { /* Browser storage can be disabled; server packages remain available. */ }
    }
    function slug(text) {
        const value = text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^[^a-z]+/, '').replace(/-+$/, '');
        return value.slice(0, 48).replace(/-+$/, '');
    }
    function savedPackage() { return snapshot.packages.find(p => p.id === packageSelect.value); }
    function launchState() { return snapshot.package_launches?.[packageSelect.value]; }
    function seatEditors() { return [...editors.children]; }
    function includedCount() {
        const saved = savedPackage();
        return saved ? saved.seats.filter(seat => !omitted.has(seat.id)).length : seatEditors().length;
    }
    function renderTeam() {
        const saved = savedPackage();
        const state = launchState();
        const stale = !!saved && loadedRevision !== snapshot.package_revisions?.[saved.id];
        const exclusionsChanged = !!state?.selection_id && (omitted.size !== state.omitted_seats.length ||
            state.omitted_seats.some(seat => !omitted.has(seat)));
        const hasSeats = seatEditors().length > 0;
        teamGo.disabled = !checksAvailable || stale || teamPending || !hasSeats || (!saved && !draftDirty) || includedCount() < 1;
        teamLaunch.disabled = !checksAvailable || !saved || draftDirty || stale || teamPending;
        teamChat.disabled = !checksAvailable || !saved || draftDirty || stale || selectionDirty || exclusionsChanged || teamPending || !state?.ready;
        reloadTeam.disabled = !saved || teamPending;
        teamGo.textContent = teamPending && goProgress ? 'Launching…' : 'Launch team and open chat';
        let text;
        let tone = '';
        if (goProgress) text = goProgress;
        else if (!checksAvailable) { text = 'Team controls are unavailable until the server answers. Press Refresh checks.'; tone = 'error'; }
        else if (!saved && !hasSeats) text = 'Add a seat to build your team.';
        else if (!saved) text = 'Name your team and its seats. Launching saves it first.';
        else if (stale) { text = 'This saved team changed elsewhere. Press Reload saved team to review its current settings.'; tone = 'error'; }
        else if (includedCount() < 1) { text = 'Tick Use on at least one seat.'; tone = 'error'; }
        else if (draftDirty) text = 'You have unsaved edits. Launching saves them first.';
        else if (selectionDirty || exclusionsChanged) text = 'Seat choices changed. Launch the team to apply them.';
        else if (state?.error) { text = state.error; tone = 'error'; }
        else if (!state?.selection_id) text = 'Your team is saved. Launch it when you are ready.';
        else {
            const seats = Object.values(state.seats);
            const count = seats.filter(seat => seat.state === 'ready').length;
            text = state.ready ? `${count} of ${seats.length} seats ready for chat. Provider/client sign-in is checked separately.` :
                `${count} of ${seats.length} seats ready. Retry or leave out the seat that needs attention.`;
            tone = state.ready ? 'success' : '';
        }
        teamStatus.textContent = text;
        teamStatus.className = tone;
    }
    function markDraft(event) {
        if (event?.target?.classList?.contains('pf-runtime-control')) return;
        draftDirty = true;
        renderTeam();
    }

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
        return node;
    }
    function catalogDate(value) {
        if (!value) return '';
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? '' : date.toLocaleString();
    }
    function catalogStatus(provider) {
        const catalog = provider?.model_catalog;
        const key = provider?.id || '';
        const refreshing = modelRefreshPending.has('*') || modelRefreshPending.has(key) || catalog?.refreshing;
        const source = catalog?.source || 'client model catalog';
        const latest = catalogDate(catalog?.catalog_fetched_at || catalog?.checked_at);
        const lastGood = catalog?.authoritative ? catalogDate(catalog?.catalog_fetched_at) : '';
        const error = modelRefreshErrors.get(key) || modelRefreshErrors.get('*') || catalog?.error;
        const configuredFallback = catalog?.dynamic && !catalog?.models?.length && catalog?.configured_models?.length;
        const fallbackNote = configuredFallback ? ' Configured model choices are shown as fallback; discovery is unavailable.' : '';
        if (refreshing && error) return (lastGood ? `Checking ${source}. Last refresh failed: ${error}. Last complete catalog: ${lastGood}.` : `Checking ${source}. Last refresh failed: ${error}. No complete catalog yet.`) + fallbackNote;
        if (refreshing) return (latest ? `Checking ${source}. Last catalog: ${latest}.` : `Checking ${source}…`) +
            (configuredFallback ? ' Configured model choices remain available as fallback.' : '');
        if (error) return (lastGood ? `${source} refresh failed: ${error}. Last complete catalog: ${lastGood}.` : `${source} refresh failed: ${error}. No complete catalog yet.`) + fallbackNote;
        if (catalog?.complete) return `${source} · refreshed ${latest || 'time unavailable'}.`;
        if (catalog?.models?.length) return `Partial ${source}${latest ? ` · checked ${latest}` : ''}.`;
        if (configuredFallback) return `${source} has no successful catalog. Configured model choices are shown as fallback.`;
        if (catalog?.dynamic) return `No model catalog yet. ${latest ? `Last check: ${latest}. ` : ''}Provider default remains available.`;
        return '';
    }
    function updateModelCatalogProviders(providers) {
        if (!Array.isArray(providers)) return;
        snapshot = {...snapshot, providers};
        for (const editor of seatEditors()) editor.refreshModelCatalog?.();
    }
    function scheduleModelCatalogPoll() {
        if (modelCatalogPollTimer || modelCatalogPolls >= 120) return;
        modelCatalogPollTimer = setTimeout(async () => {
            modelCatalogPollTimer = null;
            modelCatalogPolls++;
            await refresh(false);
        }, 1000);
    }
    async function refreshModelCatalog(providerId) {
        const key = providerId || '*';
        if (modelRefreshPending.has('*') || modelRefreshPending.has(key)) return;
        const requestVersion = ++modelCatalogRequestVersion;
        modelRefreshPending.add(key);
        if (providerId) modelRefreshErrors.delete(providerId);
        for (const editor of seatEditors()) editor.refreshModelCatalog?.();
        try {
            const result = await request('/api/preflight/models/refresh', providerId ? {provider: providerId} : {});
            if (Array.isArray(result.providers)) {
                if (requestVersion === modelCatalogRequestVersion) {
                    modelRefreshErrors.delete('*');
                    result.providers.forEach(item => modelRefreshErrors.delete(item.id));
                    updateModelCatalogProviders(result.providers);
                    if (result.providers.some(item => item.model_catalog?.refreshing)) scheduleModelCatalogPoll();
                    else modelCatalogPolls = 0;
                }
            }
        } catch (error) {
            modelRefreshErrors.set(key, error.message);
            for (const editor of seatEditors()) editor.refreshModelCatalog?.();
        } finally {
            modelRefreshPending.delete(key);
            for (const editor of seatEditors()) editor.refreshModelCatalog?.();
        }
    }
    function field(parent, name, control, hint) {
        const label = document.createElement('label');
        label.append(document.createTextNode(name), control);
        if (hint) {
            const small = document.createElement('small');
            small.textContent = hint;
            label.append(small);
        }
        parent.append(label);
        return control;
    }
    function input(parent, label, value, required = false, hint) {
        const node = document.createElement('input');
        node.value = value || '';
        node.required = required;
        node.maxLength = 256;
        return field(parent, label, node, hint);
    }
    function button(parent, label, action, className) {
        const node = document.createElement('button');
        node.type = 'button';
        node.textContent = label;
        if (className) node.className = className;
        node.addEventListener('click', action);
        parent.append(node);
        return node;
    }
    function element(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }
    function addEditor(seat = {}, savedSeat = false) {
        const editor = element('fieldset', 'pf-seat');
        editor.dataset.state = 'not_started';
        if (savedSeat) editor.dataset.savedId = seat.id;
        const legend = element('legend', 'pf-visually-hidden', 'Agent seat');
        const head = element('div', 'pf-seat-head');
        const include = element('label', 'pf-include seat-omission');
        const checkbox = element('input', 'pf-runtime-control');
        checkbox.type = 'checkbox';
        checkbox.checked = !(savedSeat && omitted.has(seat.id));
        checkbox.disabled = !savedSeat || teamPending;
        checkbox.title = savedSeat ? 'Untick to leave this seat out of this launch only' : 'Save the team to choose seats for a launch';
        checkbox.addEventListener('change', () => {
            if (checkbox.checked) omitted.delete(seat.id);
            else omitted.add(seat.id);
            selectionDirty = true;
            renderRuntime();
            renderTeam();
        });
        include.append(checkbox, document.createTextNode('Use'));
        const titleBox = element('div', 'pf-seat-title');
        const title = element('strong', null, seat.name || 'New seat');
        const summaryLine = element('span', 'pf-seat-summary');
        titleBox.append(title, summaryLine);
        const stateChip = element('span', 'pf-chip pf-chip--unknown pf-seat-state', savedSeat ? STATE_LABELS.not_started : 'Not saved yet');
        head.append(include, titleBox, stateChip);

        const problem = element('div', 'pf-seat-problem');
        problem.hidden = true;
        const problemText = element('p');
        const problemActions = element('div', 'actions');
        problem.append(problemText, problemActions);

        const config = element('details', 'pf-seat-config');
        config.open = !savedSeat;
        config.append(element('summary', null, 'Configure'));
        const fields = element('div', 'seat-fields');
        const name = input(fields, 'Display name', seat.name, true);
        name.maxLength = 100;
        name.placeholder = 'Reviewer';
        const id = input(fields, 'Seat ID', seat.id, true, 'stable; lowercase, digits, dashes');
        // '-' is escaped: browsers compile pattern with the v flag, where a bare '-' is invalid.
        id.pattern = '[a-z][a-z0-9\\-]{0,47}';
        id.maxLength = 48;
        id.placeholder = 'reviewer';
        let idTouched = !!seat.id;
        id.addEventListener('input', () => { idTouched = true; });
        name.addEventListener('input', () => {
            title.textContent = name.value || 'New seat';
            if (!idTouched && !savedSeat) id.value = slug(name.value);
        });
        const adapter = field(fields, 'Runs as', element('select'));
        option(adapter, 'openai-compatible', 'Direct API');
        option(adapter, 'cli', 'Interactive CLI');
        adapter.value = seat.adapter || 'openai-compatible';
        const provider = field(fields, 'Client configuration', element('select'),
            'Choose the launch client/provider preset. Choose the model separately below.');
        provider.required = true;
        function templates(desiredProvider = seat.provider || '') {
            provider.replaceChildren();
            const usable = snapshot.providers.filter(item => !item.error && item.adapter === adapter.value);
            option(provider, '', usable.length ? 'Choose a template' : 'No configured templates for this type');
            const primary = usable.filter(item => adapter.value !== 'cli' || item.supports_model);
            const defaultOnly = usable.filter(item => adapter.value === 'cli' && !item.supports_model);
            for (const item of primary) option(provider, item.id, item.name);
            if (defaultOnly.length) {
                const group = element('optgroup');
                group.label = 'Legacy/default-only clients';
                for (const item of defaultOnly) option(group, item.id, `${item.name} (native default only)`);
                provider.append(group);
            }
            if (desiredProvider && !usable.some(item => item.id === desiredProvider)) {
                const selectedProvider = snapshot.providers.find(item => item.id === desiredProvider);
                const saved = savedSeat && desiredProvider === seat.provider;
                option(provider, desiredProvider, `${selectedProvider?.name || desiredProvider} (${saved ? 'saved, unavailable' : 'unavailable'})`);
            }
            provider.value = desiredProvider;
        }
        templates();
        const model = field(fields, 'Model', element('select'), 'Choose a discovered model or Provider default.');
        const modelActions = element('div', 'actions');
        const refreshModelsButton = button(modelActions, 'Refresh models', () => refreshModelCatalog(provider.value));
        const modelStatus = element('p', 'pf-dim');
        modelStatus.setAttribute('role', 'status');
        const modelSelectionNote = element('p', 'pf-dim');
        fields.append(modelActions, modelStatus, modelSelectionNote);
        const reasoning = field(fields, 'Reasoning effort', element('select'), 'Choices depend on the selected model.');
        const secret = input(fields, 'Credential variable name', seat.secret_ref, false, 'environment variable NAME only, never the key');
        secret.maxLength = 128;
        secret.pattern = '[A-Za-z_][A-Za-z0-9_]{0,127}';
        secret.autocomplete = 'off';
        secret.spellcheck = false;
        const effects = element('p', 'pf-dim pf-effects');
        fields.append(effects);
        function summarize() {
            const template = snapshot.providers.find(p => p.id === provider.value);
            // Only CLI templates apply default_model; a blank API model is omitted (provider default).
            const cliDefault = adapter.value === 'cli' && template?.default_model;
            const parts = [adapter.value === 'cli' ? 'CLI' : 'API', template ? template.name : 'no template chosen',
                model.value ? `model ${model.value}` : cliDefault ? `default model ${cliDefault}` : 'provider default model'];
            if (reasoning.value) parts.push(`reasoning ${reasoning.value}`);
            if (adapter.value !== 'cli' && secret.value) parts.push(`key from ${secret.value}`);
            summaryLine.textContent = parts.join(' · ');
        }
        function capabilities(reset, preserveSelection = false, modelChanged = false) {
            const selected = snapshot.providers.find(p => p.id === provider.value);
            const catalog = selected?.model_catalog;
            const catalogModels = Array.isArray(catalog?.models) ? catalog.models : [];
            const modelEntries = new Map(catalogModels.filter(item => item && typeof item.id === 'string')
                .map(item => [item.id, item]));
            const models = new Set(catalogModels.filter(item => item?.available !== false).map(item => item.id));
            const configuredFallback = !!catalog?.dynamic && !catalogModels.length && Array.isArray(catalog.configured_models)
                ? catalog.configured_models : [];
            if (catalog?.dynamic && !catalogModels.length) {
                for (const modelId of configuredFallback) models.add(modelId);
            } else if (!catalog?.dynamic) {
                for (const modelId of Array.isArray(selected?.models) ? selected.models : []) models.add(modelId);
            }
            if (!catalog?.dynamic && typeof selected?.default_model === 'string' && selected.default_model) {
                models.add(selected.default_model);
            }
            const desiredModel = preserveSelection ? model.value : (seat.model || '');
            const desiredEffort = preserveSelection ? reasoning.value : (seat.reasoning || '');
            model.replaceChildren();
            option(model, '', 'Provider default');
            const baseLabels = [...models].map(modelId => configuredFallback.includes(modelId)
                ? `${modelId} (configured fallback)` : (modelEntries.get(modelId)?.name || modelId));
            const labelCounts = new Map();
            for (const label of baseLabels) labelCounts.set(label, (labelCounts.get(label) || 0) + 1);
            for (const modelId of models) {
                const entry = modelEntries.get(modelId);
                const baseLabel = configuredFallback.includes(modelId) ? `${modelId} (configured fallback)` : (entry?.name || modelId);
                const label = labelCounts.get(baseLabel) > 1 && !configuredFallback.includes(modelId)
                    ? `${baseLabel} (${modelId})` : baseLabel;
                const node = option(model, modelId, entry?.available === false ? `${label} (unavailable)` : label);
                if (entry?.available === false) node.disabled = true;
            }
            const catalogEntry = modelEntries.get(desiredModel);
            const dynamicMissing = !!desiredModel && catalog?.dynamic && !catalogEntry;
            if (!reset && desiredModel && !models.has(desiredModel)) {
                const authoritative = catalog?.retirement_authoritative === true && catalog?.complete === true;
                const unavailable = catalogEntry?.available === false || (dynamicMissing && authoritative);
                option(model, desiredModel, unavailable ? `${desiredModel} (unavailable)` : `${desiredModel} (saved, unverified)`);
            }
            reasoning.replaceChildren();
            option(reasoning, '', 'Provider default');
            let efforts = [];
            let reasoningKnown = false;
            const effortModel = desiredModel || selected?.default_model || '';
            const effortEntry = modelEntries.get(effortModel);
            if (effortEntry?.reasoning_known) {
                efforts = Array.isArray(effortEntry.reasoning_efforts) ? effortEntry.reasoning_efforts : [];
                reasoningKnown = true;
            } else if (!catalog?.dynamic) {
                efforts = Array.isArray(selected?.reasoning_efforts) ? selected.reasoning_efforts : [];
                reasoningKnown = efforts.length > 0;
            }
            for (const effort of efforts) option(reasoning, effort, effort);
            if (!reset && !modelChanged && desiredEffort && !efforts.includes(desiredEffort)) {
                const label = reasoningKnown ? `${desiredEffort} (unavailable for this model)` : `${desiredEffort} (saved, unverified)`;
                option(reasoning, desiredEffort, label);
            }
            reasoning.disabled = !efforts.length;
            reasoning.value = reset || (!modelChanged && !desiredEffort) || (modelChanged && !efforts.includes(desiredEffort))
                ? '' : desiredEffort;
            const cli = adapter.value === 'cli';
            secret.disabled = cli;
            secret.closest('label').hidden = cli;
            if (reset || cli) secret.value = selected?.secret_ref || '';
            model.disabled = cli && !selected?.supports_model;
            model.value = reset ? '' : desiredModel;
            effects.textContent = cli ? (selected?.configuration_effects || 'Choose a CLI template to see what launch changes.') : '';
            modelActions.hidden = selected?.model_catalog?.dynamic !== true || (cli && !selected?.supports_model);
            refreshModelsButton.disabled = !selected || modelRefreshPending.has('*') ||
                modelRefreshPending.has(selected.id) || !!selected.model_catalog?.refreshing;
            modelStatus.textContent = [catalogStatus(selected), selected?.model_catalog?.capability_note]
                .filter(Boolean).join(' ');
            modelSelectionNote.textContent = selected?.model_selection_note || '';
            modelSelectionNote.hidden = !modelSelectionNote.textContent;
            summarize();
        }
        adapter.addEventListener('change', () => { templates(''); capabilities(true); });
        provider.addEventListener('change', () => capabilities(true));
        model.addEventListener('change', () => capabilities(false, true, true));
        reasoning.addEventListener('change', summarize);
        secret.addEventListener('input', summarize);
        capabilities(false);
        editor.refreshModelCatalog = () => { templates(provider.value); capabilities(false, true); };
        const configActions = element('div', 'actions');
        button(configActions, 'Remove from team', () => { editor.remove(); markDraft(); }, 'pf-danger-quiet');
        config.append(fields, configActions);

        const statusDetails = element('details', 'pf-seat-status');
        statusDetails.hidden = !savedSeat;
        statusDetails.append(element('summary', null, 'Status details'));
        const statusList = element('dl');
        const statusActions = element('div', 'actions');
        statusDetails.append(statusList, statusActions);

        // Both toggles share one row while closed; an open one takes the full width (CSS).
        const toggles = element('div', 'pf-seat-toggles');
        toggles.append(config, statusDetails);
        editor.append(legend, head, problem, toggles);
        editor.readSeat = () => ({id: id.value, name: name.value, provider: provider.value,
            model: model.value || null, reasoning: reasoning.value || null,
            secret_ref: secret.value, adapter: adapter.value, launch_profile: 'standard'});
        editor.runtime = {checkbox, stateChip, problem, problemText, problemActions, statusList, statusActions, statusDetails, config};
        editors.append(editor);
        return editor;
    }
    function editPackage(id, keepOmitted) {
        const selected = snapshot.packages.find(p => p.id === id);
        packageSelect.value = selected?.id || '';
        loadedRevision = snapshot.package_revisions?.[id] || null;
        draftDirty = false;
        selectionDirty = false;
        packageIdTouched = !!selected;
        omitted.clear();
        (snapshot.package_launches?.[id]?.omitted_seats || []).forEach(seat => omitted.add(seat));
        if (keepOmitted && selected) {
            const before = [...omitted].sort().join();
            omitted.clear();
            keepOmitted.forEach(seat => { if (selected.seats.some(item => item.id === seat)) omitted.add(seat); });
            selectionDirty = before !== [...omitted].sort().join();
        }
        remember(selected?.id || '');
        packageId.value = selected?.id || '';
        packageName.value = selected?.name || '';
        editors.replaceChildren();
        if (selected) selected.seats.forEach(seat => addEditor(seat, true));
        else addEditor();
        renderRuntime();
        renderTeam();
    }
    async function seatAction(pkgId, seatId, action, body, label) {
        const key = `${pkgId}/${seatId}`;
        if (pending.has(key)) return false;
        pending.add(key);
        renderRuntime();
        try {
            await request(`/api/preflight/seats/${encodeURIComponent(pkgId)}/${encodeURIComponent(seatId)}/${action}`, body);
            message(`${label} recorded. No provider verification request was sent.`);
            pollsLeft = 20;
            return true;
        } catch (error) { message(error.message, true); return false; }
        finally { pending.delete(key); await refresh(false); }
    }
    function renderRuntime() {
        const pkg = savedPackage();
        const launches = snapshot.package_launches?.[pkg?.id];
        for (const editor of seatEditors()) {
            const r = editor.runtime;
            const seat = pkg?.seats.find(item => item.id === editor.dataset.savedId);
            if (!seat) continue;
            const key = `${pkg.id}/${seat.id}`;
            const left = omitted.has(seat.id);
            const state = launches?.seats?.[seat.id] || snapshot.runtime[key] || {state: 'not_started'};
            const busy = pending.has(key) || teamPending;
            r.checkbox.checked = !left;
            r.checkbox.disabled = busy;
            editor.dataset.state = left ? 'omitted' : state.state;
            editor.classList.toggle('pf-seat--omitted', left);
            r.stateChip.textContent = left ? 'Left out' : (STATE_LABELS[state.state] || state.state.replaceAll('_', ' '));
            r.stateChip.className = `pf-chip pf-seat-state pf-chip--${left ? 'neutral' :
                state.state === 'ready' ? 'good' : PROBLEM_STATES.includes(state.state) ? 'bad' :
                state.state === 'starting' ? 'busy' : 'unknown'}`;

            r.statusList.replaceChildren();
            const list = r.statusList;
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

            r.statusActions.replaceChildren();
            for (const [label, action, body] of [['Launch / reuse', 'launch', {}],
                ['Restart / retry this seat', 'launch', {restart: true}], ['Stop this seat', 'stop', {}]]) {
                button(r.statusActions, label, () => seatAction(pkg.id, seat.id, action, body, label)).disabled = busy;
            }

            const failed = !left && !!state.error && !goProgress;
            r.problem.hidden = !failed;
            r.problemActions.replaceChildren();
            if (failed) {
                r.problemText.textContent = state.error;
                button(r.problemActions, 'Retry this seat and continue', async () => {
                    if (await seatAction(pkg.id, seat.id, 'launch', {restart: true}, 'Seat retry')) go();
                }, 'pf-primary-quiet').disabled = busy;
                button(r.problemActions, 'Leave it out and continue', () => {
                    omitted.add(seat.id);
                    selectionDirty = true;
                    go();
                }).disabled = busy;
            }
        }
    }
    async function refresh(packages = true) {
        clearTimeout(timer);
        try {
            const catalogVersion = modelCatalogRequestVersion;
            const refreshed = await request('/api/preflight/seats');
            snapshot = catalogVersion === modelCatalogRequestVersion ? refreshed : {...refreshed, providers: snapshot.providers};
            checksAvailable = true;
            if (packages) {
                const selected = packageSelect.value;
                packageSelect.replaceChildren();
                option(packageSelect, '', snapshot.packages.length ? 'New team' : 'No saved teams yet');
                snapshot.packages.forEach(p => option(packageSelect, p.id, p.name));
                packageSelect.value = selected;
            }
            if (!rememberedLoaded) {
                rememberedLoaded = true;
                let remembered;
                try { remembered = localStorage.getItem('agentchattr.lastPackage'); } catch (_) { remembered = null; }
                if (!snapshot.packages.some(pkg => pkg.id === remembered) && snapshot.packages.length === 1) remembered = snapshot.packages[0].id;
                if (snapshot.packages.some(pkg => pkg.id === remembered)) {
                    editPackage(remembered);
                    // Returning with a saved team: fold the agent list so the team comes first.
                    const agentsDetails = document.getElementById('agents-details');
                    if (agentsDetails) agentsDetails.open = false;
                }
            }
            if (!editors.children.length) addEditor();
            for (const editor of seatEditors()) editor.refreshModelCatalog?.();
            renderRuntime();
            renderTeam();
            if (!snapshot.providers.some(p => !p.error)) message('No usable agent templates yet. Configure an API provider or CLI client in config.toml, then refresh.', true);
            if (!modelCatalogRefreshStarted) {
                modelCatalogRefreshStarted = true;
                if (snapshot.providers.some(item => item.model_catalog?.dynamic)) {
                    if (snapshot.providers.some(item => item.model_catalog?.refreshing)) scheduleModelCatalogPoll();
                    else void refreshModelCatalog();
                }
            } else if (snapshot.providers.some(item => item.model_catalog?.refreshing)) {
                scheduleModelCatalogPoll();
            } else {
                modelCatalogPolls = 0;
            }
            if (pollsLeft-- > 0) timer = setTimeout(() => refresh(false), 1000);
        } catch (error) {
            checksAvailable = false;
            renderTeam();
            message(`Agent seats unavailable. ${error.message}`, true);
        }
    }
    async function save() {
        if (!packageId.value && packageName.value) packageId.value = slug(packageName.value);
        for (const config of editors.querySelectorAll('details.pf-seat-config')) {
            if (config.querySelector(':invalid')) config.open = true;
        }
        if (!form.reportValidity()) {
            message('Some fields need attention before the team can be saved.', true);
            return false;
        }
        const keep = [...omitted];
        const packageData = {id: packageId.value, name: packageName.value,
            seats: seatEditors().map(editor => editor.readSeat())};
        try {
            await request('/api/preflight/packages', packageData);
            message('Team saved. Running seats keep their settings until explicitly restarted.');
            await refresh();
            editPackage(packageData.id, keep);
            return true;
        } catch (error) { message(error.message, true); return false; }
    }
    async function launchTeam() {
        const id = packageSelect.value;
        const result = await request(`/api/preflight/packages/${encodeURIComponent(id)}/launch`, {
            revision: loadedRevision, omitted_seats: [...omitted]});
        snapshot.package_launches[id] = result;
        selectionDirty = false;
        return result;
    }
    // Chat handoff accepts only a same-origin relative path from the server reply.
    function openChat(url) {
        let target = null;
        if (typeof url === 'string' && url.startsWith('/') && !url.startsWith('//') && !url.startsWith('/\\')) {
            try {
                const resolved = new URL(url, window.location.origin);
                if (resolved.origin === window.location.origin) target = resolved.pathname + resolved.search + resolved.hash;
            } catch (_) { target = null; }
        }
        if (!target) {
            message('Could not open chat: unexpected address', true);
            return false;
        }
        window.location.assign(target);
        return true;
    }
    const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
    async function go() {
        const current = savedPackage();
        if (teamPending || !checksAvailable || (current && loadedRevision !== snapshot.package_revisions?.[current.id])) return;
        if (draftDirty || !savedPackage()) {
            if (!await save()) return;
        }
        if (includedCount() < 1) { renderTeam(); return; }
        const id = packageSelect.value;
        teamPending = true;
        goProgress = 'Launching your team…';
        renderRuntime();
        renderTeam();
        const started = Date.now();
        try {
            let state = await launchTeam();
            while (true) {
                const seats = Object.values(state.seats || {});
                const ready = seats.filter(seat => seat.state === 'ready').length;
                if (state.ready) {
                    goProgress = `All ${seats.length} seats ready. Opening chat…`;
                    renderTeam();
                    const result = await request(`/api/preflight/packages/${encodeURIComponent(id)}/chat`, {selection_id: state.selection_id});
                    if (openChat(result.url)) return;
                    break;
                }
                if (state.error || state.state === 'action_required') {
                    const stuck = seats.filter(seat => seat.state !== 'ready' && seat.state !== 'starting').length;
                    message(state.error || `${stuck} seat${stuck === 1 ? ' needs' : 's need'} attention. Retry it, or leave it out and continue.`, true);
                    break;
                }
                if (Date.now() - started > GO_DEADLINE_MS) {
                    message('Still starting after 90 seconds. Open Status details on the waiting seat, then retry or leave it out.', true);
                    break;
                }
                goProgress = `Starting… ${ready} of ${seats.length} seats ready (${Math.round((Date.now() - started) / 1000)}s)`;
                renderRuntime();
                renderTeam();
                await sleep(1000);
                state = await request(`/api/preflight/packages/${encodeURIComponent(id)}/status`);
                snapshot.package_launches[id] = state;
            }
        } catch (error) { message(error.message, true); }
        finally {
            teamPending = false;
            goProgress = null;
            // Keep checking for a while so seats still starting settle without a reload.
            pollsLeft = 20;
            await refresh(false);
        }
    }
    form.addEventListener('submit', async event => {
        event.preventDefault();
        await save();
    });
    packageSelect.addEventListener('change', () => editPackage(packageSelect.value));
    document.getElementById('api-package-new').addEventListener('click', () => { packageSelect.value = ''; editPackage(''); packageName.focus(); });
    document.getElementById('api-seat-add').addEventListener('click', () => {
        const editor = addEditor();
        markDraft();
        editor.querySelector('input')?.focus();
    });
    packageId.addEventListener('input', () => { packageIdTouched = true; });
    packageName.addEventListener('input', () => {
        if (!packageIdTouched && !savedPackage()) packageId.value = slug(packageName.value);
    });
    form.addEventListener('input', markDraft);
    form.addEventListener('change', markDraft);
    reloadTeam.addEventListener('click', async () => {
        const id = packageSelect.value;
        await refresh(false);
        editPackage(id);
    });
    teamGo.addEventListener('click', go);
    teamLaunch.addEventListener('click', async () => {
        if (teamLaunch.disabled) return;
        teamPending = true;
        renderTeam();
        try {
            await launchTeam();
            message('Team launch recorded. Your saved team has not changed.');
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
            openChat(result.url);
        } catch (error) { message(error.message, true); }
        finally { teamPending = false; await refresh(false); }
    });
    document.getElementById('refresh').addEventListener('click', () => refresh());
    refresh();
})();
