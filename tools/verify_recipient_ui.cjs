// Actual-source VM contracts. Fake DOM/transports only, never browser acceptance.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');
const read = name => fs.readFileSync(path.join(root, name), 'utf8');
const cases = [];
function test(name, run) { cases.push({name, run}); }
const plain = value => JSON.parse(JSON.stringify(value));
const deferred = () => { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return {promise, resolve, reject}; };
const flush = async () => { for (let i = 0; i < 12; i++) await Promise.resolve(); };

class Element {
  constructor(tag = 'div') {
    this.tagName = tag.toUpperCase(); this.children = []; this.attributes = {};
    this.listeners = {}; this.style = {}; this.dataset = {}; this.value = '';
    this.disabled = false; this.hidden = false; this._text = ''; this.className = '';
    this.classList = {add() {}, remove() {}, toggle() {}, contains() { return false; }};
  }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(c => c.textContent || '').join(' '); }
  set innerHTML(value) { assert.equal(value, '', 'untrusted data must never enter innerHTML'); this.children = []; this._text = ''; }
  get innerHTML() { return this.textContent; }
  appendChild(child) { this.children.push(child); return child; }
  append(...children) { for (const child of children) this.appendChild(typeof child === 'string' ? {textContent: child} : child); }
  replaceChildren(...children) { this.children = []; this._text = ''; this.append(...children); }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  getAttribute(name) { return this.attributes[name] ?? null; }
  removeAttribute(name) { delete this.attributes[name]; }
  addEventListener(name, callback) { (this.listeners[name] ||= []).push(callback); }
  dispatchEvent(event) { event.target ||= this; for (const callback of this.listeners[event.type] || []) callback(event); return true; }
  click() { if (!this.disabled) { this.onclick?.({target: this}); this.dispatchEvent({type: 'click'}); } }
  focus() { this.focused = true; }
  querySelectorAll(selector) { return descendants(this).filter(e => selector === 'button' ? e.tagName === 'BUTTON' : false); }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}
function descendants(element) { return element.children.flatMap(child => [child, ...descendants(child)]); }
function environment(extra = {}) {
  const elements = new Map(); let now = 0, timerId = 0;
  const timers = new Map(), requests = [];
  const get = id => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const context = vm.createContext({console, AbortController, URLSearchParams, Map, Set, JSON,
    Event: class { constructor(type) { this.type = type; } },
    document: {getElementById: get, createElement: tag => new Element(tag),
      createTextNode: text => ({textContent: text}), querySelectorAll: () => [], querySelector: selector => get(selector)},
    setTimeout(callback, delay = 0) { const id = ++timerId; timers.set(id, {at: now + delay, callback}); return id; },
    clearTimeout(id) { timers.delete(id); },
    fetch(url, options) { const result = deferred(); requests.push({url, options, ...result}); return result.promise; },
    ...extra});
  context.window = context; context.SESSION_TOKEN = 'private-test-token';
  return {context, get, requests, timers,
    async tick(ms) { const end = now + ms; while (true) {
      const pending = [...timers].filter(([, t]) => t.at <= end).sort((a, b) => a[1].at - b[1].at);
      if (!pending.length) break;
      const [id, timer] = pending[0]; timers.delete(id); now = timer.at; timer.callback(); await flush();
    } now = end; await flush(); }};
}
const request = (text = '@claude raw') => ({text, selected_recipients: ['codex'], channel: 'general'});
const response = (overrides = {}) => ({mode: 'explicit', tokens: ['claude'], ignored: [],
  recipients: [{name: 'claude', identity_id: 'id-claude', online: true}], warnings: [], waiting: [], ...overrides});
