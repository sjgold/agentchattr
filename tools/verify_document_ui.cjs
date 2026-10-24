// Actual document UI source in a VM with fake DOM/transports, never browser proof.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const read = name => fs.readFileSync(path.join(__dirname, '..', name), 'utf8');
const tests = [];
const test = (name, run) => tests.push({name, run});
const canonical = {version: 1, kind: 'file', name: 'source.py', source_id: 'file:' + 'a'.repeat(64),
  encoding: 'utf-8', byte_length: 13, content_sha256: 'b'.repeat(64), text: 'Exact\r\nsource'};
const plain = value => JSON.parse(JSON.stringify(value));
const deferred = () => { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return {promise, resolve, reject}; };
const flush = async () => { for (let i = 0; i < 15; i++) await Promise.resolve(); };

class Element {
  constructor(tag = 'div') {
    this.tagName = tag.toUpperCase(); this.children = []; this.listeners = {}; this.attributes = {};
    this.dataset = {}; this.style = {}; this._text = ''; this.value = ''; this.isConnected = true;
    this.disabled = false; this.readOnly = false; this.className = ''; this.hidden = false;
    this.classList = {add: (...names) => { this.className += ' ' + names.join(' '); }, remove() {}, toggle() {}};
  }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(value => value.textContent || '').join(' '); }
  set innerHTML(value) { assert.equal(value, '', 'file data must never be rendered as HTML'); this._text = ''; this.children = []; }
  appendChild(child) { if (child.parentNode) child.remove(); child.parentNode = this; this.children.push(child); return child; }
  insertBefore(child, reference) {
    if (reference === null) return this.appendChild(child);
    assert.ok(this.children.includes(reference), 'insertBefore reference must belong to target');
    if (child === reference) return child;
    if (child.parentNode) child.parentNode.children = child.parentNode.children.filter(value => value !== child);
    child.parentNode = this; this.children.splice(this.children.indexOf(reference), 0, child); return child;
  }
  append(...children) { for (const child of children) this.appendChild(typeof child === 'string' ? {textContent: child} : child); }
  replaceChildren(...children) { this.children = []; this._text = ''; this.append(...children); }
  remove() { if (this.parentNode) this.parentNode.children = this.parentNode.children.filter(value => value !== this); this.parentNode = null; this.isConnected = false; }
  setAttribute(name, value) { this.attributes[name] = String(value); if (name === 'id') this.id = String(value); }
  getAttribute(name) { return this.attributes[name] ?? null; }
  addEventListener(name, callback) { (this.listeners[name] ||= []).push(callback); }
  removeEventListener(name, callback) { this.listeners[name] = (this.listeners[name] || []).filter(value => value !== callback); }
  dispatchEvent(event) { event.target ||= this; for (const callback of this.listeners[event.type] || []) callback(event); if (event.bubbles && this.parentNode) this.parentNode.dispatchEvent(event); return true; }
  click() { if (!this.disabled) { this.onclick?.({target: this}); this.dispatchEvent({type: 'click'}); } }
  focus() { this.focused = true; }
  matches(selector) {
    if (selector.startsWith('.')) return this.className.split(/\s+/).includes(selector.slice(1));
    if (selector.startsWith('#')) return this.id === selector.slice(1);
    if (selector === 'input[type="file"]' || selector === 'input[type=file]') return this.tagName === 'INPUT' && this.type === 'file';
    return this.tagName.toLowerCase() === selector.toLowerCase();
  }
  querySelectorAll(selector) {
    const parts = selector.trim().split(/\s+/);
    let roots = [this];
    for (const part of parts) roots = [...new Set(roots.flatMap(root => descendants(root).filter(child => child.matches?.(part))))];
    return roots;
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}
const descendants = element => element.children.flatMap(child => [child, ...descendants(child)]);
function environment() {
  const ids = new Map(), requests = [], timers = new Map(); let now = 0, timerId = 0;
  const context = vm.createContext({console, AbortController, TextEncoder, TextDecoder, URLSearchParams,
    Event: class { constructor(type, options = {}) { this.type = type; Object.assign(this, options); } },
    CustomEvent: class { constructor(type, options = {}) { this.type = type; Object.assign(this, options); } },
    document: {createElement: tag => new Element(tag), createTextNode: text => ({textContent: text}),
      getElementById: id => ids.get(id) || null, querySelectorAll: () => [], body: new Element('body')},
    setTimeout(callback, delay = 0) { const id = ++timerId; timers.set(id, {at: now + delay, callback}); return id; },
    clearTimeout(id) { timers.delete(id); },
    fetch(url, options) { const result = deferred(); requests.push({url, options, ...result}); return result.promise; },
    alert(message) { throw new Error('Unexpected alert: ' + message); }});
  context.window = context; context.SESSION_TOKEN = 'private-test-token'; context.activeChannel = 'review'; context.username = 'operator';
  return {context, ids, requests, timers, async tick(ms) {
    const end = now + ms;
    while (true) {
      const next = [...timers].filter(([, timer]) => timer.at <= end).sort((a, b) => a[1].at - b[1].at)[0];
      if (!next) break;
      timers.delete(next[0]); now = next[1].at; next[1].callback(); await flush();
    }
    now = end; await flush();
  }};
}
function snapshot(name = 'source.py', text = canonical.text) {
  return {...canonical, name, text, byte_length: Buffer.byteLength(text, 'utf8')};
}
function answer(call, value = canonical, status = 200) {
  call.resolve({ok: status >= 200 && status < 300, status, json: async () => plain(value)});
}
function shared() {
  const env = environment();
  vm.runInContext(read('static/document-inputs.js'), env.context);
  env.editor = new Element(); env.editor.className = 'session-source-editor';
  env.textarea = new Element('textarea'); env.textarea.value = 'Original pasted café\r\ndraft';
  env.editor.appendChild(env.textarea);
  env.facade = env.context.DocumentInput.attach(env.editor);
  env.pick = async files => {
    const input = env.editor.querySelector('.document-file-input'); assert.ok(input);
    input.files = files; input.value = 'C:\\fakepath\\selected'; input.dispatchEvent({type: 'change'}); await flush();
    return input;
  };
  return env;
}
function block(source, begin, end) {
  const start = source.indexOf(begin), stop = source.indexOf(end, start);
  assert.ok(start >= 0 && stop > start, 'actual source block ' + begin);
  return source.slice(start, stop);
}
function launchers(mode = 'file') {
  const env = environment(), submissions = [], disposals = [];
  const modal = new Element(); modal.id = 'session-launcher-modal';
  const editor = new Element(); editor.className = 'session-source-editor'; modal.appendChild(editor);
  const input = new Element('textarea'); input.value = 'VISUALLY NORMALIZED\nTEXT'; editor.appendChild(input);
  const goal = new Element('input'); goal.id = 'session-goal-input'; goal.value = 'Original goal'; modal.appendChild(goal);
  const castStep = new Element(); castStep.id = 'session-step-cast'; modal.appendChild(castStep);
  const select = new Element('select'); select.className = 'session-cast-select'; select.dataset.role = 'reader'; select.value = 'codex'; castStep.appendChild(select);
  const button = new Element('button'); button.className = 'session-start-btn'; modal.appendChild(button);
  env.ids.set(modal.id, modal); env.ids.set('session-source-input', input); env.ids.set('session-goal-input', goal);
  env.context.document.querySelectorAll = () => [select];
  const facade = {state: mode, requestFields() {
    if (this.state === 'reading') throw new Error('Wait for the file check to finish.');
    if (this.state === 'error') throw new Error('Choose another file or use pasted text.');
    return this.state === 'file' ? {source_file: plain(canonical)} : {input_text: input.value};
  }, setSubmitting(value) { submissions.push(value); }, dispose() { disposals.push(modal); }};
  env.context.DocumentInput = {attach: () => facade};
  env.context.selectedRecoveryPolicy = () => ({ack_timeout: 30});
  const source = read('static/sessions.js');
  const helpers = block(source, '// DOCUMENT LAUNCHER HELPERS BEGIN', '// DOCUMENT LAUNCHER HELPERS END');
  vm.runInContext(helpers + '\n' + extractFunction(source, 'launchSessionWithCast') + '\n' + extractFunction(source, 'launchDraftSession')
    + '\nglobalThis.ordinary = launchSessionWithCast; globalThis.draft = launchDraftSession; globalThis.closeActual = closeSessionLauncher;', env.context);
  env.context.initializeDocumentInput(modal);
  return {...env, modal, editor, input, goal, select, button, facade, submissions, disposals};
}

