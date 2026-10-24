/* Authoritative channel catalog and the shared management surface. */
'use strict';
window.ChannelLifecycle = (() => {
    let catalog = null, ready = false, epoch = 0, controller = null, current = null, mutation = null;
    const pendingEvents = [], appliedEvents = new Set();
    const policyDisabled = new WeakMap();
    const states = new Set(['active', 'archived', 'retired', 'unregistered']);
    const countKeys = ['messages', 'todos', 'jobs', 'schedules', 'sessions', 'summaries', 'uploads'];
    const ownerKeys = [...countKeys, 'queue'];
    const knownErrors = new Set([
        'That channel name is already used or retired.',
        'That channel name is already used or retired by another channel.',
        'Destination contains saved data or unresolved work; choose an unused name.',
        'Channel contents or work changed; refresh the preview.',
        'Channel work is still pending; inspect its blocking scope first.',
        'Type the exact channel name to confirm.', 'General is protected.',
        'Reopen this channel first.', 'There are no queued messages to cancel.',
        'No repairable history is pending; live work must wait or restart.'
    ]);
    const copy = value => value == null ? value : JSON.parse(JSON.stringify(value));
    const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
    const integer = value => Number.isSafeInteger(value) && value >= 0;
    const node = (tag, text, className) => {
        const element = document.createElement(tag);
        if (text !== undefined) element.textContent = text;
        if (className) element.className = className;
        return element;
    };
    const button = (text, action, className) => {
        const element = node('button', text, className || 'channel-manager-button');
        element.type = 'button'; element.onclick = action; return element;
    };
    class ChannelRequestError extends Error {
        constructor(message, status) { super(message); this.status = status; }
    }
    async function jsonRequest(url, options = {}, externalController = null) {
        const abort = externalController || new AbortController();
        const timer = setTimeout(() => abort.abort(), 8000);
        try {
            const response = await fetch(url, {...options, cache: 'no-store', signal: abort.signal,
                headers: {'X-Session-Token': window.SESSION_TOKEN, ...options.headers}});
            const value = await response.json();
            if (!response.ok) {
                const message = object(value) && knownErrors.has(value.error) ? value.error
                    : response.status === 409 ? 'Channel state changed. Refresh the preview; your draft is kept.'
                    : response.status === 503 ? 'Channel storage is unavailable. Reload after repair; drafts are kept.'
                    : response.status === 403 ? 'The operator session is unavailable. Reconnect before changing channels; drafts are kept.'
                    : 'The channel request could not be completed. Check the name and reload its preview.';
                throw new ChannelRequestError(message, response.status);
            }
            return value;
        } catch (error) {
            if (error instanceof ChannelRequestError) throw error;
            throw new ChannelRequestError('The channel request could not be confirmed. Reload the catalog and check again.', 0);
        } finally { clearTimeout(timer); }
    }
    function validCounts(value) {
        return object(value) && countKeys.every(key => integer(value[key]));
    }
    function validDisplayRow(row) {
        if (!object(row.errors) || Object.keys(row.errors).some(key => !ownerKeys.includes(key) || typeof row.errors[key] !== 'string' || !row.errors[key])) return false;
        if (row.state === 'unregistered') return row.counts === null && row.overdue_schedules === 0 && !Object.keys(row.errors).length;
        return object(row.counts) && ownerKeys.every(key => row.errors[key] ? row.counts[key] === null : integer(row.counts[key]))
            && (row.errors.schedules ? row.overdue_schedules === null : integer(row.overdue_schedules));
    }
    function validateCatalog(value) {
        if (!object(value) || !integer(value.revision) || !Array.isArray(value.channels)
                || !(value.intent === null || object(value.intent))) throw new Error('Invalid catalog.');
        const names = new Set();
        for (const row of value.channels) {
            if (!object(row) || typeof row.name !== 'string' || !row.name || names.has(row.name)
                    || !states.has(row.state) || !validDisplayRow(row)) throw new Error('Invalid channel row.');
            if (row.state !== 'unregistered' && !/^[a-z0-9][a-z0-9-]{0,19}$/.test(row.name)) throw new Error('Invalid channel name.');
            names.add(row.name);
        }
        if (!value.channels.some(row => row.name === 'general' && row.state === 'active')) throw new Error('General is unavailable.');
        if (value.intent) {
            const intent = value.intent;
            if (!/^[a-f0-9]{32}$/.test(intent.request_id) || !['delete', 'rename'].includes(intent.op)
                    || typeof intent.old !== 'string' || !names.has(intent.old)
                    || (intent.op === 'rename' ? typeof intent.new !== 'string' : intent.new !== null)
                    || !Array.isArray(intent.completed_steps) || intent.completed_steps.some(step => typeof step !== 'string')) throw new Error('Invalid pending operation.');
        }
        return copy(value);
    }
    function state(name) {
        if (!ready || !catalog) return 'unavailable';
        if (catalog.intent && [catalog.intent.old, catalog.intent.new].includes(name)) return 'held';
        return catalog.channels.find(row => row.name === name)?.state || 'unregistered';
    }
    function canWrite(name) { return state(name) === 'active'; }
    function ownerAvailable(owner, name) {
        const row = ready && catalog?.channels.find(item => item.name === name);
        return !!row && row.state !== 'unregistered' && ownerKeys.includes(owner)
            && !row.errors[owner] && integer(row.counts?.[owner]);
    }
    function partialContents(name) {
        return !!catalog?.channels.find(row => row.name === name && Object.keys(row.errors).length);
    }
    function reason(name) {
        const value = state(name);
        return value === 'active' ? '' : value === 'archived' ? `#${name} is archived. Reopen it to write or start a review.`
            : value === 'retired' ? `#${name} was deleted. Saved records are read-only.`
            : value === 'held' ? `#${name} is held while channel repair finishes.`
            : value === 'unregistered' ? `#${name} is not registered as an active channel. Your draft is kept.`
            : 'Channel status is unavailable. Reload the catalog; your draft is kept.';
    }
    function renderPolicy(message = '') {
        if (!document.body) return;
        const name = window.activeChannel || 'general';
        const writable = canWrite(name);
        document.body.dataset.channelState = state(name);
        let banner = document.getElementById('channel-state-banner');
        if (!banner) {
            banner = node('section', undefined, 'channel-state-banner'); banner.id = 'channel-state-banner';
            banner.setAttribute('aria-live', 'polite');
            const bar = document.getElementById('channel-bar');
            if (bar) bar.insertAdjacentElement('afterend', banner); else document.body.appendChild(banner);
        }
        banner.replaceChildren(); banner.hidden = writable && !message;
        if (!banner.hidden) {
            banner.appendChild(node('p', message || reason(name)));
            banner.appendChild(button('Manage channels', () => openManage({channel: name})));
            if (!writable && name !== 'general') banner.appendChild(button('Back to general', () => window.switchChannel?.('general')));
            if (!ready) banner.appendChild(button('Reload catalog', () => refresh().catch(() => {})));
        }
        const input = document.getElementById('input');
        if (input) { input.readOnly = !writable; input.setAttribute('aria-describedby', 'channel-state-banner'); }
        for (const id of ['send', 'mic', 'schedule-btn', 'session-launch-btn', 'clear-chat-btn', 'image-upload']) {
            const element = document.getElementById(id);
            const owner = id === 'schedule-btn' ? 'schedules' : id === 'session-launch-btn' ? 'sessions' : null;
            const allowed = writable && (!owner || ownerAvailable(owner, name));
            if (element && !allowed) {
                if (!policyDisabled.has(element)) policyDisabled.set(element, element.disabled);
                element.disabled = true;
            } else if (element && policyDisabled.has(element)) {
                element.disabled = policyDisabled.get(element); policyDisabled.delete(element);
            }
        }
        document.querySelectorAll('[data-channel-write]').forEach(element => {
            element.disabled = !canWrite(element.dataset.channelWrite || name) || !ownerAvailable('sessions', element.dataset.channelWrite || name);
        });
    }
    function guardWrite(name) {
        if (canWrite(name)) return true;
        renderPolicy(reason(name)); return false;
    }
    function notify() {
        renderPolicy();
        if (typeof Hub !== 'undefined') Hub.emit('channel_lifecycle', {revision: catalog?.revision ?? null});
        if (current && !current.closed) renderManager(current);
    }
    function verifiedEvents() {
        for (let index = pendingEvents.length - 1; index >= 0; index--) {
            const event = pendingEvents[index];
            if (integer(event.revision) && catalog.revision < event.revision) continue;
            const renamed = event.type === 'channel_renamed';
            const matched = renamed
                ? catalog.channels.some(row => row.name === event.new_name && row.state === 'active')
                    && !catalog.channels.some(row => row.name === event.old_name)
                : catalog.channels.some(row => row.name === event.channel && row.state === 'retired');
            if (!matched) continue;
            const key = JSON.stringify(event);
            if (!appliedEvents.has(key)) {
                if (renamed) window.applyChannelRename?.(event); else window.invalidateDeletedChannel?.(event.channel);
                if (typeof Hub !== 'undefined') Hub.emit(event.type, event);
                appliedEvents.add(key);
            }
            pendingEvents.splice(index, 1);
        }
        for (const row of catalog.channels) if (row.state === 'retired') window.invalidateDeletedChannel?.(row.name);
    }
    async function refresh() {
        const mine = ++epoch;
        controller?.abort(); controller = new AbortController();
        try {
            const value = validateCatalog(await jsonRequest('/api/channels', {}, controller));
            if (mine !== epoch) return copy(catalog);
            if (!catalog || value.revision >= catalog.revision) catalog = value;
            ready = true; verifiedEvents();
            window.applyChannelSettings?.(catalog.channels.filter(row => row.state === 'active').map(row => row.name));
            notify(); return copy(catalog);
        } catch (error) {
            if (mine !== epoch) return copy(catalog);
            ready = false; notify();
            throw new ChannelRequestError('Channel status is unavailable. Reload the catalog; drafts are kept.', error.status || 0);
        }
    }
    async function handleEvent(event) {
        if (['channel_renamed', 'channel_deleted'].includes(event.type)) pendingEvents.push(copy(event));
        return refresh();
    }
    function errorText(error) {
        return error instanceof ChannelRequestError ? error.message : 'The channel request could not be confirmed. Reload the catalog and check again.';
    }
    function report(form, text) {
        if (form !== current || form.closed) return;
        form.error = text; renderManager(form);
    }
    function closeManager(form) {
        if (form.closed) return;
        form.closed = true; form.readController?.abort();
        form.dialog.close?.(); form.dialog.remove();
        if (current === form) current = null;
        if (form.trigger?.isConnected !== false) form.trigger?.focus?.();
    }
    function openManage({channel = window.activeChannel || 'general', op = null} = {}) {
        if (current) closeManager(current);
        const dialog = node('dialog', undefined, 'channel-manager'); dialog.id = 'channel-manager';
        dialog.setAttribute('aria-labelledby', 'channel-manager-title');
        const form = {dialog, trigger: document.activeElement, channel, op, name: '', confirmation: '',
            preview: null, requestId: null, busy: false, error: '', warning: '', closed: false, retained: null, readEpoch: 0};
        current = form; document.body.appendChild(dialog);
        dialog.addEventListener('cancel', event => { event.preventDefault(); closeManager(form); });
        dialog.addEventListener('close', () => closeManager(form));
        dialog.addEventListener('click', event => { if (event.target === dialog) closeManager(form); });
        dialog.addEventListener('keydown', event => {
            if (event.key !== 'Tab') return;
            const elements = [...dialog.querySelectorAll('button, input, select, textarea, a[href]')]
                .filter(element => !element.disabled && !element.hidden);
            const first = elements[0], last = elements[elements.length - 1];
            if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
            else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
        });
        renderManager(form); dialog.showModal?.();
        refresh().then(() => {
            if (current === form && !form.closed && form.op === 'view') readRetained(form);
        }).catch(error => report(form, errorText(error)));
        return dialog;
    }
    function choose(form, channel, op) {
        form.readEpoch++; form.readController?.abort();
        form.channel = channel; form.op = op; form.name = ''; form.confirmation = '';
        form.preview = null; form.requestId = null; form.error = ''; form.warning = ''; form.retained = null;
        renderManager(form);
        if (op === 'view') readRetained(form);
    }
    function labelled(parent, text, id, value, change) {
        const label = node('label', text); label.htmlFor = id;
        const input = node('input'); input.id = id; input.type = 'text'; input.value = value;
        input.autocomplete = 'off'; input.addEventListener('input', () => change(input.value));
        parent.append(label, input); return input;
    }
    function target(form) { return form.op === 'create' ? form.name : form.channel; }
    function updateApply(form) {
        const apply = form.dialog.querySelector('#channel-manager-apply');
        const blocked = form.preview && !['create', 'reopen', 'recover_projections'].includes(form.op)
            && form.preview.blockers.some(item => !(form.op === 'cancel_queued' && item.kind === 'transport' && item.state === 'queued'));
        const noQueued = form.op === 'cancel_queued' && !form.preview?.queued_dispatch_ids.length;
        const noRepair = form.op === 'recover_projections' && !form.preview?.blockers.some(item => item.kind === 'projection_pending' && !item.reason);
        if (apply) apply.disabled = !ready || !!mutation || form.busy || !form.preview
            || form.confirmation !== target(form) || !target(form) || blocked || noQueued || noRepair || partialContents(target(form));
    }
    function renderManager(form) {
        if (form !== current || form.closed) return;
        const focused = document.activeElement;
        const focusId = form.dialog.contains(focused) ? focused.id : null;
        const selection = focused && typeof focused.selectionStart === 'number' ? [focused.selectionStart, focused.selectionEnd] : null;
        form.dialog.replaceChildren();
        const header = node('header', undefined, 'channel-manager-header');
        const title = node('h2', 'Manage channels'); title.id = 'channel-manager-title';
        header.append(title, button('Close', () => closeManager(form))); form.dialog.appendChild(header);
        const status = node('p', form.error || form.warning || (!ready ? 'Checking channel status. Drafts are kept.' : ''), 'channel-manager-status');
        status.id = 'channel-manager-status'; status.setAttribute('role', 'alert'); form.dialog.appendChild(status);
        form.dialog.appendChild(button('Reload catalog', () => refresh().catch(error => report(form, errorText(error)))));
        if (catalog?.intent) {
            const intent = catalog.intent, repair = node('section', undefined, 'channel-manager-repair');
            repair.append(node('h3', 'Channel repair is pending'), node('p', `${intent.op}: ${intent.old}${intent.new ? ' to ' + intent.new : ''}`),
                node('p', `Completed steps: ${intent.completed_steps.join(', ') || 'none'}. Only these channel names are held.`));
            let typed = '';
            const retry = button('Retry repair', () => mutate(form, true)); retry.id = 'channel-manager-retry'; retry.disabled = true;
            labelled(repair, `Type ${intent.old} to retry`, 'channel-manager-repair-confirm', '', value => {
                typed = value; form.repairConfirmed = typed === intent.old; retry.disabled = !ready || !!mutation || !form.repairConfirmed;
            });
            repair.appendChild(retry); form.dialog.appendChild(repair);
        }
        const layout = node('div', undefined, 'channel-manager-layout'), list = node('section'); list.id = 'channel-manager-list';
        list.appendChild(button('Create channel', () => choose(form, '', 'create')));
        for (const [key, title] of [['active', 'Active'], ['archived', 'Archived'], ['retired', 'Retired'], ['unregistered', 'Unregistered data']]) {
            list.appendChild(node('h3', title));
            const rows = catalog?.channels.filter(row => row.state === key) || [];
            if (!rows.length) list.appendChild(node('p', key === 'retired' ? 'Deleted channels keep their saved records here.' : `No ${title.toLowerCase()} channels.`));
            for (const row of rows) {
                const line = node('div', undefined, 'channel-manager-row');
                line.appendChild(node('strong', '# ' + row.name));
                line.appendChild(node('p', row.counts ? `${row.counts.messages ?? 'Unavailable'} messages, ${row.counts.jobs ?? 'unavailable'} jobs, ${row.counts.sessions ?? 'unavailable'} reviews, ${row.counts.summaries ?? 'unavailable'} summaries` : 'Saved data is readable. Register a valid channel name through create or import before writing.'));
                for (const owner of Object.keys(row.errors)) line.appendChild(node('p', `${owner}: Cannot confirm contents; repair storage first.`, 'channel-manager-status'));
                const actions = node('div', undefined, 'channel-manager-actions');
                const ops = row.name === 'general' ? ['view'] : key === 'active' ? ['view', 'rename', 'archive', 'delete', 'cancel_queued', 'recover_projections'] : key === 'archived' ? ['view', 'reopen', 'delete'] : ['view'];
                if (row.name === 'general') line.appendChild(node('span', 'Protected', 'channel-manager-state'));
                for (const op of ops) {
                    const labels = {view: 'View retained records', cancel_queued: 'Cancel queued only', recover_projections: 'Repair history'};
                    const control = button(labels[op] || op[0].toUpperCase() + op.slice(1), () => choose(form, row.name, op));
                    control.dataset.channelName = row.name; control.dataset.channelOp = op;
                    control.disabled = !ready || !!mutation; actions.appendChild(control);
                }
                line.appendChild(actions); list.appendChild(line);
            }
        }
        const detail = node('section'); detail.id = 'channel-manager-detail'; layout.append(list, detail); form.dialog.appendChild(layout);
        if (!form.op) detail.appendChild(node('p', 'Choose a channel action. Nothing changes until its consequences are checked and confirmed.'));
        else if (form.op === 'view') renderRetained(form, detail);
        else renderAction(form, detail);
        const next = focusId ? form.dialog.querySelector('#' + focusId) : null;
        if (next) { next.focus(); if (selection && typeof next.setSelectionRange === 'function') next.setSelectionRange(...selection); }
        updateApply(form);
    }
    function renderAction(form, detail) {
        const labels = {create: 'Create channel', rename: 'Rename channel', archive: 'Archive channel', reopen: 'Reopen channel', delete: 'Delete channel', cancel_queued: 'Cancel queued messages only', recover_projections: 'Repair retained history'};
        detail.append(node('h3', labels[form.op] || 'Channel action'), node('p', form.channel ? '# ' + form.channel : 'Choose a new channel name.'));
        if (['rename', 'create'].includes(form.op)) labelled(detail, form.op === 'rename' ? 'New name' : 'Channel name', 'channel-manager-name', form.name, value => {
            form.name = value; form.preview = null; form.requestId = null;
            form.dialog.querySelector('#channel-manager-consequences')?.replaceChildren(); updateApply(form);
        });
        if (partialContents(target(form))) detail.appendChild(node('p', 'Cannot confirm contents; repair storage first.', 'channel-manager-status'));
        const preview = button(form.busy ? 'Checking' : 'Preview consequences', () => previewAction(form));
        preview.id = 'channel-manager-preview'; preview.disabled = !ready || !!mutation || form.busy;
        detail.appendChild(preview);
        const consequences = node('div'); consequences.id = 'channel-manager-consequences'; detail.appendChild(consequences);
        if (form.preview) {
            const value = form.preview, counts = value.counts;
            consequences.appendChild(node('p', `${counts.messages} messages, ${counts.todos} todos, ${counts.jobs} jobs, ${counts.sessions} reviews, ${counts.schedules} schedules, ${counts.summaries} summaries, ${counts.uploads} attachment references.`));
            const copy = form.op === 'delete' ? 'Chat messages and todos will be removed. Jobs, reviews, summaries and attachment references stay read-only. Upload files stay. Artifact purge is not supported. You will stay in a retained view.'
                : form.op === 'archive' ? 'History and saved records stay. Writing, new reviews and automatic routing stop until Reopen.'
                : form.op === 'reopen' ? `${value.overdue_schedules} overdue enabled schedules will run once at the next tick, then follow their normal cadence.`
                : form.op === 'cancel_queued' ? 'Only the listed queued records are cancelled. Active, uncertain and cancelling work is untouched. This does not archive or delete the channel.'
                : form.op === 'rename' ? 'Messages and mutable records move to the new name. Frozen briefs, typed journals and queue audit stay unchanged. The old name remains reserved.'
                : form.op === 'recover_projections' ? 'Repair completed history only. Live pending work must wait or restart; no review or worker is started.' : 'This registers a new active channel.';
            consequences.appendChild(node('p', copy));
            for (const block of value.blockers) consequences.appendChild(node('p', `${block.kind}${block.reason ? ': ' + block.reason.replaceAll('_', ' ') : ''}. Session ${block.session_id ?? 'none'}, run ${block.run_id || 'none'}, dispatch ${block.dispatch_id || 'none'}, state ${block.state || 'unknown'}.`, 'channel-manager-blocker'));
            if (form.op === 'cancel_queued') consequences.appendChild(node('p', `Queued dispatches: ${value.queued_dispatch_ids.join(', ') || 'none'}`));
        }
        labelled(detail, `Type the exact name ${target(form) || '(choose a name)'}`, 'channel-manager-confirm', form.confirmation, value => { form.confirmation = value; updateApply(form); });
        const apply = button(form.busy ? 'Working' : 'Apply confirmed action', () => mutate(form)); apply.id = 'channel-manager-apply'; detail.appendChild(apply);
    }
    async function previewAction(form) {
        if (form.busy || mutation || !ready) return;
        form.busy = true; form.error = ''; renderManager(form);
        const body = {op: form.op, channel: target(form)};
        if (form.op === 'rename') body.new_name = form.name;
        try {
            const value = await jsonRequest('/api/channels/preview', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
            if (!object(value) || value.op !== body.op || value.channel !== body.channel || !validCounts(value.counts)
                    || !/^[a-f0-9]{64}$/.test(value.preview_token) || !Array.isArray(value.blockers) || !Array.isArray(value.queued_dispatch_ids)) throw new Error('Invalid preview.');
            if (current !== form || form.closed || body.channel !== target(form) || (body.new_name && body.new_name !== form.name)) return;
            form.preview = value;
        } catch (error) { form.preview = null; report(form, errorText(error)); }
        finally { form.busy = false; if (current === form && !form.closed) renderManager(form); }
    }
    async function mutate(form, repair = false) {
        if (mutation || form.busy || !ready) return;
        const intent = catalog?.intent;
        if (repair ? !intent || !form.repairConfirmed : !form.preview || form.confirmation !== target(form) || partialContents(target(form))) return;
        const requestId = repair ? intent.request_id : (form.requestId ||= crypto.randomUUID().replaceAll('-', ''));
        const body = repair ? {request_id: requestId} : {op: form.op, channel: target(form),
            request_id: requestId, confirmation: form.confirmation, preview_token: form.preview.preview_token};
        if (!repair && form.op === 'rename') body.new_name = form.name;
        mutation = {requestId}; form.busy = true; form.error = ''; renderManager(form);
        try {
            const value = await jsonRequest('/api/channels/' + (repair ? 'retry' : 'apply'), {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
            if (!object(value) || value.ok !== true) throw new Error('Invalid result.');
            if (value.op === 'rename') pendingEvents.push({type: 'channel_renamed', old_name: value.old_name, new_name: value.new_name, revision: value.revision});
            if (value.op === 'delete') pendingEvents.push({type: 'channel_deleted', channel: value.channel, revision: value.revision});
            await refresh();
            form.warning = value.projection_warning || value.projection_repair_error || 'Channel change confirmed.';
            form.preview = null;
            if (value.op === 'rename') form.channel = value.new_name;
        } catch (error) {
            form.preview = null; report(form, errorText(error));
            try { await refresh(); } catch (_) { /* Closed writes and visible catalog error. */ }
        } finally { mutation = null; form.busy = false; if (current === form && !form.closed) renderManager(form); }
    }
    async function readRetained(form) {
        form.readController?.abort(); form.readController = new AbortController();
        const channel = form.channel, mine = ++form.readEpoch;
        try {
            const value = await jsonRequest('/api/channels/retained?channel=' + encodeURIComponent(channel), {}, form.readController);
            if (current !== form || form.closed || form.channel !== channel || form.op !== 'view' || mine !== form.readEpoch) return;
            if (!object(value) || value.channel !== channel || !object(value.errors) || !object(value.counts) || !object(value.truncated)) throw new Error('Invalid retained records.');
            for (const owner of ['jobs', 'sessions', 'schedules', 'uploads']) if (!(value[owner] === null && value.errors[owner]) && (!Array.isArray(value[owner]) || value[owner].length > 100)) throw new Error('Invalid retained rows.');
            form.retained = value; renderManager(form);
        } catch (error) { if (!form.closed && form.channel === channel && form.op === 'view' && mine === form.readEpoch) report(form, errorText(error)); }
    }
    function renderRetained(form, detail) {
        detail.appendChild(node('h3', 'Retained records: # ' + form.channel));
        if (!form.retained) { detail.appendChild(node('p', 'Loading retained records.')); return; }
        const value = form.retained;
        for (const owner of ['jobs', 'sessions', 'schedules', 'uploads', 'summary']) if (value.errors[owner]) detail.appendChild(node('p', `${owner}: Saved records are held. Repair storage and reload.`, 'channel-manager-status'));
        if (value.summary) { detail.append(node('h4', 'Summary'), node('pre', value.summary.text)); }
        else if (!value.errors.summary) detail.appendChild(node('p', 'No saved summary for this channel.'));
        for (const owner of ['jobs', 'sessions', 'schedules', 'uploads']) {
            const label = owner === 'sessions' ? 'Reviews' : owner === 'uploads' ? 'Messages with attachments' : owner[0].toUpperCase() + owner.slice(1);
            detail.appendChild(node('h4', label));
            if (value[owner] === null) continue;
            detail.appendChild(node('p', `${value.counts[owner]} ${label.toLowerCase()}${value.truncated[owner] ? '; showing the first 100' : ''}.`));
            for (const entry of value[owner]) {
                const line = node('div', undefined, 'channel-retained-row');
                if (owner === 'uploads') {
                    line.appendChild(node('p', `Message ${entry.message_id}, ${entry.message_uid}`));
                    for (const item of entry.attachments || []) line.appendChild(node('p', typeof item.name === 'string' ? item.name : 'Attachment reference'));
                    for (const link of entry.safe_links || []) if (typeof link.url === 'string' && /^\/uploads\/[A-Za-z0-9][A-Za-z0-9._-]{0,254}$/.test(link.url)) {
                        const anchor = node('a', link.name || 'Open retained file'); anchor.href = link.url; anchor.target = '_blank'; anchor.rel = 'noopener'; line.appendChild(anchor);
                    }
                } else {
                    line.appendChild(node('p', owner === 'jobs' ? `${entry.title || 'Untitled job'} (${entry.status || 'unknown'})` : owner === 'sessions' ? `Review ${entry.id} (${entry.state || 'unknown'})` : `Schedule ${entry.id}: ${entry.active ? 'enabled' : 'inactive'}`));
                    if (owner !== 'schedules') line.appendChild(button(owner === 'jobs' ? 'Read conversation' : 'Read source and journal', () => expandRecord(form, line, owner, entry.id)));
                }
                detail.appendChild(line);
            }
        }
    }
    async function expandRecord(form, line, owner, identifier) {
        try {
            const value = await jsonRequest(owner === 'jobs' ? `/api/jobs/${identifier}/messages` : `/api/sessions/${identifier}/stop-status`);
            if (form !== current || form.closed || !line.isConnected) return;
            if (owner === 'jobs') for (const item of Array.isArray(value) ? value : value.messages || []) line.appendChild(node('pre', item.text || ''));
            else {
                line.append(node('h4', 'Frozen source'), node('pre', value.input_snapshot?.text || ''));
                for (const event of value.admitted_events || []) line.append(node('h4', event.kind || 'Journal event'), node('pre', event.content || ''));
            }
        } catch (error) { report(form, errorText(error)); }
    }
    return {refresh, state, canWrite, ownerAvailable, guardWrite, openManage, handleEvent, renderPolicy};
})();
