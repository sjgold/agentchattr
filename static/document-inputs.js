/* Literal UTF-8 document preview. Authority stays with the server snapshot. */
(function () {
    'use strict';
    const editors = new WeakMap();
    const MAX_BYTES = 512 * 1024;
    const ACCEPT = '.md,.txt,.py,.mjs,.js,.ts,.tsx,.jsx,.json,.yaml,.yml,.toml,.css,.html';
    const KEYS = ['version', 'kind', 'source_id', 'name', 'encoding', 'byte_length', 'content_sha256', 'text'];
    const copy = value => JSON.parse(JSON.stringify(value));

    function attach(editor) {
        if (editors.has(editor)) return editors.get(editor);
        const input = editor.querySelector('textarea');
        if (!input) throw new Error('Review source editor is unavailable.');
        editor.classList.add('document-input');
        const make = (tag, className, text) => {
            const node = document.createElement(tag);
            node.className = className;
            if (text) node.textContent = text;
            return node;
        };
        const actions = make('div', 'document-actions');
        const choose = make('button', 'document-choose-file', 'Choose UTF-8 file');
        const paste = make('button', 'document-use-paste', 'Use pasted text');
        choose.type = paste.type = 'button';
        paste.hidden = true;
        const picker = make('input', 'document-file-input');
        picker.type = 'file'; picker.accept = ACCEPT; picker.multiple = false; picker.hidden = true;
        const hint = make('p', 'document-picker-hint', 'Other plain-text files: choose All files in the dialog.');
        const status = make('p', 'document-status');
        status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
        const error = make('p', 'document-error');
        error.setAttribute('role', 'alert'); error.hidden = true;
        const metadata = make('dl', 'document-metadata'); metadata.hidden = true;
        actions.append(choose, paste, picker);
        editor.insertBefore(actions, input);
        editor.append(hint, status, error, metadata);
        const label = editor.querySelector('label');
        if (label) label.textContent = 'Review source (paste text or choose one file)';
        let state = 'paste', submitting = false, disposed = false, epoch = 0;
        let pasted = input.value, snapshot = null, controller = null, timer = null;
        const originalPlaceholder = input.placeholder;

        function abort() {
            if (controller) controller.abort();
            if (timer !== null) clearTimeout(timer);
            controller = null; timer = null;
        }
        function notify() {
            choose.disabled = paste.disabled = picker.disabled = submitting;
            input.disabled = submitting;
            input.readOnly = state !== 'paste';
            paste.hidden = state === 'paste';
            editor.dispatchEvent(new CustomEvent('document-input-state', {
                bubbles: true, detail: {state, canSubmit: !disposed && !submitting && (state === 'paste' || state === 'file')}
            }));
        }
        function fail(message) {
            state = 'error';
            status.textContent = snapshot ? 'Previous preview, not ready to start' : 'File not ready to start';
            error.textContent = message + ' Choose another file or use pasted text. Nothing was started.';
            error.hidden = false;
            notify();
        }
        function showMetadata(value) {
            metadata.replaceChildren();
            const endingKinds = new Set((value.text.match(/\r\n|\r|\n/g) || []).map(x => x === '\r\n' ? 'CRLF' : x === '\r' ? 'CR' : 'LF'));
            const ending = endingKinds.size > 1 ? 'mixed line endings' : [...endingKinds][0] || 'no line breaks';
            const rows = [['File', value.name], ['Size', value.byte_length === 0 ? '0 bytes (empty source)' : value.byte_length + ' bytes'],
                ['Text', ending + '. Original bytes are preserved.'], ['SHA-256', value.content_sha256], ['Source ID', value.source_id]];
            if (value.text.startsWith('\ufeff')) rows.push(['Encoding', 'UTF-8 BOM present, preserved']);
            for (const [title, text] of rows) metadata.append(make('dt', '', title), make('dd', '', text));
            metadata.hidden = false;
        }
        function valid(value, file) {
            return value && typeof value === 'object' && !Array.isArray(value)
                && Object.keys(value).length === KEYS.length && KEYS.every(key => Object.hasOwn(value, key))
                && value.version === 1 && value.kind === 'file' && value.encoding === 'utf-8'
                && typeof value.text === 'string' && value.name === file.name
                && Number.isInteger(value.byte_length) && value.byte_length >= 0 && value.byte_length <= MAX_BYTES
                && value.byte_length === file.size && new TextEncoder().encode(value.text).length === value.byte_length
                && typeof value.content_sha256 === 'string' && /^[0-9a-f]{64}$/.test(value.content_sha256)
                && typeof value.source_id === 'string' && /^file:[0-9a-f]{64}$/.test(value.source_id);
        }
        async function selected() {
            if (disposed || submitting || !picker.files?.length) return;
            const files = Array.from(picker.files);
            picker.value = '';
            if (state === 'paste') pasted = input.value;
            abort();
            const current = ++epoch;
            if (files.length !== 1) { fail('Choose one file at a time.'); return; }
            const file = files[0];
            if (file.size > MAX_BYTES) { fail('File exceeds the 512 KiB limit; nothing was truncated.'); return; }
            state = 'reading'; error.hidden = true;
            status.textContent = 'Checking UTF-8 file. Nothing has started.';
            notify();
            const ownedController = new AbortController();
            controller = ownedController;
            let timedOut = false;
            const live = () => !disposed && epoch === current && editor.isConnected;
            timer = setTimeout(() => {
                if (!live()) return;
                timedOut = true;
                ownedController.abort();
                // A transport that ignores abort must still not hold Start forever.
                epoch++;
                controller = null; timer = null;
                fail('File check timed out.');
            }, 8000);
            try {
                const response = await fetch('/api/documents/preview?filename=' + encodeURIComponent(file.name), {
                    method: 'POST', headers: {'Content-Type': 'application/octet-stream', 'X-Session-Token': window.SESSION_TOKEN},
                    body: file, signal: ownedController.signal
                });
                const value = await response.json();
                if (!live()) return;
                if (!response.ok) throw new Error(typeof value?.error === 'string' ? value.error : 'The file could not be checked.');
                if (!valid(value, file)) throw new Error('The file preview response was invalid.');
                snapshot = copy(value); state = 'file';
                input.value = value.text; input.placeholder = '';
                status.textContent = 'File checked. Start freezes this exact snapshot.';
                error.hidden = true;
                showMetadata(snapshot);
                notify();
            } catch (failure) {
                if (live() && !timedOut) fail(failure.name === 'AbortError' ? 'File check was interrupted.' :
                    failure.message || 'The file could not be checked.');
            } finally {
                if (epoch === current) {
                    if (timer !== null) clearTimeout(timer);
                    controller = null; timer = null;
                }
            }
        }
        function usePaste() {
            if (disposed || submitting) return;
            abort(); epoch++;
            state = 'paste'; snapshot = null;
            input.value = pasted; input.placeholder = originalPlaceholder;
            metadata.hidden = true; metadata.replaceChildren();
            error.hidden = true; status.textContent = '';
            notify(); input.focus();
        }
        const openPicker = () => { if (!submitting && !disposed) picker.click(); };
        const edited = () => { if (state === 'paste') pasted = input.value; };
        choose.addEventListener('click', openPicker);
        picker.addEventListener('change', selected);
        paste.addEventListener('click', usePaste);
        input.addEventListener('input', edited);
        const facade = {
            get state() { return state; },
            requestFields() {
                if (disposed) throw new Error('This source editor has closed.');
                if (state === 'reading') throw new Error('Wait for the file check to finish.');
                if (state === 'error') throw new Error('Choose another file or use pasted text.');
                if (submitting) throw new Error('Start is already in progress.');
                return state === 'file' ? {source_file: copy(snapshot)} : {input_text: input.value};
            },
            setSubmitting(value) { if (!disposed) { submitting = !!value; notify(); } },
            dispose() {
                if (disposed) return;
                disposed = true; epoch++; abort();
                choose.removeEventListener('click', openPicker);
                picker.removeEventListener('change', selected);
                paste.removeEventListener('click', usePaste);
                input.removeEventListener('input', edited);
            }
        };
        editors.set(editor, facade);
        notify();
        return facade;
    }
    window.DocumentInput = {attach};
})();