function extractFunction(source, name) {
  const start = source.indexOf('async function ' + name + '(');
  const end = source.indexOf('\n}', start);
  assert.ok(start >= 0 && end > start, 'actual source function ' + name);
  return source.slice(start, end + 2);
}

test('actual shared document facade exists', async () => {
  const env = shared();
  for (const method of ['requestFields', 'setSubmitting', 'dispose']) assert.equal(typeof env.facade[method], 'function');
  assert.equal(env.facade.state, 'paste'); assert.equal(env.context.DocumentInput.attach(env.editor), env.facade);
  const html = read('static/index.html');
  assert.ok(html.indexOf('document-inputs.js') < html.indexOf('sessions.js'));
  for (const asset of ['document-inputs.js', 'sessions.js', 'sessions.css']) assert.match(html, new RegExp(asset.replace('.', '\\.') + '\\?v='));
});

test('both actual Start launchers post canonical file object instead of textarea', async () => {
  const captured = [];
  for (const name of ['ordinary', 'draft']) {
    const env = launchers();
    const stray = new Element('select'); stray.className = 'session-cast-select';
    stray.dataset.role = 'reader'; stray.value = 'outside-cast-step'; env.modal.appendChild(stray);
    const sending = env.context[name](name === 'draft' ? 7 : 'review'); await flush();
    assert.equal(env.requests.length, 1);
    const payload = JSON.parse(env.requests[0].options.body);
    captured.push(payload);
    assert.deepEqual(payload.source_file, canonical);
    assert.equal(Object.hasOwn(payload, 'input_text'), false);
    assert.equal(payload.channel, 'review');
    answer(env.requests[0], {error: 'Fixture rejection'}, 400); await sending;
    assert.equal(env.modal.isConnected, true);
  }
  assert.equal(captured.length, 2);
  for (const payload of captured) assert.equal(payload.cast.reader, 'codex', 'only the actual cast step supplies role assignments');
});

