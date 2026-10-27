/* Manual documents: the server owns source, author, authorization and durability. */
window.ArtifactDocuments = (() => {
    const LIVE = new Set(['prepared', 'queued', 'active']);
    const ERRORS = {
        source_unavailable: 'Session source could not be captured. Refresh the session and try again.',
        source_too_large: 'Session source is too large. Nothing was truncated.',
        request_too_large: 'The instruction is too large. Use at most 32768 UTF-8 bytes.',
        invalid_request: 'Check the document request and try again.',
        channel_inactive: 'This channel is not writable. Retained documents are still available.',
        channel_mismatch: 'The session belongs to another channel.',
        session_unknown: 'The session was not found.', run_unknown: 'The session run was not found.',
        boundary_held: 'Document storage is busy. Check status before retrying.',
        request_conflict: 'This request conflicts with saved state.',
        not_ready: 'The document is not ready yet.', storage_unavailable: 'Document storage is unavailable.',
        no_author_available: 'No supported live author is available for this session.',
        unexpected_failure: 'The document operation could not be confirmed.',
        operator_forbidden: 'Operator authentication is required. Reload this page.',
        not_found: 'The document request was not found.'
    };
    const CAUSES = {capability_off: 'Artifact authoring is not enabled.', no_agent_role: 'This session has no agent author.',
        no_live_instance: 'The bound author is not running.', not_supported: 'The author does not support document authoring.',
        unmanaged: 'The author is not an app-managed seat.', binding_changed: 'The author binding changed.',
        runtime_unverified: 'The author runtime is not verified.', ambiguous: 'The author identity is ambiguous.',
        producer_unavailable: 'The author became unavailable. Refresh the session before trying again.'};
    const PRE_EFFECT = new Set(['invalid_request', 'request_too_large', 'operator_forbidden', 'capability_off',
        'no_author_available', 'source_unavailable', 'source_too_large', 'session_unknown', 'run_unknown',
        'channel_mismatch', 'channel_inactive']);
    const ABANDON = 'The earlier request may still finish and could create a second document.';
    let view = null, initialized = false;
    const drafts = new Map();
    const key = channel => 'artifact-request:' + channel;
    const hex = (value, length = 32) => typeof value === 'string' && new RegExp('^[0-9a-f]{' + length + '}$').test(value);
    const active = s => view === s && !s.closed && window.activeChannel === s.channel;
    const writable = s => window.ChannelLifecycle?.canWrite(s.channel) === true
        && window.ChannelLifecycle?.ownerAvailable('artifacts', s.channel) === true;

    function node(tag, id, text) {
        const item = document.createElement(tag);
        if (id) item.id = id;
        if (text !== undefined) item.textContent = text;
        return item;
    }
    function text(item, value) {
        value = String(value);
        if (item.textContent !== value) item.textContent = value;
    }
    function button(id, text, action) {
        const item = node('button', id, text); item.type = 'button'; item.onclick = action; return item;
    }
    function persist(s) {
        try {
            if (s.known) window.sessionStorage.setItem(key(s.channel), JSON.stringify(s.known));
            else window.sessionStorage.removeItem(key(s.channel));
        } catch (_) { s.storageUnavailable = true; }
    }
    function saved(channel) {
        try {
            const value = JSON.parse(window.sessionStorage.getItem(key(channel)) || 'null');
            if (value && value.channel === channel && hex(value.request_id) && hex(value.run_id)
                && Number.isSafeInteger(value.session_id) && value.session_id > 0)
                return {channel, request_id: value.request_id, session_id: value.session_id, run_id: value.run_id,
                    instruction_sha256: hex(value.instruction_sha256, 64) ? value.instruction_sha256 : null,
                    intent_channel: typeof value.intent_channel === 'string' ? value.intent_channel : channel,
                    unknown: value.unknown === true};
        } catch (_) { /* Unreadable browser metadata is not server history. */ }
        return null;
    }
    async function digest(text) {
        const bytes = await window.crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
        return [...new Uint8Array(bytes)].map(value => value.toString(16).padStart(2, '0')).join('');
    }
    function textFor(row) {
        if (row.needs_resume && LIVE.has(row.state)) return 'Needs recovery';
        if (row.state === 'imported') return row.version_id ? 'Imported history' : 'Imported history, no document';
        if (row.state === 'cancelled') return row.reason === 'source_stopped' ? 'Stopped' : 'Cancelled';
        return {prepared: 'Queued', queued: 'Queued', active: 'Writing document', fulfilled: 'Ready',
            failed: 'Document could not be completed', quarantined: 'Response rejected'}[row.state] || 'Status unavailable';
    }
    function errorText(data) {
        if (data?.code === 'no_author_available' && data?.cause === 'no_live_instance')
            return 'The agent that ran this session is no longer running. Start a new session with your current team to write from it.';
        let text = typeof data?.error === 'string' ? data.error : ERRORS[data?.code] || ERRORS.unexpected_failure;
        if (data?.cause === 'capability_off') text = CAUSES.capability_off;
        else if (CAUSES[data?.cause]) text += ' ' + CAUSES[data.cause];
        if (data?.cause === 'packet_exists') text += ' Use Request document again to start a fresh request.';
        if (data?.author_name) text += ' Author: ' + data.author_name + '.';
        if (Number.isInteger(data?.examined_roles)) text += ' Agent roles checked: ' + data.examined_roles + '.';
        if (['recorded', 'not_recorded', 'unknown'].includes(data?.durability)) text += ' Effect: ' + data.durability + '.';
        return text;
    }
    function stopPoll(s) { if (s.pollTimer) clearTimeout(s.pollTimer); s.pollTimer = null; }
    function schedule(s) {
        stopPoll(s);
        if (active(s) && !document.hidden && !s.nodes.panel.hidden && s.known && s.row && LIVE.has(s.row.state))
            s.pollTimer = setTimeout(() => refresh(s), Math.min(30000, 2000 * (2 ** s.failures)));
    }
    async function request(s, path, options = {}, blob = false) {
        const controller = new AbortController(); let alarm, cancel;
        const interrupted = new Promise((_, reject) => {
            cancel = () => { controller.abort(); reject(Object.assign(new Error('Request interrupted'), {interrupted: true})); };
            alarm = setTimeout(() => { controller.abort(); reject(Object.assign(new Error('Request timed out'), {timeout: true})); }, 20000);
        });
        s.requests.add(cancel);
        try {
            const work = (async () => {
                const response = await fetch(path, {...options, cache: 'no-store', signal: controller.signal,
                    headers: {'X-Session-Token': window.SESSION_TOKEN, ...(options.body ? {'Content-Type': 'application/json'} : {})}});
                let data;
                if (blob && response.ok) {
                    const media = (response.headers.get('Content-Type') || '').split(';')[0].trim().toLowerCase();
                    if (!['text/markdown', 'application/octet-stream'].includes(media))
                        throw Object.assign(new Error('Unexpected download response'), {data: {code: 'unexpected_failure'}});
                    return response.blob();
                }
                try { data = await response.json(); }
                catch (_) { throw Object.assign(new Error('Invalid server response'), {status: response.status, data: {code: response.status >= 500 ? 'storage_unavailable' : 'unexpected_failure'}}); }
                if (!response.ok) throw Object.assign(new Error('Document operation refused'), {status: response.status, data});
                return data;
            })();
            return await Promise.race([work, interrupted]);
        } finally { clearTimeout(alarm); s.requests.delete(cancel); }
    }
    function render(s) {
        if (!active(s)) return;
        const n = s.nodes, row = s.row;
        const otherSession = row && s.selected && row.source.session_id !== s.selected.session_id;
        const requestTitle = row?.source.session_id ? (s.sessions.get(row.source.session_id)?.title || 'Session ' + row.source.session_id) : 'Imported source';
        const cardLabel = otherSession ? 'Latest request: ' + requestTitle + ' · ' : '';
        text(n.status, row ? cardLabel + textFor(row) + (s.offline ? ' (status unavailable)' : '')
            : s.notFound ? 'Not found yet (the earlier request may still finish)'
            : s.known?.unknown ? 'Not confirmed' : s.listBusy ? 'Loading sessions...' : s.selected ? '' : 'Choose a session to write from');
        let detail = row ? (row.source.session_id ? 'Session ' + row.source.session_id : 'Imported source') + ' · ' + (row.author_name || 'Author unavailable') + ' · ' + row.source.message_count + ' source messages · '
            + row.source.packet_bytes + ' bytes' + (row.source.source_so_far ? ' · Source so far' : ' · Completed source') : '';
        if (s.cancelWarning) detail += ' Document cancellation is unconfirmed; the worker may still be running.';
        if (s.storageUnavailable) detail += ' Browser status recovery is unavailable after reload.';
        text(n.source, detail);
        text(n.error, s.error || '');
        text(n.submit, s.submitting ? 'Saving request...' : s.known?.unknown ? 'Retry same request' : row ? 'Request another document' : 'Request document');
        n.submit.disabled = s.submitting || !writable(s) || (!s.selected && !s.known?.unknown);
        n.select.disabled = s.submitting || s.known?.unknown === true || s.sessions.size === 0;
        n.cancel.hidden = !row || !LIVE.has(row.state); n.cancel.disabled = s.cancelling;
        n.refresh.disabled = !s.known || s.refreshing || s.cancelling;
        const ready = hex(row?.version_id) && ['fulfilled', 'imported'].includes(row.state);
        n.read.hidden = !ready; n.download.hidden = !ready;
        n.read.disabled = s.reading; n.download.disabled = s.downloading;
        n.abandon.hidden = !s.known?.unknown;
        text(n.policy, writable(s) ? '' : 'New documents are unavailable while this channel or its artifact storage is archived, held or unavailable.');
    }
    function adopt(s, row, id) {
        if (!row || row.request_id !== id || row.channel !== s.channel || !row.source) throw new Error('Mismatched document response');
        s.row = row; s.notFound = false; s.offline = false; s.failures = 0;
        s.known = {...s.known, request_id: id, channel: s.channel, session_id: row.source.session_id,
            run_id: row.source.run_id, unknown: false};
        s.intent = null; persist(s);
    }
    async function refresh(s) {
        if (!active(s) || document.hidden || s.nodes.panel.hidden || !s.known || s.refreshing || s.cancelling) return;
        stopPoll(s); s.refreshing = true; const id = s.known.request_id, serial = ++s.statusSerial; render(s);
        try {
            const row = await request(s, '/api/artifacts/requests/' + encodeURIComponent(id));
            if (!active(s) || s.known?.request_id !== id || s.statusSerial !== serial) return;
            adopt(s, row, id); s.error = '';
            if (row.transport_settled === true) s.cancelWarning = null;
        } catch (error) {
            if (!active(s) || s.known?.request_id !== id || s.statusSerial !== serial) return;
            if (error.data?.code === 'not_found' && s.known.unknown) {
                s.notFound = true; s.error = 'The earlier request may still finish. Check status or retry the same instruction.';
            } else { s.offline = true; s.failures = Math.min(s.failures + 1, 4); s.error = errorText(error.data); }
        } finally { s.refreshing = false; if (active(s)) { render(s); schedule(s); } }
    }
    async function loadSessions(s, more = false) {
        if (!active(s) || s.listBusy) return;
        s.listBusy = true; const serial = ++s.listSerial, offset = more ? s.offset : 0;
        s.nodes.more.disabled = true; render(s);
        try {
            const value = await request(s, '/api/artifacts/sessions?channel=' + encodeURIComponent(s.channel) + '&offset=' + offset);
            if (!active(s) || serial !== s.listSerial) return;
            if (s.listFailure) { s.error = ''; s.listFailure = false; }
            text(s.nodes.more, 'More sessions');
            if (!more) { s.sessions.clear(); s.nodes.select.replaceChildren(); }
            for (const item of value.sessions || []) {
                if (s.sessions.has(item.session_id)) continue;
                s.sessions.set(item.session_id, item);
                // The start time tells apart sessions that share a template title.
                const started = new Date(item.started_at * 1000).toLocaleString([], {month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'});
                const option = node('option', null, item.title + ' (' + item.state + ') · ' + started); option.value = String(item.session_id);
                s.nodes.select.appendChild(option);
            }
            s.offset = offset + 20; s.nodes.more.hidden = value.has_more !== true;
            const preferred = s.sessions.get(s.known?.session_id) || [...s.sessions.values()][0];
            if (!s.selected && preferred) { s.selected = preferred; s.nodes.select.value = String(preferred.session_id); }
            if (!preferred) {
                s.error = 'No saved sessions in this channel yet. Complete a session, then return here.';
                const placeholder = node('option', null, 'No finished sessions yet'); placeholder.value = '';
                s.nodes.select.replaceChildren(placeholder);
            }
        } catch (error) { if (active(s)) { s.error = errorText(error.data); s.listFailure = true; s.nodes.more.hidden = false; text(s.nodes.more, 'Retry sessions'); } }
        finally { s.listBusy = false; if (active(s)) { s.nodes.more.disabled = false; render(s); } }
    }
    async function submit(s) {
        if (!active(s) || s.submitting || !writable(s)) return;
        s.submitting = true; stopPoll(s); s.error = ''; render(s);
        try {
            const instruction = s.nodes.instruction.value;
            if (!instruction.trim() || /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(instruction) || new TextEncoder().encode(instruction).length > 32768) {
                s.error = 'Enter a non-blank instruction of at most 32768 UTF-8 bytes; only tab and line-break controls are allowed.'; return;
            }
            const wasUnknown = s.known?.unknown === true;
            const identifier = wasUnknown ? s.known.request_id : window.crypto.randomUUID().replace(/-/g, '');
            const instructionHash = await digest(identifier + ':' + instruction);
            if (!active(s) || (wasUnknown && s.known?.request_id !== identifier)) return;
            let intent;
            if (s.known?.unknown) {
                if (s.known.instruction_sha256 !== instructionHash) {
                    s.error = 'Re-enter the original instruction to retry this request, or explicitly abandon it.'; return;
                }
                intent = s.intent || {request_id: s.known.request_id, channel: s.known.intent_channel || s.channel, session_id: s.known.session_id,
                    run_id: s.known.run_id, instruction};
            } else {
                if (!s.selected) return;
                intent = {request_id: identifier, channel: s.channel,
                    session_id: s.selected.session_id, run_id: s.selected.run_id, instruction};
                s.cancelWarning = null;
                s.row = null; s.nodes.reader.textContent = ''; s.nodes.reader.hidden = true;
            }
            s.statusSerial++; s.readSerial++; s.notFound = false; s.intent = intent;
            s.known = {request_id: intent.request_id, channel: s.channel, session_id: intent.session_id,
                run_id: intent.run_id, instruction_sha256: instructionHash, intent_channel: intent.channel, unknown: true};
            persist(s); render(s); const id = intent.request_id;
            try {
                const value = await request(s, '/api/artifacts/requests', {method: 'POST', body: JSON.stringify(intent)});
                if (!active(s) || s.known?.request_id !== id) return;
                adopt(s, value.request, id); s.error = '';
            } catch (error) {
                if (!active(s) || s.known?.request_id !== id) return;
                s.error = errorText(error.data);
                if (error.data?.request) adopt(s, error.data.request, id);
                else if (error.data?.cause === 'packet_exists' || (error.data?.durability === 'not_recorded' && error.data?.code)
                    || (!wasUnknown && error.status >= 400 && error.status < 500 && PRE_EFFECT.has(error.data?.code))) {
                    s.known = null; s.intent = null; persist(s);
                } else s.error = 'Not confirmed. ' + s.error + ' Check status before starting a new request.';
            }
        } catch (_) { if (active(s)) s.error = s.known?.unknown
            ? 'Not confirmed. Check status or retry the same request.' : 'The request could not be prepared. No new request was sent.'; }
        finally { s.submitting = false; if (active(s)) { render(s); schedule(s); } }
    }
    async function cancel(s) {
        if (!active(s) || !s.row || !LIVE.has(s.row.state) || s.cancelling) return;
        stopPoll(s); s.cancelling = true; s.statusSerial++; const id = s.row.request_id; render(s);
        try {
            const value = await request(s, '/api/artifacts/requests/' + encodeURIComponent(id) + '/cancel', {method: 'POST', body: '{}'});
            if (!active(s) || s.known?.request_id !== id) return;
            adopt(s, value.request, id);
            s.cancelWarning = value.transport_settled === true ? null : value.request.warning || 'transport_unconfirmed';
            s.error = '';
        } catch (error) {
            if (!active(s) || s.known?.request_id !== id) return;
            if (error.data?.request) adopt(s, error.data.request, id);
            s.cancelWarning = error.status === 404 && error.data?.code === 'not_found' ? null : 'transport_unconfirmed';
            s.offline = true; s.error = errorText(error.data);
        } finally { s.cancelling = false; if (active(s)) { render(s); schedule(s); } }
    }
    async function read(s) {
        if (!active(s) || !s.row?.version_id || s.reading) return;
        s.reading = true; s.nodes.reader.hidden = true; s.nodes.reader.textContent = '';
        const serial = ++s.readSerial, id = s.row.request_id; render(s);
        try {
            const value = await request(s, '/api/artifacts/requests/' + encodeURIComponent(id) + '/document');
            if (!active(s) || s.known?.request_id !== id || serial !== s.readSerial) return;
            if (typeof value.markdown !== 'string') throw new Error('Document text unavailable');
            s.nodes.reader.textContent = value.markdown; s.nodes.reader.hidden = false; s.error = '';
            s.nodes.reader.scrollIntoView?.({block: 'nearest'});
        } catch (error) {
            if (active(s) && serial === s.readSerial) { s.nodes.reader.hidden = true; s.error = errorText(error.data); }
        } finally { s.reading = false; if (active(s)) render(s); }
    }
    async function download(s) {
        if (!active(s) || !s.row?.version_id || s.downloading) return;
        if (!hex(s.row.version_id)) { s.error = 'Document version is unavailable. Refresh before downloading.'; render(s); return; }
        s.downloading = true; const id = s.known.request_id, version = s.row.version_id; render(s);
        try {
            const blob = await request(s, '/api/artifacts/versions/' + encodeURIComponent(version) + '/download', {}, true);
            if (!active(s) || s.known?.request_id !== id) return;
            const url = URL.createObjectURL(blob); s.urls.add(url);
            const anchor = node('a'); anchor.href = url; anchor.download = 'document.md'; document.body.appendChild(anchor);
            anchor.click(); anchor.remove();
            const timer = setTimeout(() => { s.revokeTimers.delete(timer); if (s.urls.delete(url)) URL.revokeObjectURL(url); }, 1000);
            s.revokeTimers.add(timer);
        } catch (error) { if (active(s) && s.known?.request_id === id) s.error = errorText(error.data); }
        finally { s.downloading = false; if (active(s)) render(s); }
    }
    function close(focus = true) {
        const s = view; if (!s) return;
        drafts.set(s.channel, s.nodes.instruction.value);
        s.closed = true; stopPoll(s); s.requests.forEach(abort => abort());
        s.urls.forEach(url => URL.revokeObjectURL(url)); s.urls.clear();
        s.revokeTimers.forEach(clearTimeout); s.revokeTimers.clear();
        s.nodes.reader.textContent = ''; s.nodes.reader.hidden = true; s.nodes.panel.hidden = true;
        view = null;
        document.getElementById('artifact-documents-open')?.setAttribute('aria-expanded', 'false');
        if (focus) document.getElementById('artifact-documents-open')?.focus();
    }
    function createPanel(s) {
        document.getElementById('artifact-documents-panel')?.remove();
        const panel = node('section', 'artifact-documents-panel'); panel.className = 'artifact-documents'; panel.setAttribute('aria-label', 'Session documents');
        const heading = node('div'); heading.className = 'artifact-heading';
        heading.append(node('h2', null, 'Write from a session'), button('artifact-close', 'Close', () => close()));
        const intro = node('p', null, 'Turn accepted session work into a document. Source is captured when you submit.');
        const label = node('label', null, 'Session'); label.htmlFor = 'artifact-session-select';
        const select = node('select', 'artifact-session-select');
        select.onchange = () => { if (active(s) && !s.known?.unknown) { s.selected = s.sessions.get(Number(select.value)); render(s); } };
        const more = button('artifact-more-sessions', 'More sessions', () => loadSessions(s, true)); more.hidden = true;
        const instructionLabel = node('label', null, 'What should the document do?'); instructionLabel.htmlFor = 'artifact-instruction';
        const instruction = node('textarea', 'artifact-instruction'); instruction.rows = 3;
        instruction.value = drafts.get(s.channel) || '';
        instruction.placeholder = 'For example: summarize the decisions and open questions.';
        const policy = node('p'); policy.className = 'artifact-note'; policy.setAttribute('role', 'status');
        const submitButton = button('artifact-submit', 'Request document', () => submit(s));
        const status = node('p', 'artifact-status'); status.className = 'artifact-status'; status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
        const source = node('p', 'artifact-source'); source.className = 'artifact-note';
        const error = node('p', 'artifact-error'); error.setAttribute('role', 'alert');
        const actions = node('div'); actions.className = 'artifact-actions';
        const refreshButton = button('artifact-refresh', 'Refresh', () => refresh(s));
        const cancelButton = button('artifact-cancel', 'Cancel request', () => cancel(s));
        const readButton = button('artifact-read', 'Read document', () => read(s));
        const downloadButton = button('artifact-download', 'Download Markdown', () => download(s));
        const abandon = button('artifact-abandon', 'Abandon and start new', () => { warning.hidden = false; confirm.focus(); });
        const warning = node('div', 'artifact-abandon-warning'); warning.hidden = true;
        const warningText = node('p', null, ABANDON); warningText.setAttribute('role', 'alert');
        const confirm = button('artifact-abandon-confirm', 'Abandon earlier request', () => {
            s.statusSerial++; s.readSerial++; stopPoll(s); s.known = null; s.intent = null; s.row = null; s.notFound = false;
            persist(s); warning.hidden = true; s.error = ABANDON; render(s); instruction.focus();
        });
        warning.append(warningText, confirm, button('artifact-abandon-keep', 'Keep earlier request', () => { warning.hidden = true; abandon.focus(); }));
        actions.append(refreshButton, cancelButton, readButton, downloadButton, abandon);
        const reader = node('pre', 'artifact-reader'); reader.hidden = true; reader.tabIndex = 0; reader.setAttribute('aria-label', 'Verified document text');
        const history = node('p', null, 'Only the latest request is shown here. Earlier requests are not listed and may still be running.'); history.className = 'artifact-note';
        panel.append(heading, intro, label, select, more, instructionLabel, instruction, policy, submitButton, status, source, error, actions, warning, reader, history);
        panel.addEventListener('keydown', event => { if (event.key === 'Escape') { event.preventDefault(); close(); } });
        document.getElementById('session-bar').after(panel);
        s.nodes = {panel, select, more, instruction, policy, submit: submitButton, status, source, error,
            refresh: refreshButton, cancel: cancelButton, read: readButton, download: downloadButton, abandon, reader};
    }
    async function open() {
        close(false);
        const openingFocus = document.activeElement;
        const channel = window.activeChannel;
        const s = {channel, closed: false, sessions: new Map(), selected: null, known: saved(channel), row: null,
            requests: new Set(), urls: new Set(), revokeTimers: new Set(), offset: 0, failures: 0, statusSerial: 0, readSerial: 0, listSerial: 0};
        view = s; createPanel(s); render(s);
        document.getElementById('artifact-documents-open')?.setAttribute('aria-expanded', 'true');
        await loadSessions(s);
        if (active(s) && s.known) await refresh(s);
        if (active(s) && document.activeElement === openingFocus) s.nodes.select.focus();
    }
    function init() {
        if (initialized) return; initialized = true;
        const trigger = document.getElementById('artifact-documents-open');
        if (trigger) { trigger.onclick = open; trigger.setAttribute('aria-expanded', 'false'); }
        document.addEventListener('visibilitychange', () => {
            if (!view) return;
            if (document.hidden) stopPoll(view); else schedule(view);
        });
        Store.watch('activeChannel', () => close(false));
        Hub.on('channel_lifecycle', () => { if (view) render(view); });
        Hub.on('channel_renamed', event => {
            if (view && [event.old_name, event.new_name].includes(view.channel)) close(false);
            if (drafts.has(event.old_name)) { drafts.set(event.new_name, drafts.get(event.old_name)); drafts.delete(event.old_name); }
            try {
                const previous = saved(event.old_name);
                if (previous) { previous.channel = event.new_name; window.sessionStorage.setItem(key(event.new_name), JSON.stringify(previous)); window.sessionStorage.removeItem(key(event.old_name)); }
            } catch (_) { /* Browser metadata does not authorize writes. */ }
        });
        Hub.on('channel_deleted', event => {
            if (view?.channel === event.channel) close(false);
            drafts.delete(event.channel);
            try { window.sessionStorage.removeItem(key(event.channel)); } catch (_) { /* Optional browser metadata. */ }
        });
    }
    return {init, open, close};
})();
