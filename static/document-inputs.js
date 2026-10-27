/* Literal UTF-8 document preview. Authority stays with the server snapshot. */
(function () {
    'use strict';
    const editors = new WeakMap();
    const MAX_BYTES = 512 * 1024;
    const ACCEPT = '.md,.txt,.py,.mjs,.js,.ts,.tsx,.jsx,.json,.yaml,.yml,.toml,.css,.html';
    const KEYS = ['version', 'kind', 'source_id', 'name', 'encoding', 'byte_length', 'content_sha256', 'text'];
    const copy = value => JSON.parse(JSON.stringify(value));
    class FileCheckError extends Error {}

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
        const choose = make('button', 'document-choose-file', 'Choose UTF-8 files');
        const paste = make('button', 'document-use-paste', 'Use pasted text');
        choose.type = paste.type = 'button';
        paste.hidden = true;
        const picker = make('input', 'document-file-input');
        picker.type = 'file'; picker.accept = ACCEPT; picker.multiple = true; picker.hidden = true;
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
        if (label) label.textContent = 'Review source (paste text or choose files)';
        let state = 'paste', submitting = false, disposed = false, epoch = 0;
        let pasted = input.value, snapshot = null, controller = null, timer = null, checkedFiles = [];
        const originalPlaceholder = input.placeholder;

        function abort() {
            if (controller) controller.abort();
            if (timer !== null) clearTimeout(timer);
            controller = null; timer = null;
        }
        function notify() {
            choose.disabled = paste.disabled = picker.disabled = submitting;
            input.disabled = submitting;
            for (const button of metadata.querySelectorAll('.document-remove-file')) button.disabled = submitting || state === 'reading';
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
            const remove = (index, label) => {
                const button = make('button', 'document-remove-file', label);
                button.type = 'button';
                button.onclick = async () => {
                    if (disposed || submitting || state === 'reading') return;
                    const remaining = checkedFiles.filter((_, i) => i !== index);
                    if (!remaining.length) { usePaste(); return; }
                    await checkSelection(null, remaining);
                };
                metadata.append(button);
            };
            if (value.version === 2) {
                metadata.append(make('dt', '', 'Files'), make('dd', '', value.files.length + ' files; ' + value.byte_length + ' total bytes of 524288'));
                value.files.forEach((file, index) => {
                    metadata.append(make('dt', '', file.file_id), make('dd', '', file.name + ' (' + file.byte_length + ' bytes)'));
                    remove(index, 'Remove ' + file.file_id);
                });
                metadata.append(make('dt', '', 'Packet revision'), make('dd', '', value.content_sha256));
                metadata.hidden = false;
                return;
            }
            const endingKinds = new Set((value.text.match(/\r\n|\r|\n/g) || []).map(x => x === '\r\n' ? 'CRLF' : x === '\r' ? 'CR' : 'LF'));
            const ending = endingKinds.size > 1 ? 'mixed line endings' : [...endingKinds][0] || 'no line breaks';
            const rows = [['File', value.name], ['Size', value.byte_length === 0 ? '0 bytes (empty source)' : value.byte_length + ' bytes'],
                ['Text', ending + '. Original bytes are preserved.'], ['SHA-256', value.content_sha256], ['Source ID', value.source_id]];
            if (value.text.startsWith('\ufeff')) rows.push(['Encoding', 'UTF-8 BOM present, preserved']);
            for (const [title, text] of rows) metadata.append(make('dt', '', title), make('dd', '', text));
            remove(0, 'Remove file');
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
        function validPacket(value, files) {
            const fields = ['version','kind','encoding','source_id','byte_length','content_sha256','files','text'];
            if (!value || typeof value !== 'object' || Object.keys(value).length !== fields.length || !fields.every(k => Object.hasOwn(value, k))
                || value.version !== 2 || value.kind !== 'file_packet' || value.encoding !== 'utf-8'
                || !Array.isArray(value.files) || value.files.length !== files.length || typeof value.text !== 'string'
                || new TextEncoder().encode(value.text).length > 1114112
                || !/^[0-9a-f]{64}$/.test(value.content_sha256) || value.source_id !== 'packet:' + value.content_sha256
                || value.byte_length !== files.reduce((sum, file) => sum + file.byte_length, 0)) return false;
            let manifest;
            try { manifest = JSON.parse(value.text); } catch { return false; }
            if (!manifest || Object.keys(manifest).length !== 3 || manifest.version !== 2 || manifest.kind !== 'file_packet'
                || !Array.isArray(manifest.files) || manifest.files.length !== files.length) return false;
            return files.every((file, i) => {
                const row = manifest.files[i], meta = value.files[i], id = 'f' + (i + 1);
                return row && meta && Object.keys(row).length === KEYS.length + 1 && Object.keys(meta).length === KEYS.length
                    && row.file_id === id && meta.file_id === id
                    && KEYS.every(key => row[key] === file[key])
                    && KEYS.filter(key => key !== 'text').every(key => meta[key] === file[key]);
            });
        }
        function previewText(value) {
            if (value.version !== 2) return value.text;
            return JSON.parse(value.text).files.map(file =>
                file.file_id + ': ' + file.name + ' (' + file.byte_length + ' bytes)\n\n' + file.text).join('\n\n');
        }
        async function checkSelection(files, alreadyChecked) {
            if (disposed || submitting) return;
            if (state === 'paste') pasted = input.value;
            abort();
            const current = ++epoch;
            const total = (files || alreadyChecked).reduce((sum, file) => sum + (files ? file.size : file.byte_length), 0);
            if (total > MAX_BYTES) { fail('Combined file bytes exceed the 512 KiB aggregate limit; nothing was truncated.'); return; }
            state = 'reading'; error.hidden = true;
            status.textContent = 'Checking UTF-8 files. Nothing has started.';
            notify();
            const ownedController = new AbortController();
            controller = ownedController;
            let timedOut = false;
            const live = () => !disposed && epoch === current && editor.isConnected;
            timer = setTimeout(() => {
                if (!live()) return;
                timedOut = true; ownedController.abort(); epoch++;
                controller = null; timer = null; fail('File check timed out.');
            }, 8000);
            try {
                const checked = alreadyChecked ? copy(alreadyChecked) : [];
                if (files) for (const file of files) {
                    const response = await fetch('/api/documents/preview?filename=' + encodeURIComponent(file.name), {
                        method: 'POST', headers: {'Content-Type': 'application/octet-stream', 'X-Session-Token': window.SESSION_TOKEN},
                        body: file, signal: ownedController.signal
                    });
                    const value = await response.json();
                    if (!live()) return;
                    if (!response.ok) throw new FileCheckError(typeof value?.error === 'string' ? value.error : 'The file could not be checked.');
                    if (!valid(value, file)) throw new FileCheckError('The file preview response was invalid.');
                    checked.push(copy(value));
                }
                let value = checked[0];
                if (checked.length > 1) {
                    const response = await fetch('/api/documents/packet-preview', {
                        method: 'POST', headers: {'Content-Type': 'application/json', 'X-Session-Token': window.SESSION_TOKEN},
                        body: JSON.stringify({files: checked}), signal: ownedController.signal
                    });
                    value = await response.json();
                    if (!live()) return;
                    if (!response.ok) throw new FileCheckError(typeof value?.error === 'string' ? value.error : 'The packet could not be checked.');
                    if (!validPacket(value, checked)) throw new FileCheckError('The packet preview response was invalid.');
                }
                if (!live()) return;
                checkedFiles = copy(checked); snapshot = copy(value); state = 'file';
                input.value = previewText(value); input.placeholder = '';
                status.textContent = checked.length > 1 ? 'Files checked. Start freezes this exact packet.' : 'File checked. Start freezes this exact snapshot.';
                error.hidden = true; showMetadata(snapshot); notify();
            } catch (failure) {
                if (live() && !timedOut) fail(failure instanceof FileCheckError ? failure.message :
                    failure?.name === 'AbortError' ? 'File check was interrupted.' : 'The files could not be checked.');
            } finally {
                if (epoch === current) {
                    if (timer !== null) clearTimeout(timer);
                    controller = null; timer = null;
                }
            }
        }
        async function selected() {
            if (disposed || submitting || !picker.files?.length) return;
            const files = Array.from(picker.files); picker.value = '';
            await checkSelection(files, null);
        }
        function usePaste() {
            if (disposed || submitting) return;
            abort(); epoch++;
            state = 'paste'; snapshot = null; checkedFiles = [];
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