test('paste and canonical file fields are detached and file mode ignores normalized textarea', async () => {
  const env = shared();
  assert.deepEqual(plain(env.facade.requestFields()), {input_text: 'Original pasted café\r\ndraft'});
  await env.pick([{name: canonical.name, size: canonical.byte_length}]);
  assert.equal(env.facade.state, 'reading'); assert.throws(() => env.facade.requestFields());
  answer(env.requests[0]); await flush();
  assert.equal(env.facade.state, 'file'); assert.equal(env.textarea.readOnly, true);
  env.textarea.value = 'Normalized\nvisual source';
  const first = plain(env.facade.requestFields());
  assert.deepEqual(first, {source_file: canonical});
  first.source_file.text = 'local edit';
  assert.deepEqual(plain(env.facade.requestFields()), {source_file: canonical});
  env.facade.setSubmitting(true); assert.throws(() => env.facade.requestFields());
  env.facade.setSubmitting(false); assert.deepEqual(plain(env.facade.requestFields()), {source_file: canonical});
});

test('file fetch is raw and advisory extensions Unicode plus BOM empty and size are honest', async () => {
  for (const [name, text] of [['資料 + source.rs', '\ufeffcafé\r\n😀'], ['Makefile', ''], ['query.sql', 'literal']]) {
    const env = shared(), data = snapshot(name, text), file = {name, size: data.byte_length};
    const input = await env.pick([file]);
    assert.equal(input.value, '', 'same file can be selected again');
    assert.equal(env.requests.length, 1);
    assert.equal(env.requests[0].url, '/api/documents/preview?filename=' + encodeURIComponent(name));
    assert.equal(env.requests[0].options.body, file);
    assert.equal(env.requests[0].options.headers['Content-Type'], 'application/octet-stream');
    assert.equal(env.requests[0].options.headers['X-Session-Token'], 'private-test-token');
    answer(env.requests[0], data); await flush();
    assert.deepEqual(plain(env.facade.requestFields()), {source_file: data});
    assert.ok(env.editor.textContent.includes(name));
    assert.ok(env.editor.textContent.includes(data.content_sha256));
    assert.ok(env.editor.textContent.includes(data.source_id));
    assert.match(env.editor.textContent, /Other plain-text files.*All files/i);
    if (text.startsWith('\ufeff')) assert.match(env.editor.textContent, /BOM present, preserved/);
    if (!text) assert.match(env.editor.textContent, /0 bytes \(empty source\)/);
  }
  const env = shared(); await env.pick([{name: 'large.txt', size: 524289}]);
  assert.equal(env.requests.length, 0); assert.equal(env.facade.state, 'error');
});