function answer(call, data = response(), status = 200) {
  call.resolve({ok: status >= 200 && status < 300, status, json: async () => data});
}
function shared() {
  const env = environment();
  vm.runInContext(read('static/recipients.js') + '\nglobalThis.shared = RecipientPreview;', env.context);
  env.panel = new Element(); env.preview = env.context.shared.attach(env.panel);
  return env;
}
function composer(kind = 'channel') {
  const posts = [], checks = [], errors = [];
  let prepare = async value => response();
  const preview = {state: 'ready', schedule() {}, invalidate() {}, error: text => errors.push(text),
    prepare(value) { checks.push(plain(value)); return prepare(value); }};
  const socket = {readyState: 1, closes: [], send: value => posts.push(JSON.parse(value)),
    close(...args) { this.closes.push(args); this.readyState = 3; }};
  const env = environment({RecipientPreview: {attach: () => preview},
    WebSocket: {OPEN: 1}, ws: socket, username: 'operator',
    activeChannel: 'general', activeMentions: new Set(['claude', 'codex', 'glm']),
    pendingAttachments: [], replyingTo: null, activeJobId: 1,
    jobsData: [{id: 1, channel: 'general'}, {id: 2, channel: 'other'}],
    jobReplyTargets: {1: 'codex'}, jobPendingAttachments: [],
    SLASH_COMMANDS: [], restartVoiceAfterEdit() {}, updateSendButton() {},
    clearAttachments() { env.context.pendingAttachments.length = 0; },
    cancelReply() { env.context.replyingTo = null; },
    clearJobAttachments() { env.context.jobPendingAttachments.length = 0; },
    updateJobReplyTargetUI() {}, _normalizeJobRecipient: value => value || '',
    showSlashHint() {}, renderReplyBar() {}, saveActiveMentions() {}});
  const source = read(kind === 'channel' ? 'static/chat.js' : 'static/jobs.js');
  const marker = kind === 'channel' ? '// --- Recipient composer ---' : '// --- Recipient job composer ---';
  let start = source.indexOf(marker);
  if (start < 0) start = source.indexOf(kind === 'channel' ? 'function sendMessage() {' : 'async function sendJobMessage() {');
  const end = source.indexOf(kind === 'channel' ? '// --- Image paste/drop ---' : 'async function uploadJobImage', start);
  assert.ok(start >= 0 && end > start, 'actual-source extraction boundaries');
  vm.runInContext(source.slice(start, end) + (kind === 'channel'
    ? '\nglobalThis.sendActual = sendMessage; globalThis.eventActual = typeof handleChannelPostEvent === "function" ? handleChannelPostEvent : null; globalThis.keyActual = channelComposerKeydown;'
    : '\nglobalThis.sendActual = sendJobMessage; globalThis.keyActual = jobComposerKeydown;'), env.context);
  const input = env.get(kind === 'channel' ? 'input' : 'jobs-conv-input-text');
  input.value = '@claude review this';
  return {...env, input, posts, checks, errors, socket, preview,
    holdPrepare() { const gate = deferred(); prepare = () => gate.promise; return gate; },
    set(name, value) { env.context.__value = value; vm.runInContext(name + ' = __value;', env.context); },
    event(value, ws = socket) { return env.context.eventActual(value, ws); }};
}

test('shared preview API exists in actual script', async () => {
  const env = shared();
  for (const method of ['schedule', 'prepare', 'invalidate', 'error']) assert.equal(typeof env.preview[method], 'function');
  const html = read('static/index.html');
  assert.ok(html.indexOf('recipients.js') >= 0 && html.indexOf('recipients.js') < html.indexOf('jobs.js') && html.indexOf('recipients.js') < html.indexOf('chat.js'));
});

test('actual channel send preserves raw text and separate selected names', async () => {
  const env = composer();
  await env.context.sendActual();
  assert.equal(env.posts.length, 1);
  assert.equal(env.posts[0].text, '@claude review this');
  assert.deepEqual(env.posts[0].selected_recipients, ['claude', 'codex', 'glm']);
  assert.equal(env.checks.length, 1, 'fresh final check');
  assert.equal(env.input.value, '@claude review this', 'retain until content ACK');
});

