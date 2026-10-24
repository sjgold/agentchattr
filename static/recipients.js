// Server-owned audience preview. This module never parses addresses.
(() => {
    const FAILURE = 'Audience preview is unavailable. Draft kept. Check again before sending.';
    function attach(element) {
        let state = 'idle', epoch = 0, timer = null, controller = null;
        let request = null, key = null, announcement = null, announcementKey = null;
        element.classList.add('recipient-preview');
        const live = document.createElement('div');
        live.setAttribute('aria-live', 'polite');
        live.setAttribute('aria-atomic', 'true');
        const body = document.createElement('div');
        element.replaceChildren(body, live);
        live.className = 'recipient-announcement';
        function change(next) {
            state = next;
            element.setAttribute('aria-busy', String(next === 'checking'));
            element.dispatchEvent(new Event('recipient-preview-state'));
        }
        function line(parent, text, className = '') {
            const node = document.createElement('p');
            node.className = className;
            node.textContent = text;
            parent.appendChild(node);
            return node;
        }
        function announce(text, comparison = text) {
            if (comparison !== announcementKey) { live.textContent = text; announcement = text; announcementKey = comparison; }
        }
        function idle() {
            body.replaceChildren();
            line(body, 'Addressed agents', 'recipient-heading');
            line(body, 'Choose recipients or write @names. Unaddressed messages stay in the shared conversation.');
            announce('');
        }
        function error(text = FAILURE) {
            body.replaceChildren();
            line(body, 'Addressed agents', 'recipient-heading');
            line(body, text, 'recipient-warning');
            const retry = document.createElement('button');
            retry.type = 'button'; retry.textContent = 'Check again';
            retry.addEventListener('click', () => { if (request) prepare(request).catch(() => {}); });
            body.appendChild(retry);
            change('error'); announce(text);
        }
        function validate(data) {
            if (!data || !['explicit', 'selected', 'none'].includes(data.mode)
                || !['tokens', 'ignored', 'recipients', 'warnings', 'waiting'].every(k => Array.isArray(data[k]))
                || data.recipients.some(r => !r || typeof r.name !== 'string' || typeof r.identity_id !== 'string')
                || data.ignored.some(r => !r || typeof r.token !== 'string' || !['quote', 'code', 'fence'].includes(r.reason))
                || data.warnings.some(r => !r || typeof r.kind !== 'string' || typeof r.token !== 'string')
                || data.waiting.some(r => !r || typeof r.identity_id !== 'string')) throw new Error('Invalid preview');
            return data;
        }
        function render(data) {
            body.replaceChildren();
            line(body, 'Addressed agents', 'recipient-heading');
            const label = {explicit: 'Explicit addresses', selected: 'Selected recipients', none: 'Shared note'}[data.mode];
            line(body, label, 'recipient-source');
            line(body, data.recipients.length ? data.recipients.map(r => '@' + r.name).join(', ')
                : 'No agents addressed. This stays in the shared conversation.', 'recipient-audience');
            if (data.mode === 'explicit' && request.selected_recipients.length)
                line(body, 'Explicit @mentions replace the selected buttons for this message.');
            for (const warning of data.warnings) {
                const descriptions = {unknown: 'Unknown address', ambiguous: 'Ambiguous address', unavailable: 'Unavailable recipient', offline: 'Offline recipient'};
                let text = (descriptions[warning.kind] || 'Address warning') + ': @' + warning.token;
                if (Array.isArray(warning.candidates) && warning.candidates.length) text += '. Choose ' + warning.candidates.join(', ');
                if (warning.kind === 'offline') text += '. Work will queue for this identity.';
                line(body, text, 'recipient-warning');
            }
            if (data.waiting.length) {
                line(body, 'Waits for the earlier review turn on this seat; recover or Stop that turn.', 'recipient-warning');
                line(body, 'Agent mentions during a review are display-only.');
            }
            if (data.ignored.length) {
                const details = document.createElement('details');
                details.open = data.ignored.length <= 3;
                const summary = document.createElement('summary');
                summary.textContent = 'Ignored addresses (' + data.ignored.length + ')';
                details.appendChild(summary);
                for (const item of data.ignored) line(details, '@' + item.token + ' in ' + {quote: 'quoted text', code: 'inline code', fence: 'fenced code'}[item.reason]);
                body.appendChild(details);
            }
            // Text edits with the same audience do not repeat live announcements.
            const comparison = JSON.stringify({label, recipients: data.recipients, warnings: data.warnings, ignored: data.ignored, waiting: data.waiting});
            announce(label + '. ' + (data.recipients.length ? data.recipients.map(r => '@' + r.name).join(', ') : 'No agents addressed.')
                + (data.warnings.length ? ' Address warnings: ' + data.warnings.map(w => w.kind + ' @' + w.token).join(', ') + '.' : '')
                + (data.ignored.length ? ' Ignored addresses: ' + data.ignored.map(i => '@' + i.token + ' in ' + i.reason).join(', ') + '.' : '')
                + (data.waiting.length ? ' Waits for an earlier review turn.' : ''), comparison);
        }
        function cancel() {
            epoch++; clearTimeout(timer); timer = null;
            if (controller) controller.abort(); controller = null;
        }
        async function prepare(value) {
            cancel(); request = JSON.parse(JSON.stringify(value)); key = JSON.stringify(request);
            const own = epoch;
            controller = new AbortController();
            const signal = controller.signal;
            change('checking');
            let deadline;
            try {
                const timeout = new Promise((_, reject) => {
                    deadline = setTimeout(() => { if (own === epoch && controller) controller.abort(); reject(new Error('Preview timeout')); }, 8000);
                });
                const data = await Promise.race([fetch('/api/recipients/preview', {
                    method: 'POST', headers: {'Content-Type': 'application/json', 'X-Session-Token': window.SESSION_TOKEN},
                    body: JSON.stringify(request), signal,
                }).then(async response => { if (!response.ok) throw new Error('Preview unavailable'); return validate(await response.json()); }), timeout]);
                if (own !== epoch) throw new Error('Stale preview');
                render(data); change('ready'); return data;
            } catch (failure) {
                if (own === epoch) error();
                throw failure;
            } finally { clearTimeout(deadline); if (own === epoch) controller = null; }
        }
        function schedule(value, force = false) {
            const next = value === null ? null : JSON.stringify(value);
            if (next === key && force !== true) return;
            cancel(); key = next; request = value === null ? null : JSON.parse(next);
            if (request === null) { idle(); change('idle'); return; }
            timer = setTimeout(() => { prepare(request).catch(() => {}); }, 250);
        }
        function invalidate() { cancel(); key = null; request = null; idle(); change('idle'); }
        idle();
        return {schedule, prepare, invalidate, error, get state() { return state; }};
    }
    function appendReceipt(element, message) {
        const receipt = message.metadata?.recipient_routing;
        if (!receipt || receipt.version !== 1 || receipt.message_uid !== message.uid || !Array.isArray(receipt.recipients)) return;
        const target = element.querySelector('.chat-bubble') || element;
        const row = target.querySelector('.recipient-receipt') || document.createElement('p');
        row.className = 'recipient-receipt';
        row.textContent = 'Resolved audience: ' + (receipt.recipients.length
            ? receipt.recipients.map(r => '@' + r.name).join(', ') : 'No agents addressed. Shared conversation.');
        const actions = target.querySelector('.msg-actions');
        target.insertBefore(row, actions?.parentNode === target ? actions : null);
    }
    window.RecipientPreview = {attach, appendReceipt};
})();