test('picker cancel same-file reselection and invalid replacement never silently fall back', async () => {
  const env = shared(), file = {name: canonical.name, size: canonical.byte_length};
  await env.pick([]); assert.equal(env.facade.state, 'paste'); assert.equal(env.requests.length, 0);
  await env.pick([file]); answer(env.requests[0]); await flush();
  await env.pick([]); assert.equal(env.facade.state, 'file');
  await env.pick([file]); assert.equal(env.requests.length, 2); answer(env.requests[1]); await flush();
  await env.pick([{name: 'bad.txt', size: 1}]); answer(env.requests[2], {error: 'Invalid document at byte 0.'}, 400); await flush();
  assert.equal(env.facade.state, 'error'); assert.throws(() => env.facade.requestFields());
  assert.match(env.editor.textContent, /Previous preview, not ready to start/i);
  assert.match(env.editor.querySelector('.document-error').textContent, /Invalid document at byte 0\./);
  assert.match(env.editor.textContent, /Nothing was started/i);
  await env.pick([]); assert.equal(env.facade.state, 'error');
  env.editor.querySelector('.document-use-paste').click(); await flush();
  assert.equal(env.facade.state, 'paste');
  assert.deepEqual(plain(env.facade.requestFields()), {input_text: 'Original pasted café\r\ndraft'});
  assert.equal(env.textarea.focused, true);
  const multiple = shared(); await multiple.pick([file, file]);
  assert.equal(multiple.requests.length, 0); assert.equal(multiple.facade.state, 'error');
});

test('malformed preview response fails closed without substituting canonical claims', async () => {
  const changes = [{version: true}, {kind: 'paste'}, {encoding: 'utf-16'}, {name: 'other.py'},
    {byte_length: true}, {byte_length: 14}, {content_sha256: 'B'.repeat(64)}, {source_id: 'path:source.py'},
    {text: 'Different length'}, {path: 'extra'}, {text: null}];
  for (const change of changes) {
    const env = shared(); await env.pick([{name: canonical.name, size: canonical.byte_length}]);
    answer(env.requests[0], {...canonical, ...change}); await flush();
    assert.equal(env.facade.state, 'error', JSON.stringify(change));
    assert.throws(() => env.facade.requestFields()); assert.equal(env.requests.length, 1);
    assert.match(env.editor.querySelector('.document-error').textContent, /The file preview response was invalid\./);
  }
  for (const failure of ['network', 'json']) {
    const env = shared(); const originalDraft = env.textarea.value;
    await env.pick([{name: canonical.name, size: canonical.byte_length}]);
    if (failure === 'network') env.requests[0].reject(new TypeError('PRIVATE_NETWORK_PATH /secret/source.py'));
    else env.requests[0].resolve({ok: true, status: 200,
      json: async () => { throw new SyntaxError('PRIVATE_RESPONSE_BODY <script>source</script>'); }});
    await flush();
    assert.equal(env.facade.state, 'error'); assert.equal(env.textarea.value, originalDraft);
    assert.throws(() => env.facade.requestFields());
    const feedback = env.editor.querySelector('.document-error').textContent;
    assert.match(feedback, /The file could not be checked\./);
    assert.doesNotMatch(feedback, /PRIVATE_NETWORK_PATH|PRIVATE_RESPONSE_BODY|secret\/source|<script>/);
  }
});

test('stale previews abort timeout and dispose cannot change the newest or removed editor', async () => {
  const env = shared(); await env.pick([{name: 'old.py', size: 3}]);
  await env.pick([{name: 'new.py', size: 3}]);
  assert.equal(env.requests[0].options.signal.aborted, true);
  answer(env.requests[1], snapshot('new.py', 'new')); await flush();
  answer(env.requests[0], snapshot('old.py', 'old')); await flush();
  assert.equal(env.facade.requestFields().source_file.name, 'new.py');
  const timeout = shared(); await timeout.pick([{name: canonical.name, size: canonical.byte_length}]);
  await timeout.tick(8000); assert.equal(timeout.requests[0].options.signal.aborted, true);
  assert.equal(timeout.facade.state, 'error'); assert.throws(() => timeout.facade.requestFields());
  for (const dispose of [false, true]) {
    const closed = shared(); await closed.pick([{name: canonical.name, size: canonical.byte_length}]);
    if (dispose) closed.facade.dispose(); else closed.editor.isConnected = false;
    answer(closed.requests[0]); await flush();
    assert.notEqual(closed.facade.state, 'file'); assert.throws(() => closed.facade.requestFields());
    if (dispose) assert.equal(closed.timers.size, 0);
  }
});

test('both Start paths catch reading and error before POST or submitting changes', async () => {
  for (const state of ['reading', 'error']) for (const path of ['ordinary', 'draft']) {
    const env = launchers(state), before = env.submissions.length;
    await env.context[path](path === 'draft' ? 7 : 'review');
    assert.equal(env.requests.length, 0); assert.equal(env.submissions.length, before);
    assert.equal(env.modal.isConnected, true); assert.equal(env.input.value, 'VISUALLY NORMALIZED\nTEXT');
    assert.match(env.modal.textContent, state === 'reading' ? /Wait for the file check to finish/ : /Choose another file or use pasted text/);
  }
});

