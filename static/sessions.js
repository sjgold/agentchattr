/**
 * sessions.js -- Session orchestration UI module
 *
 * Extracted from chat.js (PR 2 of monolith breakup).
 * Depends on core.js (Hub) and store.js (Store) loaded first.
 *
 * Owns all session state, rendering, and interaction logic.
 * Subscribes to Hub for WS events and watches Store for channel changes.
 *
 * Reads from window: activeChannel, username, SESSION_TOKEN, ws,
 *                    agentConfig, escapeHtml, switchChannel
 */

// ---------------------------------------------------------------------------
// Session state (moved from chat.js globals)
// ---------------------------------------------------------------------------

let activeSession = null;
let sessionTemplates = [];
let sessionCapacity = null;
let activeSessionsByChannel = {};
let sessionIndicatorTargetChannel = null;
let stopStatusBusy = false;
let recoveryStatusBusy = false;
const recoveryRequests = new Map();
const recoveryWaitDrafts = new Map();
const recoveryOffers = new Map();

// ---------------------------------------------------------------------------
// Message Renderers
// ---------------------------------------------------------------------------
// Register session message renderers so appendMessage in chat.js can
// delegate to us via window._messageRenderers[msg.type](el, msg).

if (!window._messageRenderers) window._messageRenderers = {};

function _renderSessionDraftResolvedCard(label, detail = '') {
    return `
        <div class="proposal-card session-proposal-card proposal-resolved">
            <div class="proposal-header">
                <span class="proposal-pill">Session Proposal</span>
            </div>
            <div class="proposal-title">${window.escapeHtml(label)}</div>
            ${detail ? `<div class="proposal-body session-proposal-desc">${window.escapeHtml(detail)}</div>` : ''}
        </div>`;
}

window._messageRenderers['session_start'] = function (el, msg) {
    el.classList.add('system-msg', 'session-banner', 'session-banner-start');
    const goal = msg.metadata?.goal ? ` -- ${window.escapeHtml(msg.metadata.goal)}` : '';
    el.innerHTML = `<span class="session-banner-icon">&#9654;</span> <strong>${window.escapeHtml(msg.text)}</strong>${goal}`;
};

window._messageRenderers['session_end'] = function (el, msg) {
    el.classList.add('system-msg', 'session-banner', 'session-banner-end');
    const outputId = msg.metadata?.output_message_id;
    const jumpLink = outputId ? ` <span class="session-output-link" onclick="scrollToSessionOutput(${outputId})">View output</span>` : '';
    el.innerHTML = `<span class="session-banner-icon">&#9632;</span> <strong>${window.escapeHtml(msg.text)}</strong>${jumpLink}`;
};

window._messageRenderers['session_phase'] = function (el, msg) {
    el.classList.add('system-msg', 'session-banner', 'session-banner-phase');
    el.innerHTML = `<span class="session-banner-icon">&#9656;</span> ${window.escapeHtml(msg.text)}`;
};

window._messageRenderers['quarantine'] = function (el, msg) {
    const label = document.createElement('strong');
    label.textContent = 'Quarantined output, no work triggered';
    const content = document.createElement('pre');
    content.className = 'session-quarantine-content';
    content.textContent = msg.text;
    el.replaceChildren(label, content);
};

window._messageRenderers['session_draft'] = function (el, msg) {
    el.classList.add('system-msg', 'session-draft-card');
    const meta = msg.metadata || {};
    const valid = meta.valid;
    const errors = meta.errors || [];
    const tmpl = meta.template || {};
    const draftId = meta.draft_id || '';
    const proposedBy = meta.proposed_by || '?';
    const revision = meta.revision || 1;
    const proposedByColor = window.getColor ? window.getColor(proposedBy) : 'var(--text-dim)';

    // Check if superseded by a newer revision
    const isSuperseded = _isSupersededDraft(draftId, revision);

    // Always store draft identity for supersession lookups
    el.dataset.draftId = draftId;
    el.dataset.draftRevision = revision;

    if (isSuperseded) {
        el.classList.add('session-draft-superseded');
        el.innerHTML = _renderSessionDraftResolvedCard('Superseded draft', `Replaced by revision ${revision}.`);
    } else if (!valid) {
        el.classList.add('session-draft-invalid');
        const errorList = errors.map(e => `<li>${window.escapeHtml(e)}</li>`).join('');
        el.innerHTML = `
            <div class="proposal-card session-proposal-card session-proposal-invalid">
                <div class="proposal-header">
                    <span class="proposal-pill">Session Proposal</span>
                    <span class="proposal-author" style="color: ${proposedByColor}">${window.escapeHtml(proposedBy)}</span>
                </div>
                <div class="proposal-title">Invalid session draft</div>
                <div class="proposal-body session-proposal-desc">This draft needs changes before it can be run or saved.</div>
                ${capacitySummary()}
                <ul class="session-draft-errors">${errorList}</ul>
                <details class="session-invalid-design">
                    <summary>Read the unchanged proposal</summary>
                    <pre>${window.escapeHtml(JSON.stringify(tmpl, null, 2))}</pre>
                </details>
                <div class="proposal-actions">
                    <button class="proposal-request-changes" onclick="recheckSessionDraft(${msg.id}, this)">Check current limits</button>
                    <button class="proposal-request-changes" onclick="requestDraftChanges('${window.escapeHtml(draftId)}', '${window.escapeHtml(proposedBy)}', ${msg.id})">Request Changes</button>
                    <button class="proposal-dismiss" onclick="dismissDraft(${msg.id})">Dismiss</button>
                </div>
            </div>`;
    } else {
        const phases = tmpl.phases || [];
        const phasesDetailHtml = phases.map((p, i) => {
            const parts = (p.participants || [])
                .map(r => `<span class="session-draft-phase-participant-pill">${window.escapeHtml(r)}</span>`)
                .join('');
            const promptText = p.prompt ? window.escapeHtml(p.prompt) : '';
            return `<div class="session-draft-phase-detail">
                <span class="session-draft-phase-num">${i + 1}</span>
                <div class="session-draft-phase-copy">
                    <div class="session-draft-phase-top">
                        <span class="session-draft-phase-name">${window.escapeHtml(p.name)}</span>
                        ${parts ? `<span class="session-draft-phase-participants">${parts}</span>` : ''}
                    </div>
                    ${promptText ? `<div class="session-draft-phase-prompt">${promptText}</div>` : ''}
                </div>
            </div>`;
        }).join('');
        const metaLabel = revision > 1 ? `rev ${revision}` : '';
        el.dataset.draftTemplate = JSON.stringify(tmpl);
        el.dataset.draftMsgId = msg.id;
        el.innerHTML = `
            <div class="proposal-card session-proposal-card">
                <div class="proposal-header">
                    <span class="proposal-pill">Session Proposal</span>
                    <span class="proposal-author" style="color: ${proposedByColor}">${window.escapeHtml(proposedBy)}</span>
                    ${metaLabel ? `<span class="session-draft-meta">${metaLabel}</span>` : ''}
                </div>
                <div class="proposal-title">${window.escapeHtml(tmpl.name || '?')}</div>
                ${capacitySummary()}
                ${tmpl.description ? `<div class="proposal-body session-proposal-desc">${window.escapeHtml(tmpl.description)}</div>` : ''}
                <div class="session-draft-details">
                    ${phasesDetailHtml}
                </div>
                <div class="proposal-actions">
                    <button class="proposal-accept" onclick="runDraft(${msg.id})">Run</button>
                    <button class="proposal-request-changes session-draft-btn-save" onclick="saveDraft(${msg.id}, this)">Save Template</button>
                    <button class="proposal-request-changes" onclick="requestDraftChanges('${window.escapeHtml(draftId)}', '${window.escapeHtml(proposedBy)}', ${msg.id})">Request Changes</button>
                    <button class="proposal-dismiss" onclick="dismissDraft(${msg.id})">Dismiss</button>
                </div>
            </div>`;
        // Supersede older revisions of the same draft
        if (revision > 1) {
            setTimeout(() => _supersedePreviousDrafts(draftId, revision), 0);
        }
    }
};

// ---------------------------------------------------------------------------
// Session API functions
// ---------------------------------------------------------------------------

async function fetchSessionTemplates() {
    await fetchSessionCapacity();
    try {
        const res = await fetch('/api/sessions/templates', { headers: { 'X-Session-Token': window.SESSION_TOKEN } });
        if (res.ok) sessionTemplates = await res.json();
    } catch (e) {
        console.warn('Failed to fetch session templates', e);
    }
}