test('shared debounce deduplicates requests and rejects stale aborted response', async () => {
  const env = shared();
  env.preview.schedule(request());
  await env.tick(249); assert.equal(env.requests.length, 0);
  await env.tick(1); assert.equal(env.requests.length, 1);
  env.preview.schedule(request()); await env.tick(250); assert.equal(env.requests.length, 1);
  env.preview.schedule(request('@codex newer')); await env.tick(250);
  assert.equal(env.requests.length, 2);
  assert.equal(env.requests[0].options.signal.aborted, true);
  answer(env.requests[1], response({recipients: [{name: 'newer', identity_id: 'new', online: true}]})); await flush();
  const current = env.panel.textContent;
  answer(env.requests[0], response({recipients: [{name: 'stale', identity_id: 'old', online: true}]})); await flush();
  assert.equal(env.panel.textContent, current);
  assert.match(current, /newer/);
});

test('shared failures and timeout block posting and Check again retries preview only', async () => {
  const env = shared();
  env.preview.schedule(request()); await env.tick(250);
  env.requests[0].reject(new Error('<private-path>')); await flush();
  assert.equal(env.preview.state, 'error');
  assert.doesNotMatch(env.panel.textContent, /private-path/);
  const retry = descendants(env.panel).find(e => e.tagName === 'BUTTON' && /check again/i.test(e.textContent));
  assert.ok(retry); retry.click(); await env.tick(250);
  assert.equal(env.requests.length, 2);
  await env.tick(8000); assert.equal(env.requests[1].options.signal.aborted, true);
  assert.equal(env.preview.state, 'error');
});

test('shared renderer uses only server audience diagnostics and text-safe content', async () => {
  const env = shared();
  const waiting = env.preview.prepare(request('unknown quoted @all'));
  answer(env.requests[0], response({tokens: ['unknown', 'all'],
    recipients: [{name: '<img onerror=boom>', identity_id: 'one', online: false}],
    ignored: [{token: 'quoted', reason: 'quote'}, {token: 'code', reason: 'code'}, {token: 'fenced', reason: 'fence'}],
    warnings: [{kind: 'unknown', token: 'unknown', candidates: []}, {kind: 'ambiguous', token: 'family', candidates: ['one', 'two']},
      {kind: 'offline', token: '<img onerror=boom>', candidates: []}],
    waiting: [{identity_id: 'one', reason: 'earlier_review_turn'}]}));
  await waiting;
  for (const text of ['<img onerror=boom>', 'unknown', 'one', 'two', 'quoted', 'code', 'fenced']) assert.ok(env.panel.textContent.includes(text));
  assert.match(env.panel.textContent, /earlier review/i);
  assert.equal(env.preview.state, 'ready');
  assert.ok(descendants(env.panel).some(e => e.getAttribute?.('aria-live') === 'polite'));
  env.preview.schedule(null); await flush();
  assert.doesNotMatch(env.panel.textContent, /img onerror/);
});

test('fresh prepare cancels changed draft and duplicate sends are single flight', async () => {
  const env = composer(); const gate = env.holdPrepare();
  const first = env.context.sendActual(); const second = env.context.sendActual();
  assert.equal(env.checks.length, 1);
  env.input.value = 'edited café\r\nraw'; gate.resolve(response());
  await Promise.all([first, second]);
  assert.equal(env.posts.length, 0); assert.equal(env.input.value, 'edited café\r\nraw');
});

test('ACK before or after broadcast clears only unchanged matching draft', async () => {
  for (const broadcastFirst of [true, false]) {
    const env = composer(); await env.context.sendActual();
    if (broadcastFirst) env.event({type: 'message', uid: 'saved', channel: 'general'});
    assert.equal(env.input.value, '@claude review this');
    env.event({type: 'message_accepted', uid: 'saved', channel: 'general'});
    if (!broadcastFirst) env.event({type: 'message', uid: 'saved', channel: 'general'});
    assert.equal(env.input.value, ''); assert.equal(env.posts.length, 1);
  }
  const env = composer(); await env.context.sendActual(); env.input.value = 'new draft';
  env.event({type: 'message_accepted', uid: 'saved', channel: 'general'});
  assert.equal(env.input.value, 'new draft');
});