test('single-flight Starts retain source task cast and recovery settings after refusal', async () => {
  for (const path of ['ordinary', 'draft']) {
    const env = launchers();
    const first = env.context[path](path === 'draft' ? 7 : 'review');
    const second = env.context[path](path === 'draft' ? 7 : 'review'); await flush();
    assert.equal(env.requests.length, 1); assert.deepEqual(env.submissions, [true]);
    answer(env.requests[0], {error: 'Refused by fixture'}, 400); await Promise.all([first, second]);
    assert.deepEqual(env.submissions, [true, false]); assert.equal(env.modal.isConnected, true);
    assert.equal(env.goal.value, 'Original goal'); assert.equal(env.select.value, 'codex');
    assert.deepEqual(env.facade.requestFields(), {source_file: canonical});
    assert.match(env.modal.textContent, /Refused by fixture/); assert.equal(env.requests.length, 1);
  }
});

test('closed modal success cannot remove or submit a newer modal', async () => {
  for (const path of ['ordinary', 'draft']) {
    const env = launchers(); const sending = env.context[path](path === 'draft' ? 7 : 'review'); await flush();
    env.context.closeActual(env.modal);
    const newer = new Element(); newer.id = 'session-launcher-modal'; env.ids.set(newer.id, newer);
    answer(env.requests[0], {id: 1}); await sending;
    assert.equal(newer.isConnected, true); assert.equal(env.ids.get(newer.id), newer);
    assert.equal(env.disposals.length, 1); assert.equal(env.requests.length, 1);
  }
});

test('actual close helper and design request dispose while every modal close path delegates', async () => {
  const env = launchers(), source = read('static/sessions.js');
  const agent = new Element('select'); agent.value = 'codex'; env.ids.set('session-design-agent', agent);
  const description = new Element('input'); description.value = 'Design fixture'; env.ids.set('session-design-desc', description);
  vm.runInContext(extractFunction(source, 'sendDesignRequest') + '\nglobalThis.designActual = sendDesignRequest;', env.context);
  const sending = env.context.designActual(); await flush();
  assert.equal(env.modal.isConnected, false); assert.equal(env.disposals.length, 1);
  answer(env.requests[0], {ok: true}); await sending;
  const helpers = block(source, '// DOCUMENT LAUNCHER HELPERS BEGIN', '// DOCUMENT LAUNCHER HELPERS END');
  const withoutHelper = source.replace(helpers, '');
  assert.doesNotMatch(withoutHelper, /\b(?:modal|existing)\.remove\(/, 'direct modal removal must pass disposal helper');
  assert.match(source, /if\s*\(e\.target === modal\)\s*closeSessionLauncher\(modal\)/);
  assert.match(source, /onclick="closeSessionLauncher\(/);
});

test('actual restart badge is literal and file-only with scoped readable control styles', async () => {
  const env = environment(), source = read('static/sessions.js');
  vm.runInContext(block(source, '// DOCUMENT RESTART BADGE BEGIN', '// DOCUMENT RESTART BADGE END'), env.context);
  const fileSection = new Element();
  env.context.appendOriginalFileBadge(fileSection, {input_snapshot: {text: 'first\r\nsecond', document: {kind: 'file', name: '<script>literal.py'}}});
  assert.match(fileSection.textContent, /Original file: <script>literal\.py/);
  assert.match(fileSection.textContent, /CRLF/);
  assert.match(fileSection.textContent, /pasted snapshot/);
  for (const input_snapshot of [{text: 'paste'}, {text: 'prepared child'}]) {
    const section = new Element(); env.context.appendOriginalFileBadge(section, {input_snapshot});
    assert.equal(section.children.length, 0);
  }
  const css = read('static/sessions.css');
  const component = css.slice(css.indexOf('.document-'));
  assert.match(component, /font-size:\s*14px/); assert.match(component, /min-height:\s*44px/);
  assert.match(component, /padding:\s*12px/); assert.match(component, /(?:overflow-wrap:\s*anywhere|word-break:\s*break-all)/);
});

(async () => {
  let failures = 0;
  for (const {name, run} of tests) {
    try { await run(); console.log('PASS ' + name); }
    catch (error) { failures++; console.error('FAIL ' + name + '\n' + error.stack); }
  }
  console.log(JSON.stringify({cases: tests.length, failures, scope: 'actual_source_vm_only'}));
  process.exitCode = failures ? 1 : 0;
})();