async function recheckSessionDraft(messageId, button) {
    const card = button.closest('.session-draft-card');
    if (!card) return;
    button.disabled = true;
    try {
        const response = await fetch('/api/sessions/validate-draft', {
            method: 'POST', headers: {'X-Session-Token': window.SESSION_TOKEN, 'Content-Type': 'application/json'},
            body: JSON.stringify({message_id: messageId}),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Draft could not be checked');
        sessionCapacity = result.capacity;
        card.classList.remove('session-draft-invalid');
        window._messageRenderers.session_draft(card, {id: messageId, metadata: {
            draft_id: card.dataset.draftId, revision: Number(card.dataset.draftRevision),
            proposed_by: card.querySelector('.proposal-author')?.textContent || 'coordinator',
            template: result.template, valid: result.valid, errors: result.errors,
        }});
    } catch (error) {
        button.textContent = error.message + '. Check again';
    } finally { if (button.isConnected) button.disabled = false; }
}

function capacitySummary() {
    return `<p class="session-capacity-note" data-session-capacity aria-live="polite">${window.escapeHtml(
        sessionCapacity?.limits_text || 'Loading shared design limits…')}</p>`;
}

async function fetchSessionCapacity() {
    try {
        const response = await fetch('/api/session-capacity', {headers: {'X-Session-Token': window.SESSION_TOKEN}});
        if (!response.ok) throw new Error('Capacity policy unavailable');
        sessionCapacity = await response.json();
        document.querySelectorAll('[data-session-capacity]').forEach(node => {
            node.textContent = sessionCapacity.limits_text;
        });
    } catch (_) {
        document.querySelectorAll('[data-session-capacity]').forEach(node => {
            node.textContent = 'Design limits could not load. Reopen this editor to retry. Start still validates the complete design on the server.';
        });
    }
}

async function fetchAllActiveSessions() {
    try {
        const res = await fetch('/api/sessions/active-all', { headers: { 'X-Session-Token': window.SESSION_TOKEN } });
        if (res.ok) {
            const sessions = await res.json();
            activeSessionsByChannel = {};
            (sessions || []).forEach(session => {
                const channel = session?.channel || 'general';
                activeSessionsByChannel[channel] = session;
            });
            activeSession = activeSessionsByChannel[window.activeChannel] || null;
            updateSessionBar();
        }
    } catch (e) {
        console.warn('Failed to fetch active sessions', e);
    }
}

async function fetchActiveSession(channelName) {
    if (channelName === undefined) channelName = window.activeChannel;
    try {
        const res = await fetch(`/api/sessions/active?channel=${encodeURIComponent(channelName)}`, { headers: { 'X-Session-Token': window.SESSION_TOKEN } });
        if (res.ok) {
            const data = await res.json();
            if (data) activeSessionsByChannel[channelName] = data;
            else delete activeSessionsByChannel[channelName];
            if (channelName !== window.activeChannel) return;
            activeSession = data;
            updateSessionBar();
        }
    } catch (e) {
        console.warn('Failed to fetch active session', e);
    }
}

// ---------------------------------------------------------------------------
// WebSocket event handler
// ---------------------------------------------------------------------------

function handleSessionEvent(action, session) {
    if (!session) return;
    if (session.state === 'complete' && !session.projection_pending) action = 'complete';
    if (session.state === 'interrupted') action = session.restart_recovery && !session.stop_id ? 'update' : 'interrupt';
    const channel = session.channel || 'general';
    // A delayed parent Stop update must not replace its newer prepared child.
    if (activeSessionsByChannel[channel]?.id > session.id) return;
    if (activeSessionsByChannel[channel]?.id === session.id &&
        activeSessionsByChannel[channel].updated_at > session.updated_at) return;

    if (action === 'create' || action === 'update') {
        activeSessionsByChannel[channel] = session;
        if (channel === window.activeChannel) {
            activeSession = session;
        }
    } else if (action === 'complete' || action === 'interrupt') {
        delete activeSessionsByChannel[channel];
        if (channel === window.activeChannel) {
            activeSession = null;
        }
        // Highlight the output message
        if (channel === window.activeChannel && action === 'complete' && session.output_message_id) {
            highlightSessionOutput(session.output_message_id);
        }
    }
    updateSessionBar();
}

// ---------------------------------------------------------------------------
// Session bar
// ---------------------------------------------------------------------------

function updateSessionBar() {
    const bar = document.getElementById('session-bar');
    if (!bar) return;
    renderSessionTurnControls(bar);
    renderRestartControls(bar);
    const templateEl = bar.querySelector('.session-template');
    const phaseEl = bar.querySelector('.session-phase');
    const waitingEl = bar.querySelector('.session-waiting');
    const endBtn = document.getElementById('session-end-btn');
    const jumpBtn = document.getElementById('session-jump-btn');

    if (!activeSession) {
        const otherSessions = Object.values(activeSessionsByChannel)
            .filter(session => session && (session.channel || 'general') !== window.activeChannel);

        if (!otherSessions.length) {
            clearEndSessionConfirm();
            sessionIndicatorTargetChannel = null;
            bar.classList.add('hidden');
            bar.classList.remove('session-elsewhere');
            return;
        }

        const target = otherSessions[0];
        const extraCount = otherSessions.length - 1;
        const targetChannel = target.channel || 'general';
        const targetName = target.template_name || target.template_id || 'Session';
        const channelListText = otherSessions.map(session => `#${session.channel || 'general'}`).join(', ');

        sessionIndicatorTargetChannel = targetChannel;
        clearEndSessionConfirm();
        bar.classList.remove('hidden');
        bar.classList.add('session-elsewhere');
        templateEl.textContent = otherSessions.length === 1
            ? `Session active in #${targetChannel}`
            : `${otherSessions.length} sessions active elsewhere`;
        phaseEl.textContent = otherSessions.length === 1
            ? targetName
            : channelListText;
        waitingEl.style.display = 'none';
        if (jumpBtn) {
            jumpBtn.textContent = extraCount > 0
                ? `Go to #${targetChannel} (+${extraCount})`
                : `Go to #${targetChannel}`;
            jumpBtn.classList.remove('hidden');
            jumpBtn.style.display = '';
        }
        if (endBtn) endBtn.style.display = 'none';
        return;
    }

    bar.classList.remove('hidden');
    bar.classList.remove('session-elsewhere');
    sessionIndicatorTargetChannel = null;
    const s = activeSession;
    const templateName = s.template_name || s.template_id || '?';
    const phaseName = s.phase_name || `Phase ${(s.current_phase || 0) + 1}`;
    const totalPhases = s.total_phases || '?';
    const phaseNum = (s.current_phase || 0) + 1;

    templateEl.textContent = templateName;
    phaseEl.textContent = `${phaseName} (${phaseNum}/${totalPhases})`;
    if (jumpBtn) {
        jumpBtn.classList.add('hidden');
        jumpBtn.style.display = 'none';
    }
    if (endBtn) endBtn.style.display = s.stop_id ? 'none' : '';

    const waitingAgent = s.current_agent || s.waiting_on;
    if (s.state === 'prepared' && !s.stop_id) {
        waitingEl.textContent = 'Corrected source saved, not started';
        waitingEl.style.display = '';
    } else if (s.stop_id) {
        waitingEl.textContent = s.state === 'stopped' ? 'Stopped locally' : s.state === 'unresolved' ? 'Cancellation unresolved' : 'Stopping';
        waitingEl.style.display = '';
    } else if (s.state === 'retrying') {
        waitingEl.textContent = 'Retry preparing, previous attempt retired';
        waitingEl.style.display = '';
    } else if (s.state === 'stalled') {
        waitingEl.textContent = 'Turn needs attention';
        waitingEl.style.display = '';
    } else if (s.state === 'interrupted' && s.restart_recovery) {
        waitingEl.textContent = 'Interrupted after server restart';
        waitingEl.style.display = '';
    } else if (s.legacy) {
        waitingEl.textContent = 'Legacy run, explicit restart required';
        waitingEl.style.display = '';
    } else if (s.projection_pending) {
        waitingEl.textContent = 'Result saved, awaiting display';
        waitingEl.style.display = '';
    } else if (s.state === 'awaiting_input') {
        waitingEl.textContent = 'Waiting for your answer';
        waitingEl.style.display = '';
    } else if (s.state !== 'paused' && s.choice_message_id != null) {
        waitingEl.textContent = 'Waiting for your choice';
        waitingEl.style.display = '';
    } else if (s.state === 'waiting' && waitingAgent) {
        waitingEl.textContent = `Waiting for ${waitingAgent}`;
        waitingEl.style.display = '';
    } else if (s.state === 'paused') {
        waitingEl.textContent = 'Paused';
        waitingEl.style.display = '';
    } else {
        waitingEl.style.display = 'none';
    }
}

async function refreshStopStatus() {
    const s = activeSession;
    if (!s || (!s.stop_id && s.state !== 'prepared') || stopStatusBusy) return;
    stopStatusBusy = true;
    try {
        const response = await fetch(`/api/sessions/${s.id}/${s.stop_id ? 'stop-status' : 'restart-status'}`,
            {headers: {'X-Session-Token': window.SESSION_TOKEN}});
        const value = await response.json();
        if (!response.ok) throw new Error(value.error || 'Cancellation status unavailable');
        handleSessionEvent('update', value);
    } catch (error) {
        const note = document.querySelector('.session-stop-status-note');
        if (note) note.textContent = `${error.message}. Retrying status; no new review is dispatched.`;
    } finally {
        stopStatusBusy = false;
    }
}

setInterval(refreshStopStatus, 2000);

async function refreshRecoveryStatus() {
    const s = activeSession;
    if (!s || s.legacy || s.stop_id || !['waiting', 'stalled', 'retrying'].includes(s.state) || recoveryStatusBusy) return;
    recoveryStatusBusy = true;
    try { handleSessionEvent('update', await restartRequest(s.id, 'recovery-status')); }
    catch (error) {
        const note = document.querySelector('.session-recovery-status');
        if (note) note.textContent = `${error.message}. Your saved checkpoint remains in place.`;
    } finally { recoveryStatusBusy = false; }
}
setInterval(refreshRecoveryStatus, 1000);

const recoveryReasons = {
    restart_unverified: 'The server restarted; worker ownership is not yet verified',
    missing_ack: 'Delivery was not acknowledged', response_timeout: 'The response deadline passed',
    disconnected: 'The expected seat is disconnected', provider_timeout: 'The provider request timed out',
    http_error: 'The provider returned an HTTP error', provider_failure: 'The provider request failed',
    empty_completion: 'The provider returned no answer', malformed_session_response: 'The reply was not a valid final result or question',
    local_delivery_failure: 'The completed reply could not be delivered', transport_closed: 'Delivery is uncertain',
    process_crash: 'The request process exited unexpectedly', prepared_client_exit_unverified: 'Client exit has not been verified',
    preparation_confirmation_required: 'Confirm ending the failed prepared context before repair'
};

function renderRecoveryControls(panel, s) {
    const checkpoint = s.turn_recovery;
    const pending = s.pending_retry;
    const context = pending?.context;
    if (s.retry_offer) recoveryOffers.set(checkpoint.checkpoint_id, s.retry_offer);
    const offer = s.retry_offer || recoveryOffers.get(checkpoint.checkpoint_id);
    const key = `${s.id}:${s.state}:recovery:${checkpoint.checkpoint_id}:${pending ? pending.status + ':' + (context?.launch_attempt || '') : 'choices:' + (offer?.launch_attempt || '')}`;
    panel.hidden = false;
    if (panel.dataset.key !== key) {
        panel.dataset.key = key;
        panel.replaceChildren();
        const title = document.createElement('strong');
        title.textContent = s.state === 'interrupted' ? 'Review interrupted after server restart' :
            pending ? 'Retry preparing. Earlier accepted work is retained.' : 'This turn needs attention';
        const status = document.createElement('p');
        status.className = 'session-recovery-status';
        status.setAttribute('role', 'status');
        const evidence = document.createElement('p');
        evidence.className = 'session-recovery-evidence';
        const saved = document.createElement('p');
        const accepted = s.admitted_events?.filter(e => e.kind === 'final').length || 0;
        saved.textContent = `${accepted} accepted ${accepted === 1 ? 'result' : 'results'} retained. No durable saved answer is known for this failed attempt.`;
        const error = document.createElement('p');
        error.setAttribute('role', 'alert');
        panel.append(title, status, evidence, saved, error);
        const perform = async (action, body) => {
            panel.dataset.busy = 'true';
            panel.querySelectorAll('button').forEach(button => { button.disabled = true; });
            error.textContent = 'Saving your recovery choice…';
            try {
                handleSessionEvent('update', await restartRequest(s.id, action, body));
                error.textContent = '';
                await refreshRecoveryStatus();
            } catch (failure) { error.textContent = failure.message; }
            finally {
                delete panel.dataset.busy;
                panel.querySelectorAll('button').forEach(button => { button.disabled = button.dataset.unavailable === 'true'; });
            }
        };
        const confirmedAction = (label, attempt, description, submit) => {
            const open = document.createElement('button');
            open.textContent = label;
            const confirmation = document.createElement('div');
            confirmation.className = 'session-stop-termination';
            confirmation.hidden = true;
            const impact = document.createElement('p');
            impact.textContent = `${description} Owned launch ${attempt.slice(0, 8)}. Native login and history files are preserved.`;
            const yes = document.createElement('button');
            yes.textContent = 'Confirm termination and retry';
            const no = document.createElement('button');
            no.textContent = 'Keep context running';
            open.onclick = () => { confirmation.hidden = false; yes.focus(); confirmation.scrollIntoView({block: 'nearest', inline: 'nearest'}); };
            no.onclick = () => { confirmation.hidden = true; open.focus(); };
            yes.onclick = () => submit({confirm: true, launch_attempt: attempt});
            confirmation.append(impact, yes, no);
            panel.append(open, confirmation);
        };
        if (pending) {
            if (s.state === 'interrupted' && pending.status !== 'preparation_failed') {
                const resume = document.createElement('button');
                resume.textContent = 'Resume saved retry';
                resume.onclick = () => perform('retry', {
                    checkpoint_id: pending.checkpoint_id, attempt_id: pending.old_invocation.attempt_id,
                    request_id: pending.request_id, ...(pending.confirmation ? {confirmation: pending.confirmation} : {})});
                panel.appendChild(resume);
            }
            if (pending.status === 'preparation_failed') {
                const repair = confirmation => perform(context?.launch_attempt ? 'repair-retry' : 'retry', context?.launch_attempt ?
                    {request_id: pending.request_id, preparation_attempt: context.launch_attempt, ...(confirmation ? {confirmation} : {})} :
                    {checkpoint_id: pending.checkpoint_id, attempt_id: pending.old_invocation.attempt_id,
                        request_id: pending.request_id, ...(pending.confirmation ? {confirmation: pending.confirmation} : {})});
                if (context?.worker_alive) confirmedAction('Repair failed launch…', context.launch_attempt,
                    'This ends only the failed prepared context and prepares the same reserved turn again.', repair);
                else {
                    const button = document.createElement('button');
                    button.textContent = 'Repair saved retry preparation';
                    button.onclick = () => repair();
                    panel.appendChild(button);
                }
            }
        } else {
            const form = document.createElement('form');
            form.className = 'session-recovery-wait';
            const label = document.createElement('label');
            label.textContent = 'Wait another (seconds)';
            const input = document.createElement('input');
            input.id = 'session-wait-seconds';
            input.type = 'number'; input.min = '.1'; input.step = 'any'; input.required = true;
            input.value = recoveryWaitDrafts.get(checkpoint.checkpoint_id) || '300';
            input.oninput = () => recoveryWaitDrafts.set(checkpoint.checkpoint_id, input.value);
            label.htmlFor = input.id;
            const wait = document.createElement('button');
            wait.textContent = 'Wait longer'; wait.type = 'submit';
            form.append(label, input, wait);
            form.onsubmit = event => { event.preventDefault(); perform('wait', {
                checkpoint_id: checkpoint.checkpoint_id, attempt_id: checkpoint.attempt_id, extend_seconds: Number(input.value)}); };
            panel.appendChild(form);
            const retry = confirmation => {
                const fingerprint = JSON.stringify([checkpoint.checkpoint_id, confirmation || null]);
                if (!recoveryRequests.has(fingerprint)) recoveryRequests.set(fingerprint, crypto.randomUUID());
                return perform('retry', {checkpoint_id: checkpoint.checkpoint_id, attempt_id: checkpoint.attempt_id,
                    request_id: recoveryRequests.get(fingerprint), ...(confirmation ? {confirmation} : {})});
            };
            const role = s.active_invocation?.role;
            const cli = s.participant_bindings?.[role]?.launch_provenance?.effective.seat.adapter === 'cli';
            if (cli && offer?.state === 'confirmation_required') confirmedAction('Retry this CLI turn…', offer.launch_attempt,
                'This ends only this persistent CLI context and starts the same source and model in a new owned process. Other work on this seat blocks replacement.', retry);
            else {
                const button = document.createElement('button');
                button.textContent = cli && !offer ? 'Checking owned CLI launch…' : 'Retry this turn';
                button.dataset.unavailable = String(cli && (!offer || offer.state !== 'ready'));
                button.disabled = button.dataset.unavailable === 'true';
                button.onclick = () => retry();
                panel.appendChild(button);
                if (cli && !offer) refreshRecoveryStatus();
            }
            const note = document.createElement('p');
            note.textContent = 'Wait keeps this attempt alive without calling the model again. Retry replaces it and starts only this turn. Remote provider computation remains unverified.';
            panel.appendChild(note);
        }
    }
    const status = panel.querySelector('.session-recovery-status');
    const frozenSeat = s.participant_bindings?.[s.active_invocation?.role]?.launch_provenance?.effective?.seat;
    const seatLabel = window.agentConfig?.[s.current_agent]?.label || frozenSeat?.name || s.current_agent || s.waiting_on || 'Participant';
    const model = frozenSeat?.model;
    status.textContent = pending ? (context?.state === 'starting' ? 'Starting the owned retry context. No new turn is dispatched until readiness is confirmed.' :
        pending.status === 'awaiting_local_end' ? 'Waiting for proof that the old local invocation ended. No new prompt is sent yet.' :
        recoveryReasons[context?.reason] || 'Preparation needs attention. Its reserved turn and source are retained.') :
        `${seatLabel}${model ? ' (' + model + ')' : ''} · ${s.phase_name || 'Current phase'}: ${recoveryReasons[checkpoint.reason] || 'Turn stalled'}${checkpoint.http_status ? ' (HTTP ' + checkpoint.http_status + ')' : ''}.${checkpoint.status === 'waiting' ? ' Your wait extension is active.' : ''}`;
    const policy = s.active_invocation?.monitoring?.policy || s.recovery_policy || {};
    const receipt = checkpoint.last_event;
    const timing = s.active_invocation?.monitoring;
    const due = timing?.response_deadline || timing?.ack_deadline;
    panel.querySelector('.session-recovery-evidence').textContent = `Last receipt: ${receipt?.state || 'not acknowledged'}${receipt?.at ? ' at ' + new Date(receipt.at * 1000).toLocaleTimeString() : ''}. Delivery limit ${policy.ack_timeout}s; response limit ${policy.response_timeout}s.${pending ? ' New timing begins after preparation.' : due ? ' Due at ' + new Date(due * 1000).toLocaleTimeString() + '.' : ''} Heartbeats do not extend these limits.`;
}

function renderStopControls(panel, s) {
    panel.hidden = false;
    const key = JSON.stringify([s.id, s.state, s.cancellation_receipts, s.termination_offers, s.quarantined_events?.length]);
    if (panel.dataset.key === key) return;
    panel.dataset.key = key;
    panel.replaceChildren();
    const title = document.createElement('strong');
    title.textContent = s.state === 'stopped' ? 'Review stopped locally' :
        s.state === 'unresolved' ? 'Stop saved, local work is unresolved' : 'Stop saved, checking local work';
    const description = document.createElement('p');
    description.textContent = `No further work can start for this run. ${s.admitted_events?.length || 0} accepted results and the original source are retained.`;
    const note = document.createElement('p');
    note.className = 'session-stop-status-note';
    note.setAttribute('role', 'status');
    note.textContent = 'Remote provider computation and usage remain unverified. Local termination cannot retract contents already sent.';
    panel.append(title, description, note);
    const receipts = document.createElement('ul');
    for (const receipt of s.cancellation_receipts || []) {
        const row = document.createElement('li');
        const status = receipt.evidence?.status || receipt.state;
        const labels = {requested: 'Cancellation requested', delivered: 'Cancellation delivered',
            local_ended: 'Local invocation ended', unsupported: 'This CLI has no verified turn interrupt',
            unresolved: 'Local termination unresolved', cancelled: 'Pending work cancelled'};
        row.textContent = `${labels[status] || status}. Dispatch ${receipt.dispatch_id.slice(0, 8)}.`;
        receipts.appendChild(row);
    }
    panel.appendChild(receipts);
    for (const offer of s.termination_offers || []) {
        const action = document.createElement('div');
        action.className = 'session-stop-termination';
        const impact = document.createElement('p');
        impact.textContent = `${offer.seat_name}: ${offer.impact}`;
        const button = document.createElement('button');
        button.textContent = `Terminate ${offer.seat_name} context…`;
        const confirmation = document.createElement('div');
        confirmation.hidden = true;
        const explanation = document.createElement('p');
        explanation.textContent = 'Confirm ending this owned CLI process and its persistent context. Other seats stay running. This action cannot be undone.';
        const confirm = document.createElement('button');
        confirm.textContent = 'Confirm termination';
        const cancel = document.createElement('button');
        cancel.textContent = 'Keep seat running';
        const error = document.createElement('p');
        error.setAttribute('role', 'alert');
        button.onclick = () => { confirmation.hidden = false; confirm.focus(); };
        cancel.onclick = () => { confirmation.hidden = true; button.focus(); };
        confirm.onclick = async () => {
            confirm.disabled = true;
            cancel.disabled = true;
            error.textContent = 'Waiting for evidence that the owned process ended…';
            try {
                const response = await fetch(`/api/sessions/${s.id}/terminate-seat`, {
                    method: 'POST', headers: {'X-Session-Token': window.SESSION_TOKEN, 'Content-Type': 'application/json'},
                    body: JSON.stringify({dispatch_id: offer.dispatch_id, launch_attempt: offer.launch_attempt, confirm: true})});
                const value = await response.json();
                if (!response.ok) throw new Error(value.error || 'Termination could not be confirmed');
                handleSessionEvent('update', value);
            } catch (failure) {
                error.textContent = failure.message;
                confirm.disabled = false;
                cancel.disabled = false;
            }
        };
        confirmation.append(explanation, confirm, cancel, error);
        action.append(impact, button, confirmation);
        panel.appendChild(action);
    }
    const events = s.quarantined_events || [];
    if (events.length) {
        const details = document.createElement('details');
        const summary = document.createElement('summary');
        summary.textContent = `${events.length} quarantined outputs, excluded from results and routing`;
        details.appendChild(summary);
        for (const event of events) {
            const text = document.createElement('pre');
            text.textContent = (event.provenance === 'unverified_scope' ? 'Scope unverified. ' : '') + event.content;
            details.appendChild(text);
        }
        panel.appendChild(details);
    }
}

function renderSessionTurnControls(bar) {
    let panel = document.getElementById('session-turn-controls');
    if (!panel) {
        panel = document.createElement('section');
        panel.id = 'session-turn-controls';
        panel.className = 'session-turn-controls';
        bar.after(panel);
    }
    const s = activeSession;
    if (s?.stop_id) {
        renderStopControls(panel, s);
        return;
    }
    if (s?.turn_recovery && (s.state === 'retrying' || (s.state === 'interrupted' && s.pending_retry) ||
        (['stalled', 'waiting', 'interrupted'].includes(s.state) && ['stalled', 'waiting'].includes(s.turn_recovery.status) &&
         s.active_invocation?.attempt_id === s.turn_recovery.attempt_id))) {
        renderRecoveryControls(panel, s);
        return;
    }
    const invocation = s?.active_invocation;
    const mode = !s || s.legacy ? null : s.projection_pending ? 'recover-projection' :
        s.state === 'awaiting_input' ? 'continue' : s.state === 'paused' ? 'resume' :
        invocation?.human ? 'human-result' : null;
    panel.hidden = !mode;
    if (!mode) { panel.dataset.key = ''; return; }
    const key = `${s.id}:${mode}:${s.current_question?.event_id || invocation?.brief_id || ''}`;
    // Live receipt/status updates must not replace an answer being composed.
    if (panel.dataset.key === key) return;
    panel.dataset.key = key;
    panel.replaceChildren();
    const title = document.createElement('strong');
    const questionSeat = s.current_question?.asked_by;
    const questionLabel = document.getElementById(`status-${questionSeat}`)?.textContent.trim() || questionSeat;
    title.textContent = mode === 'continue' ? `Question from ${questionLabel}` :
        mode === 'human-result' ? 'Your turn' : mode === 'resume' ? 'Session paused' : 'Accepted result saved';
    panel.appendChild(title);
    const detail = document.createElement('p');
    detail.textContent = mode === 'continue' ? s.current_question.text : mode === 'human-result' ?
        'Submit your final result here to finish this turn. Chat stays available for discussion.' :
        mode === 'resume' ? 'Resume the current turn without restarting it.' :
        'The result is safely recorded. Retry its display before the next participant starts.';
    panel.appendChild(detail);
    if (mode === 'human-result') {
        const source = document.createElement('details');
        const summary = document.createElement('summary');
        summary.textContent = 'Read this turn’s brief and source';
        const content = document.createElement('pre');
        source.append(summary, content);
        source.addEventListener('toggle', async () => {
            if (!source.open || source.dataset.loaded) return;
            try {
                const response = await fetch(`/api/review-briefs/${encodeURIComponent(invocation.brief_id)}`,
                    {headers: {'X-Session-Token': window.SESSION_TOKEN}});
                const brief = await response.json();
                if (!response.ok) throw new Error(brief.error || 'Brief unavailable');
                content.textContent = `Role: ${brief.role}\nPhase: ${brief.phase.name}\n${brief.phase.prompt}\n\n${brief.goal}\n\nRules:\n${(brief.rules.rules || []).join('\n')}\n\nSource (untrusted text):\n${brief.source}`;
                if (brief.prior_results?.length) content.textContent += '\n\nEarlier accepted results:\n' +
                    brief.prior_results.map(result => `${result.sender}: ${result.text}`).join('\n\n');
                if (brief.continuation_context?.length) content.textContent += '\n\nOperator answers:\n' +
                    brief.continuation_context.map(context => `${context.question}\n${context.answer}`).join('\n\n');
                source.dataset.loaded = 'true';
            } catch (error) { content.textContent = error.message; }
        });
        panel.appendChild(source);
    }
    const form = document.createElement('form');
    let input;
    if (mode === 'continue' || mode === 'human-result') {
        const label = document.createElement('label');
        label.textContent = mode === 'continue' ? 'Your answer' : 'Your final result';
        input = document.createElement('textarea');
        input.id = 'session-turn-answer';
        input.rows = 3;
        input.required = true;
        label.htmlFor = input.id;
        form.append(label, input);
    }
    const error = document.createElement('p');
    error.setAttribute('role', 'alert');
    const submit = document.createElement('button');
    submit.type = 'submit';
    submit.textContent = mode === 'continue' ? 'Continue turn' : mode === 'human-result' ?
        'Submit final result' : mode === 'resume' ? 'Resume session' : 'Retry display';
    form.append(error, submit);
    form.onsubmit = async event => {
        event.preventDefault();
        submit.disabled = true;
        error.textContent = '';
        const body = mode === 'continue' ? {question_event_id: s.current_question.event_id, answer: input.value} :
            mode === 'human-result' ? {brief_id: invocation.brief_id, content: input.value,
                submitted_by: window.username || 'user'} : {};
        try {
            const response = await fetch(`/api/sessions/${s.id}/${mode}`, {method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-Session-Token': window.SESSION_TOKEN},
                body: JSON.stringify(body)});
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'Could not submit this turn');
            await fetchActiveSession();
        } catch (failure) { error.textContent = failure.message; }
        finally { submit.disabled = false; }
    };
    panel.appendChild(form);
}

function jumpToSessionChannel() {
    if (!sessionIndicatorTargetChannel || sessionIndicatorTargetChannel === window.activeChannel) return;
    window.switchChannel(sessionIndicatorTargetChannel);
}

// Correction drafts and request IDs survive receipt polling and channel switches.
const restartDrafts = new Map();
const restartLabels = {
    confirmation_required: 'Confirm replacement of this exact CLI launch below.',
    unsupported_clean_context: 'This adapter has no verified fresh-context contract. Select a supported managed seat.',
    unresolved_child_exit: 'The old client has not proved local exit. Resolve its Stop or select an independent seat.',
    context_unavailable: 'The retained seat is unavailable. Select a current managed replacement.',
    stale_launch_provenance: 'The original launch changed. Select a current managed replacement.',
    context_preparation_failed: 'Context preparation failed. Refresh or select a replacement; source is retained.',
    prepared_context_changed: 'The prepared launch changed. Select a replacement.',
    context_retry_needs_termination: 'The failed context is still running. Resolve its owned process before retrying.'
};

async function restartRequest(id, action, body) {
    const response = await fetch(`/api/sessions/${id}/${action}`, {
        method: body === undefined ? 'GET' : 'POST',
        headers: {'X-Session-Token': window.SESSION_TOKEN, 'Content-Type': 'application/json'},
        ...(body === undefined ? {} : {body: JSON.stringify(body)})});
    const value = await response.json();
    if (!response.ok) throw new Error(value.error || 'Corrected review could not be updated');
    return value;
}

function renderRestartControls(bar) {
    let panel = document.getElementById('session-restart-controls');
    if (!panel) {
        panel = document.createElement('section');
        panel.id = 'session-restart-controls';
        panel.className = 'session-turn-controls session-restart-controls';
        document.getElementById('session-turn-controls').after(panel);
    }
    const s = activeSession;
    const prepared = s?.state === 'prepared' && !s.stop_id;
    panel.hidden = !s || (!s.stop_id && !prepared) || !!s.legacy;
    if (panel.hidden) { panel.dataset.key = ''; return; }
    const key = `${s.id}:${prepared ? 'prepared' : 'stopped'}`;
    if (panel.dataset.key !== key) {
        panel.dataset.key = key;
        delete panel.dataset.dirty;
        panel.replaceChildren();
        buildRestartControls(panel, s, prepared);
    }
    if (!prepared) return;
    for (const row of panel.querySelectorAll('[data-context-role]')) {
        const context = s.preparation_contexts?.[row.dataset.contextRole];
        const status = row.querySelector('.session-context-status');
        status.textContent = !context ? 'Not prepared yet.' :
            context.state === 'ready' && context.clean_context ? `Ready, clean context confirmed${context.name ? ': ' + context.name : ''}.` :
            context.state === 'starting' ? 'Launching a fresh context. No review has started.' :
            restartLabels[context.reason] || `Context ${context.state}. Review remains held.`;
        const retry = row.querySelector('.session-context-retry');
        retry.hidden = !context?.launch_attempt || !context?.key || !['failed', 'stopped', 'action_required'].includes(context.state);
        const confirmation = row.querySelector('.session-context-confirm:not(.session-context-retry)');
        if (confirmation && !row.querySelector('select').value && context?.state === 'ready') confirmation.hidden = true;
    }
    const ready = Object.keys(s.participant_bindings || {}).every(role =>
        s.preparation_contexts?.[role]?.state === 'ready' && s.preparation_contexts[role].clean_context);
    const start = panel.querySelector('.session-restart-start');
    if (start && !start.dataset.busy) start.disabled = !ready || panel.dataset.dirty === 'true';
}

function buildRestartControls(panel, s, prepared) {
    const draft = restartDrafts.get(s.id) || {text: s.input_snapshot?.text || '', operations: new Map()};
    restartDrafts.set(s.id, draft);
    const section = document.createElement(prepared ? 'div' : 'details');
    const heading = document.createElement(prepared ? 'strong' : 'summary');
    heading.textContent = prepared ? 'Corrected source saved. Prepare, then start.' : 'Correct source and restart';
    section.appendChild(heading);
    const explanation = document.createElement('p');
    explanation.textContent = prepared ?
        `Replacement of review ${s.parent_session_id}. Its source, goal, design and rules are frozen. Old answers and continuation text are excluded.` :
        'Edit the source for a linked review. Goal, design, rules and roles are retained. Old source and answers stay readable in history.';
    section.appendChild(explanation);
    const source = document.createElement('details');
    const sourceHeading = document.createElement('summary');
    sourceHeading.textContent = prepared ? 'Preview frozen replacement source' : 'Read original source';
    const original = document.createElement('pre');
    original.textContent = s.input_snapshot?.text || '(No pasted source)';
    source.append(sourceHeading, original);
    section.appendChild(source);
    if (prepared) {
        const history = document.createElement('details');
        const historyTitle = document.createElement('summary');
        historyTitle.textContent = 'Read preserved original review';
        const content = document.createElement('pre');
        history.append(historyTitle, content);
        history.ontoggle = async () => {
            if (!history.open || history.dataset.loaded) return;
            try {
                const parent = await restartRequest(s.parent_session_id, 'restart-status');
                content.textContent = `Original source:\n${parent.input_snapshot?.text || ''}\n\nAccepted results:\n${(parent.admitted_events || []).filter(e => e.kind === 'final').map(e => e.content).join('\n\n')}\n\nOperator answers:\n${(parent.continuation_context || []).map(e => e.answer).join('\n\n')}`;
                history.dataset.loaded = 'true';
            } catch (failure) { content.textContent = failure.message; }
        };
        section.appendChild(history);
    }
    const form = document.createElement('form');
    form.onchange = () => {
        if (prepared) { panel.dataset.dirty = 'true'; renderRestartControls(document.getElementById('session-bar')); }
    };
    let input;
    if (!prepared) {
        const label = document.createElement('label');
        label.textContent = 'Corrected source';
        input = document.createElement('textarea');
        input.id = 'session-corrected-source';
        input.rows = 6;
        input.required = true;
        input.value = draft.text;
        input.oninput = () => { draft.text = input.value; };
        label.htmlFor = input.id;
        const hint = document.createElement('p');
        hint.textContent = 'Paste or edit the full replacement, up to 512 KiB of UTF-8 text. Preparing saves it without starting a review.';
        form.append(label, input, hint);
    }
    const roles = document.createElement('div');
    roles.textContent = 'Loading frozen role settings and available managed seats…';
    const error = document.createElement('p');
    error.setAttribute('role', 'alert');
    const submit = document.createElement('button');
    submit.type = 'submit';
    submit.textContent = prepared ? 'Prepare selected contexts' : 'Save corrected source and prepare';
    submit.disabled = true;
    form.append(roles, submit);
    section.appendChild(error);
    if (prepared) {
        const choices = document.createElement('details');
        const choicesTitle = document.createElement('summary');
        choicesTitle.textContent = 'Review or change role contexts';
        choices.open = !Object.keys(s.participant_bindings || {}).every(role =>
            s.preparation_contexts?.[role]?.state === 'ready' && s.preparation_contexts[role].clean_context);
        choices.append(choicesTitle, form);
        section.appendChild(choices);
    } else section.appendChild(form);
    panel.appendChild(section);
    const current = () => panel.dataset.key === `${s.id}:${prepared ? 'prepared' : 'stopped'}`;
    restartRequest(s.id, 'restart-options').then(options => {
        if (!current()) return;
        roles.replaceChildren();
        for (const role of options.roles) {
            const row = document.createElement('fieldset');
            row.dataset.contextRole = role.role;
            const legend = document.createElement('legend');
            legend.textContent = `${role.role}: ${role.name}`;
            const settings = document.createElement('p');
            settings.textContent = role.kind === 'human' ? 'Operator role, no client restart.' : !role.adapter ?
                'Original launch settings are unavailable. Explicitly select a current managed replacement.' :
                `${role.adapter || 'Unknown launch'} · ${role.model || 'Provider default'}${role.reasoning ? ' · ' + role.reasoning : ''}. Frozen launch settings retained.`;
            row.append(legend, settings);
            if (role.kind !== 'human') {
                const label = document.createElement('label');
                label.textContent = 'Seat for this role';
                const select = document.createElement('select');
                select.id = `restart-seat-${s.id}-${roles.children.length}`;
                label.htmlFor = select.id;
                select.add(new Option('Retain frozen seat settings', ''));
                for (const candidate of options.candidates) {
                    select.add(new Option(`${candidate.name} · ${candidate.adapter} · ${candidate.model || 'Provider default'}${candidate.fresh_context_supported ? '' : ' · fresh context unsupported'}`, candidate.identity_id));
                }
                const confirmLabel = document.createElement('label');
                confirmLabel.className = 'session-context-confirm';
                const confirm = document.createElement('input');
                confirm.type = 'checkbox';
                const impact = document.createElement('span');
                const updateImpact = () => {
                    confirm.checked = false;
                    const chosen = options.candidates.find(c => c.identity_id === select.value) || role;
                    confirmLabel.hidden = chosen.adapter !== 'cli' || !chosen.launch_attempt;
                    confirm.dataset.attempt = chosen.launch_attempt || '';
                    impact.textContent = `Confirm ending ${chosen.name || role.name}'s owned CLI launch ${chosen.launch_attempt?.slice(0, 8) || ''} and replacing its persistent context. Native login and history files are preserved.`;
                };
                select.onchange = updateImpact;
                updateImpact();
                confirmLabel.append(confirm, impact);
                row.append(label, select, confirmLabel);
            }
            const status = document.createElement('p');
            status.className = 'session-context-status';
            const retryLabel = document.createElement('label');
            retryLabel.className = 'session-context-confirm session-context-retry';
            retryLabel.hidden = true;
            const retry = document.createElement('input');
            retry.type = 'checkbox';
            retryLabel.append(retry, 'Retry this failed preparation with a new owned context.');
            row.append(status, retryLabel);
            roles.appendChild(row);
        }
        submit.disabled = false;
        renderRestartControls(document.getElementById('session-bar'));
    }).catch(failure => { if (current()) roles.textContent = failure.message + '. Reopen this channel to reload choices.'; });
    form.onsubmit = async event => {
        event.preventDefault();
        error.textContent = '';
        if (input && new TextEncoder().encode(input.value).length > 512 * 1024) {
            error.textContent = 'Replacement exceeds 512 KiB. Your draft is retained for editing.';
            return;
        }
        const replacements = {}, confirmations = {}, retry_attempts = {};
        for (const row of roles.querySelectorAll('[data-context-role]')) {
            const role = row.dataset.contextRole;
            const select = row.querySelector('select');
            if (select?.value) replacements[role] = select.value;
            const confirm = row.querySelector('.session-context-confirm input');
            if (confirm?.checked) confirmations[role] = {confirm: true, launch_attempt: confirm.dataset.attempt};
            const context = activeSession?.id === s.id ? activeSession.preparation_contexts?.[role] : null;
            if (row.querySelector('.session-context-retry input').checked && context?.launch_attempt) retry_attempts[role] = context.launch_attempt;
        }
        const body = prepared ? {replacements, confirmations, retry_attempts} : {input_text: input.value, replacements, confirmations};
        const fingerprint = JSON.stringify(body);
        // Repeating a failed HTTP request reuses the exact persisted intent.
        if (!draft.operations.has(fingerprint)) draft.operations.set(fingerprint, crypto.randomUUID());
        body[prepared ? 'context_request_id' : 'request_id'] = draft.operations.get(fingerprint);
        submit.disabled = true;
        error.textContent = 'Saving preparation. No review is dispatched…';
        try {
            const value = await restartRequest(s.id, prepared ? 'prepare-contexts' : 'correct-and-restart', body);
            error.textContent = '';
            delete panel.dataset.dirty;
            handleSessionEvent('update', value);
        } catch (failure) { error.textContent = failure.message; }
        finally { submit.disabled = false; }
    };
    if (prepared) {
        const start = document.createElement('button');
        start.className = 'session-restart-start';
        start.textContent = 'Start corrected review';
        start.disabled = true;
        start.onclick = async () => {
            if (panel.dataset.dirty === 'true') { error.textContent = 'Prepare the selected role changes before starting.'; return; }
            start.disabled = true;
            start.dataset.busy = 'true';
            try { handleSessionEvent('update', await restartRequest(s.id, 'activate-restart', {})); }
            catch (failure) { error.textContent = failure.message; }
            finally { delete start.dataset.busy; renderRestartControls(document.getElementById('session-bar')); }
        };
        const note = document.createElement('p');
        note.textContent = 'Start stays unavailable until every role is ready and clean. The original run keeps its permanent Stop fence.';
        section.insertBefore(start, source);
        section.insertBefore(note, start);
    }
}

// ---------------------------------------------------------------------------
// Cast helpers
// ---------------------------------------------------------------------------

function _getAvailableAgents() {
    return Object.entries(window.agentConfig || {})
        .filter(([_, cfg]) => cfg.state === 'active')
        .map(([name]) => name);
}

function _autoCast(roles, agents) {
    const cast = {};
    let pool = [...agents];
    for (const role of roles) {
        if (!pool.length) pool = [...agents];
        if (!pool.length) return null;
        cast[role] = pool.shift();
    }
    return cast;
}

function syncSessionCastRole(selectEl) {
    const role = selectEl?.dataset?.role;
    if (!role) return;
    const value = selectEl.value;
    document.querySelectorAll('.session-cast-select').forEach(sel => {
        if (sel !== selectEl && sel.dataset.role === role) {
            sel.value = value;
        }
    });
}

function buildSessionCastEditor(tmpl, cast, assignees) {
    const phases = tmpl.phases || [];
    if (!phases.length) {
        return (tmpl.roles || []).map(role => {
            const assigned = cast ? cast[role] : '';
            const options = assignees.map(a =>
                `<option value="${window.escapeHtml(a)}" ${a === assigned ? 'selected' : ''}>${window.escapeHtml(a)}</option>`
            ).join('');
            return `<div class="session-cast-row">
                <span class="session-cast-role">${window.escapeHtml(role)}</span>
                <select class="session-cast-select" data-role="${window.escapeHtml(role)}" onchange="syncSessionCastRole(this)">${options}</select>
            </div>`;
        }).join('');
    }

    return phases.map((phase, idx) => {
        const participantRows = (phase.participants || []).map(role => {
            const assigned = cast ? cast[role] : '';
            const options = assignees.map(a =>
                `<option value="${window.escapeHtml(a)}" ${a === assigned ? 'selected' : ''}>${window.escapeHtml(a)}</option>`
            ).join('');
            return `<div class="session-cast-row">
                <span class="session-cast-role">${window.escapeHtml(role)}</span>
                <select class="session-cast-select" data-role="${window.escapeHtml(role)}" onchange="syncSessionCastRole(this)">${options}</select>
            </div>`;
        }).join('');

        return `<div class="session-cast-phase">
            <div class="session-cast-phase-head">
                <span class="session-cast-phase-num">${idx + 1}.</span>
                <span class="session-cast-phase-name">${window.escapeHtml(phase.name || `Phase ${idx + 1}`)}</span>
            </div>
            <div class="session-cast-phase-list">${participantRows}</div>
        </div>`;
    }).join('');
}

// ---------------------------------------------------------------------------
// Session launcher modal
// ---------------------------------------------------------------------------

function recoveryPolicyEditor() {
    return `<details class="session-recovery-settings">
        <summary>Turn timing</summary>
        <p>Server defaults apply unless you choose custom limits. Heartbeats never renew a delivery or response deadline. Human inputs and paused turns are excluded.</p>
        <label class="session-recovery-custom"><input id="session-custom-timing" type="checkbox" onchange="this.closest('details').querySelectorAll('input[type=number]').forEach(input => input.disabled = !this.checked)"> Use custom limits for this run</label>
        <div class="session-recovery-limits">
            <label>Delivery acknowledgement (seconds)<input type="number" id="session-ack-timeout" value="30" min="0.1" step="any" disabled></label>
            <label>Response (seconds)<input type="number" id="session-response-timeout" value="900" min="0.1" step="any" disabled></label>
            <label>Monitor interval (seconds)<input type="number" id="session-monitor-interval" value="1" min="0.1" step="any" disabled></label>
        </div>
    </details>`;
}

function selectedRecoveryPolicy() {
    if (!document.getElementById('session-custom-timing')?.checked) return undefined;
    const values = ['session-ack-timeout', 'session-response-timeout', 'session-monitor-interval']
        .map(id => Number(document.getElementById(id).value));
    if (values.some(value => !Number.isFinite(value) || value <= 0)) throw new Error('Turn timing requires positive, finite seconds. Your draft is retained.');
    return {ack_timeout: values[0], response_timeout: values[1], monitor_interval: values[2]};
}

function showSessionLauncher() {
    let existing = document.getElementById('session-launcher-modal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = 'session-launcher-modal';
    modal.className = 'session-launcher-overlay';
    modal.onclick = (e) => { if (e.target === modal) modal.remove(); };

    let templateOptions = sessionTemplates.map(t =>
        `<div class="session-tmpl-card" onclick="showCastPreview('${window.escapeHtml(t.id)}')" title="${window.escapeHtml(t.description || '')}">
            ${t.is_custom ? `<span class="session-tmpl-delete-wrap"><button class="session-tmpl-delete" onclick="toggleDeleteSessionTemplateConfirm(this, '${window.escapeHtml(t.id)}', event)" title="Delete custom template">Delete</button></span>` : ''}
            <div class="session-tmpl-name">${window.escapeHtml(t.name)}</div>
            <div class="session-tmpl-desc">${window.escapeHtml(t.description || '')}</div>
            <div class="session-tmpl-roles">${(t.roles || []).map(r => `<span class="session-role-pill">${window.escapeHtml(r)}</span>`).join(' ')}</div>
        </div>`
    ).join('');

    // "Design a session" card -- lets user describe what they want and pick an agent to draft it
    const agents = _getAvailableAgents();
    const agentOptions = agents.map(a =>
        `<option value="${window.escapeHtml(a)}">${window.escapeHtml(a)}</option>`
    ).join('');
    const designCard = `
        <div class="session-tmpl-card session-design-card">
            <div class="session-tmpl-name">+ Design a session</div>
            <div class="session-tmpl-desc">Ask an agent to draft a custom session template</div>
            <div class="session-design-row">
                <select id="session-design-agent" class="session-design-select">${agentOptions}</select>
                <input id="session-design-desc" type="text" class="session-design-input" placeholder="Describe the session you want..." />
                <button class="session-draft-btn run" onclick="sendDesignRequest()">Ask</button>
            </div>
        </div>`;

    modal.innerHTML = `
        <div class="session-launcher-dialog">
            <div class="session-launcher-header">
                <span>Start a Session</span>
                <button onclick="this.closest('.session-launcher-overlay').remove()">&times;</button>
            </div>
            <div class="session-launcher-goal">
                <input id="session-goal-input" type="text" placeholder="Goal (optional) -- what should this session achieve?" />
            </div>
            ${capacitySummary()}
            <div class="session-source-editor">
                <label for="session-source-input">Pasted review source (optional)</label>
                <textarea id="session-source-input" rows="6" placeholder="Paste the text every participant should review."></textarea>
                <p>Start freezes this source, the task brief, design and rules. Source is data, not tool instructions. Oversized input is rejected and stays here for editing.</p>
            </div>
            ${recoveryPolicyEditor()}
            <div id="session-step-templates">
                <div class="session-launcher-templates">${templateOptions}${designCard}</div>
            </div>
            <div id="session-step-cast" class="hidden"></div>
        </div>
    `;
    document.body.appendChild(modal);
    fetchSessionCapacity();
    document.getElementById('session-goal-input')?.focus();
}

async function sendDesignRequest() {
    const agent = document.getElementById('session-design-agent')?.value;
    const desc = document.getElementById('session-design-desc')?.value?.trim();
    if (!agent || !desc) return;
    const modal = document.getElementById('session-launcher-modal');
    if (modal) modal.remove();
    try {
        const res = await fetch('/api/sessions/request-draft', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Session-Token': window.SESSION_TOKEN },
            body: JSON.stringify({ agent: agent, description: desc, channel: window.activeChannel, sender: window.username }),
        });
        if (!res.ok) alert('Failed to send design request (HTTP ' + res.status + ')');
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

function showCastPreview(templateId) {
    const tmpl = sessionTemplates.find(t => t.id === templateId);
    if (!tmpl) return;

    const agents = _getAvailableAgents();
    const cast = _autoCast(tmpl.roles || [], agents);

    // All possible assignees: agents + "user" (self) + "none" (skip)
    const assignees = [...agents, window.username];

    const castStep = document.getElementById('session-step-cast');
    const tmplStep = document.getElementById('session-step-templates');
    if (!castStep || !tmplStep) return;

    tmplStep.classList.add('hidden');
    castStep.classList.remove('hidden');

    const roleRows = buildSessionCastEditor(tmpl, cast, assignees);

    castStep.innerHTML = `
        <div class="session-cast-header">
            <button class="session-back-btn" onclick="sessionCastBack()">&larr;</button>
            <span>${window.escapeHtml(tmpl.name)} -- Cast</span>
        </div>
        <div class="session-cast-list">${roleRows}</div>
        <button class="session-start-btn" onclick="launchSessionWithCast('${window.escapeHtml(templateId)}')">Start Session</button>
    `;
}

function sessionCastBack() {
    const castStep = document.getElementById('session-step-cast');
    const tmplStep = document.getElementById('session-step-templates');
    if (castStep) castStep.classList.add('hidden');
    if (tmplStep) tmplStep.classList.remove('hidden');
}

async function launchSessionWithCast(templateId) {
    const goalInput = document.getElementById('session-goal-input');
    const goal = goalInput ? goalInput.value.trim() : '';
    const inputText = document.getElementById('session-source-input')?.value || '';

    // Read cast from dropdowns
    const cast = {};
    document.querySelectorAll('#session-step-cast .session-cast-select').forEach(sel => {
        cast[sel.dataset.role] = sel.value;
    });

    const modal = document.getElementById('session-launcher-modal');

    try {
        const res = await fetch('/api/sessions/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Session-Token': window.SESSION_TOKEN },
            body: JSON.stringify({
                template_id: templateId,
                channel: window.activeChannel,
                cast: cast,
                goal: goal,
                input_text: inputText,
                recovery_policy: selectedRecoveryPolicy(),
                started_by: window.username,
            }),
        });
        if (!res.ok) {
            const data = await res.json();
            alert(data.error || 'Failed to start session');
        } else if (modal) {
            modal.remove();
        }
    } catch (e) {
        alert('Error starting session: ' + e.message);
    }
}

// ---------------------------------------------------------------------------
// End session
// ---------------------------------------------------------------------------

function clearEndSessionConfirm() {
    const btn = document.getElementById('session-end-btn');
    const confirm = document.getElementById('session-end-confirm');
    if (confirm) confirm.remove();
    if (btn) {
        btn.textContent = 'Stop review';
        btn.classList.remove('confirming');
    }
}

function toggleEndSessionConfirm(event) {
    event.stopPropagation();
    const btn = event.currentTarget;
    const controls = document.getElementById('session-end-controls');
    const existing = document.getElementById('session-end-confirm');
    if (existing) {
        clearEndSessionConfirm();
        return;
    }

    btn.textContent = 'Stop review?';
    btn.classList.add('confirming');

    const confirmWrap = document.createElement('span');
    confirmWrap.id = 'session-end-confirm';
    confirmWrap.className = 'session-inline-confirm';
    confirmWrap.innerHTML = `
        <button class="session-inline-confirm-yes ch-confirm-yes" title="Confirm Stop, keep accepted results">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3 8.5l3.5 3.5 6.5-7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
        <button class="session-inline-confirm-no ch-confirm-no" title="Cancel">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
        </button>
    `;
    (controls || btn.parentElement || btn).appendChild(confirmWrap);

    confirmWrap.querySelector('.session-inline-confirm-yes').onclick = async (e) => {
        e.stopPropagation();
        await endActiveSession();
    };
    confirmWrap.querySelector('.session-inline-confirm-no').onclick = (e) => {
        e.stopPropagation();
        clearEndSessionConfirm();
    };
}

async function endActiveSession() {
    if (!activeSession) return;

    try {
        const res = await fetch(`/api/sessions/${activeSession.id}/stop`, {
            method: 'POST',
            headers: { 'X-Session-Token': window.SESSION_TOKEN },
        });
        if (!res.ok) {
            const data = await res.json();
            alert(data.error || 'Stop could not be saved. Check local storage and try again.');
        } else {
            handleSessionEvent('update', await res.json());
            await refreshStopStatus();
        }
    } catch (e) {
        alert('Stop could not be confirmed: ' + e.message);
    } finally {
        clearEndSessionConfirm();
    }
}

// ---------------------------------------------------------------------------
// Session Drafts
// ---------------------------------------------------------------------------

function _isSupersededDraft(draftId, revision) {
    if (!draftId) return false;
    const allDrafts = document.querySelectorAll('.session-draft-card');
    for (const card of allDrafts) {
        if (card.dataset.draftId === draftId && parseInt(card.dataset.draftRevision || '0') > revision) {
            return true;
        }
    }
    return false;
}

function _supersedePreviousDrafts(draftId, currentRevision) {
    if (!draftId) return;
    const allDrafts = document.querySelectorAll('.session-draft-card');
    for (const card of allDrafts) {
        if (card.dataset.draftId === draftId && parseInt(card.dataset.draftRevision || '0') < currentRevision) {
            if (!card.classList.contains('session-draft-superseded')) {
                card.classList.add('session-draft-superseded');
                card.innerHTML = _renderSessionDraftResolvedCard(
                    `Superseded (rev ${card.dataset.draftRevision})`,
                    'A newer revision is now the active draft.'
                );
            }
        }
    }
}

function runDraft(msgId) {
    const el = document.querySelector(`.message[data-id="${msgId}"]`);
    if (!el || !el.dataset.draftTemplate) return;
    const tmpl = JSON.parse(el.dataset.draftTemplate);

    // Open the cast preview modal with draft context
    showDraftCastPreview(tmpl, msgId);
}

function showDraftCastPreview(tmpl, draftMsgId) {
    const agents = _getAvailableAgents();
    const cast = _autoCast(tmpl.roles || [], agents);
    const assignees = [...agents, window.username];

    let existing = document.getElementById('session-launcher-modal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = 'session-launcher-modal';
    modal.className = 'session-launcher-overlay';
    modal.onclick = (e) => { if (e.target === modal) modal.remove(); };

    const roleRows = buildSessionCastEditor(tmpl, cast, assignees);

    modal.innerHTML = `
        <div class="session-launcher-dialog">
            <div class="session-launcher-header">
                <span>${window.escapeHtml(tmpl.name || '?')} -- Cast</span>
                <button onclick="this.closest('.session-launcher-overlay').remove()">&times;</button>
            </div>
            <div class="session-launcher-goal">
                <input id="session-goal-input" type="text" placeholder="Goal (optional)" />
            </div>
            ${capacitySummary()}
            <div class="session-source-editor">
                <label for="session-source-input">Pasted review source (optional)</label>
                <textarea id="session-source-input" rows="6" placeholder="Paste the text every participant should review."></textarea>
                <p>Start freezes source, task, design and rules. Oversized input stays here for editing.</p>
            </div>
            ${recoveryPolicyEditor()}
            <div id="session-step-cast">
                <div class="session-cast-list">${roleRows}</div>
                <button class="session-start-btn" onclick="launchDraftSession(${draftMsgId})">Start Session</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    fetchSessionCapacity();
}

async function launchDraftSession(draftMsgId) {
    const goalInput = document.getElementById('session-goal-input');
    const goal = goalInput ? goalInput.value.trim() : '';
    const inputText = document.getElementById('session-source-input')?.value || '';

    const cast = {};
    document.querySelectorAll('#session-step-cast .session-cast-select').forEach(sel => {
        cast[sel.dataset.role] = sel.value;
    });

    const modal = document.getElementById('session-launcher-modal');

    try {
        const res = await fetch('/api/sessions/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Session-Token': window.SESSION_TOKEN },
            body: JSON.stringify({
                draft_message_id: draftMsgId,
                channel: window.activeChannel,
                cast: cast,
                goal: goal,
                input_text: inputText,
                recovery_policy: selectedRecoveryPolicy(),
                started_by: window.username,
            }),
        });
        if (!res.ok) {
            const data = await res.json();
            alert(data.error || 'Failed to start session from draft');
        } else if (modal) {
            modal.remove();
        }
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

async function saveDraft(msgId, btn) {
    try {
        const res = await fetch('/api/sessions/save-draft', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Session-Token': window.SESSION_TOKEN },
            body: JSON.stringify({ message_id: msgId }),
        });
        if (res.ok) {
            if (btn) {
                btn.textContent = 'Saved';
                btn.disabled = true;
                btn.classList.add('saved');
            }
            fetchSessionTemplates();
        } else {
            const data = await res.json();
            alert(data.error || 'Failed to save template');
        }
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

function clearSessionTemplateDeleteConfirms() {
    document.querySelectorAll('.session-tmpl-delete-confirm').forEach(el => el.remove());
    document.querySelectorAll('.session-tmpl-delete.confirming').forEach(btn => {
        btn.classList.remove('confirming');
        btn.textContent = 'Delete';
    });
}

function toggleDeleteSessionTemplateConfirm(btn, templateId, event) {
    if (event) event.stopPropagation();
    const wrap = btn.closest('.session-tmpl-delete-wrap');
    const existing = wrap?.querySelector('.session-tmpl-delete-confirm');
    if (existing) {
        clearSessionTemplateDeleteConfirms();
        return;
    }

    clearSessionTemplateDeleteConfirms();
    btn.classList.add('confirming');
    btn.textContent = 'Delete?';

    const confirmWrap = document.createElement('span');
    confirmWrap.className = 'session-tmpl-delete-confirm';
    confirmWrap.innerHTML = `
        <button class="session-inline-confirm-yes ch-confirm-yes" title="Confirm delete">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3 8.5l3.5 3.5 6.5-7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
        <button class="session-inline-confirm-no ch-confirm-no" title="Cancel">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
        </button>
    `;
    wrap.appendChild(confirmWrap);

    confirmWrap.querySelector('.session-inline-confirm-yes').onclick = async (e) => {
        e.stopPropagation();
        await deleteSessionTemplate(templateId);
    };
    confirmWrap.querySelector('.session-inline-confirm-no').onclick = (e) => {
        e.stopPropagation();
        clearSessionTemplateDeleteConfirms();
    };
}

async function deleteSessionTemplate(templateId) {
    try {
        const res = await fetch(`/api/sessions/templates/${encodeURIComponent(templateId)}`, {
            method: 'DELETE',
            headers: { 'X-Session-Token': window.SESSION_TOKEN },
        });
        if (res.ok) {
            await fetchSessionTemplates();
            showSessionLauncher();
        } else {
            const data = await res.json();
            alert(data.error || 'Failed to delete template');
        }
    } catch (e) {
        alert('Error: ' + e.message);
    } finally {
        clearSessionTemplateDeleteConfirms();
    }
}

function requestDraftChanges(draftId, proposedBy, msgId) {
    const el = document.querySelector(`.message[data-id="${msgId}"]`);
    if (!el) return;
    const actions = el.querySelector('.proposal-actions') || el.querySelector('.session-draft-actions');
    if (!actions) return;

    // Only allow one inline editor per draft card.
    const existingInputs = el.querySelectorAll('.draft-changes-input');
    if (existingInputs.length) {
        existingInputs.forEach((row, idx) => {
            if (idx > 0) row.remove();
        });
        existingInputs[0].querySelector('textarea')?.focus();
        return;
    }

    const inputRow = document.createElement('div');
    inputRow.className = 'draft-changes-input';
    inputRow.innerHTML = `
        <textarea class="draft-changes-textarea" rows="2" placeholder="What changes do you want?"></textarea>
        <div class="draft-changes-btns">
            <button class="session-draft-btn run" onclick="submitDraftChanges('${window.escapeHtml(draftId)}', '${window.escapeHtml(proposedBy)}', ${msgId})">Send</button>
            <button class="session-draft-btn dismiss" onclick="dismissDraftChanges(this)">Cancel</button>
        </div>
    `;
    actions.after(inputRow);
    const ta = inputRow.querySelector('textarea');
    ta.focus();
    ta.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submitDraftChanges(draftId, proposedBy, msgId);
        }
        if (e.key === 'Escape') inputRow.remove();
    });
}

function submitDraftChanges(draftId, proposedBy, msgId) {
    const el = document.querySelector(`.message[data-id="${msgId}"]`);
    if (!el) return;
    const inputRow = el.querySelector('.draft-changes-input');
    const ta = inputRow?.querySelector('textarea');
    const feedback = ta?.value?.trim();
    if (!feedback) return;

    const tmplJson = el.dataset.draftTemplate || '';
    const text = `@${proposedBy} Please revise session draft [${draftId}]: ${feedback}\n\nCurrent draft:\n\`\`\`session\n${tmplJson}\n\`\`\``;
    if (window.ws && window.ws.readyState === WebSocket.OPEN) {
        window.ws.send(JSON.stringify({
            type: 'message',
            text: text,
            sender: window.username,
            channel: window.activeChannel,
        }));
    } else {
        alert('Connection lost. Reconnect and try again.');
        return;
    }
    if (inputRow) inputRow.remove();
}

function dismissDraft(msgId) {
    fetch(`/api/messages/${msgId}/demote`, {
        method: 'POST',
        headers: { 'X-Session-Token': window.SESSION_TOKEN },
    }).then((res) => {
        if (!res.ok) alert('Failed to dismiss session proposal (HTTP ' + res.status + ')');
    }).catch((e) => {
        console.error('Failed to demote session draft:', e);
        alert('Failed to dismiss session proposal');
    });
}

function dismissDraftChanges(btn) {
    const row = btn.closest('.draft-changes-input');
    if (row) row.remove();
}

function highlightSessionOutput(messageId) {
    const el = document.querySelector(`.message[data-id="${messageId}"]`);
    if (el) el.classList.add('session-output');
}

function scrollToSessionOutput(messageId) {
    const el = document.querySelector(`.message[data-id="${messageId}"]`);
    if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.classList.add('session-output');
        el.classList.add('session-output-flash');
        setTimeout(() => el.classList.remove('session-output-flash'), 2000);
    }
}

// ---------------------------------------------------------------------------
// Hub subscription -- handle session WebSocket events
// ---------------------------------------------------------------------------

Hub.on('session', function (event) {
    handleSessionEvent(event.action, event.data);
});

Hub.on('channel_renamed', function (event) {
    // Migrate session cache key so Store watcher resolves the correct session
    if (activeSessionsByChannel[event.old_name]) {
        activeSessionsByChannel[event.new_name] = activeSessionsByChannel[event.old_name];
        delete activeSessionsByChannel[event.old_name];
    }
});

// ---------------------------------------------------------------------------
// Store integration -- react to channel changes
// ---------------------------------------------------------------------------

Store.watch('activeChannel', function (newChannel) {
    activeSession = activeSessionsByChannel[newChannel] || null;
    updateSessionBar();
    fetchActiveSession(newChannel);
});

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

function _sessionsInit() {
    fetchSessionTemplates();
    fetchAllActiveSessions();
    activeSession = null;
    updateSessionBar();
    fetchActiveSession();
}

// ---------------------------------------------------------------------------
// Window exports (for inline onclick handlers in generated HTML)
// ---------------------------------------------------------------------------

window.showSessionLauncher = showSessionLauncher;
window.runDraft = runDraft;
window.saveDraft = saveDraft;
window.dismissDraft = dismissDraft;
window.dismissDraftChanges = dismissDraftChanges;
window.requestDraftChanges = requestDraftChanges;
window.submitDraftChanges = submitDraftChanges;
window.toggleEndSessionConfirm = toggleEndSessionConfirm;
window.jumpToSessionChannel = jumpToSessionChannel;
window.showCastPreview = showCastPreview;
window.sessionCastBack = sessionCastBack;
window.launchSessionWithCast = launchSessionWithCast;
window.launchDraftSession = launchDraftSession;
window.sendDesignRequest = sendDesignRequest;
window.syncSessionCastRole = syncSessionCastRole;

window.toggleDeleteSessionTemplateConfirm = toggleDeleteSessionTemplateConfirm;
window.scrollToSessionOutput = scrollToSessionOutput;

window.Sessions = { init: _sessionsInit };