test('retired socket error close and ACK timeout retain draft without resend', async () => {
  for (const type of ['message_error', 'close']) {
    const env = composer(); await env.context.sendActual();
    env.event({type, message: 'rejected'}); assert.equal(env.input.value, '@claude review this');
    assert.equal(env.posts.length, 1);
  }
  const env = composer(); await env.context.sendActual(); await env.tick(10000);
  assert.equal(env.socket.closes.length, 1); assert.equal(env.input.value, '@claude review this');
  const newer = {readyState: 1, send: value => env.posts.push(JSON.parse(value)), close() {}};
  env.set('ws', newer); await env.context.sendActual();
  env.event({type: 'message_accepted', uid: 'old', channel: 'general'}, env.socket);
  assert.equal(env.input.value, '@claude review this');
  env.event({type: 'message_accepted', uid: 'new', channel: 'general'}, newer);
  assert.equal(env.input.value, ''); assert.equal(env.posts.length, 2);
});

test('job sends exact raw text and default selection without regex inference', async () => {
  const env = composer('job'); env.input.value = ' @claude café\r\nraw ';
  const sending = env.context.sendActual(); await flush();
  assert.equal(env.requests.length, 1);
  const payload = JSON.parse(env.requests[0].options.body);
  assert.equal(payload.text, ' @claude café\r\nraw ');
  assert.deepEqual(payload.selected_recipients, ['codex']);
  assert.equal(env.checks.length, 1);
  answer(env.requests[0], {id: 1}); await sending;
  assert.equal(env.input.value, ''); assert.equal(env.context.jobReplyTargets[1], 'codex');
});

test('job duplicate context mutation and HTTP failure preserve current draft', async () => {
  const env = composer('job'); const gate = env.holdPrepare();
  const first = env.context.sendActual(), second = env.context.sendActual();
  assert.equal(env.checks.length, 1); env.set('activeJobId', 2); env.input.value = 'other job';
  gate.resolve(response()); await Promise.all([first, second]);
  assert.equal(env.requests.length, 0); assert.equal(env.input.value, 'other job');
  const failed = composer('job'); const sending = failed.context.sendActual(); await flush();
  answer(failed.requests[0], {}, 503); await sending;
  assert.equal(failed.input.value, '@claude review this'); assert.equal(failed.requests.length, 1);
  assert.ok(failed.errors.length > 0);
});

test('local commands bypass preview and composing IME Enter cannot post', async () => {
  for (const text of ['/clear x', '/CONTINUE x']) {
    const env = composer(); env.input.value = text; await env.context.sendActual();
    assert.equal(env.checks.length, 0); assert.equal(env.posts[0].text, text);
  }
  for (const kind of ['channel', 'job']) {
    const ime = composer(kind);
    ime.context.keyActual({key: 'Enter', isComposing: true, shiftKey: false,
      preventDefault() { throw new Error('composing Enter must remain with IME'); }});
    await flush(); assert.equal(ime.checks.length, 0); assert.equal(ime.posts.length, 0); assert.equal(ime.requests.length, 0);
  }
  const env = composer(); env.input.value = '/roastreview'; await env.context.sendActual();
  assert.equal(env.checks.length, 1); assert.equal(env.posts[0].text, '/roastreview');
});

test('attachment reply and channel mutations preserve the newer composer context', async () => {
  for (const mutate of [env => env.set('activeChannel', 'other'),
    env => env.context.pendingAttachments.push({path: 'new', name: '@all.txt'}),
    env => env.set('replyingTo', {id: 0})]) {
    const env = composer(); const gate = env.holdPrepare();
    const sending = env.context.sendActual(); mutate(env); gate.resolve(response()); await sending;
    assert.equal(env.posts.length, 0); assert.equal(env.input.value, '@claude review this');
  }
  const env = composer(); await env.context.sendActual(); env.set('activeChannel', 'other');
  env.input.value = 'other channel draft';
  env.event({type: 'message_accepted', uid: 'saved', channel: 'general'});
  assert.equal(env.input.value, 'other channel draft');
});

(async () => {
  let failures = 0;
  for (const {name, run} of cases) {
    try { await run(); console.log('PASS ' + name); }
    catch (error) { failures++; console.error('FAIL ' + name + '\n' + error.stack); }
  }
  console.log(JSON.stringify({cases: cases.length, failures, scope: 'actual_source_vm_only'}));
  process.exitCode = failures ? 1 : 0;
})();
