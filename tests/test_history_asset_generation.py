"""Keep history rendering safe when browser assets come from mixed generations."""
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HistoryAssetGenerationTests(unittest.TestCase):
    def test_history_renders_with_current_core_and_rejects_stale_generation(self):
        script = r"""
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const root = process.argv[1];
const coreSource = fs.readFileSync(root + '/static/core.js', 'utf8');
const chatSource = fs.readFileSync(root + '/static/chat.js', 'utf8');
const start = (source, name) => source.indexOf('function ' + name + '(');
const end = (source, name, next) => source.indexOf('function ' + next + '(', start(source, name));
const appendSource = chatSource.slice(start(chatSource, 'appendMessage'), end(chatSource, 'appendMessage', 'getSenderClass'));
const historySource = chatSource.slice(start(chatSource, 'renderHistoryBatch'), end(chatSource, 'renderHistoryBatch', 'handleServerEvent'));
const displayBlockStart = coreSource.indexOf('// Display aliases are separate');
const displayBlockEnd = coreSource.indexOf('window.agentDisplayName = agentDisplayName;', displayBlockStart) + 'window.agentDisplayName = agentDisplayName;'.length;
assert(displayBlockStart >= 0 && displayBlockEnd > displayBlockStart, 'could not isolate display helper from current core');
const staleCore = coreSource.slice(0, displayBlockStart) + coreSource.slice(displayBlockEnd);

function run(core) {
  const rendered = [];
  const container = { appendChild(node) { rendered.push(...(node.children || [node])); } };
  const sandbox = {
    console,
    window: null,
    agentDisplayLabels: { 'cli-12345678-': 'Codex Sol' },
    activeChannel: 'general',
    username: 'Seth',
    agentConfig: {},
    todos: {},
    agentHats: {},
    _agentRoles: {},
    channelUnread: {},
    autoScroll: false,
    soundEnabled: false,
    pendingHistory: [{ id: 1, type: 'chat', sender: 'cli-12345678-old', channel: 'general', text: 'message one' }],
    pendingLiveEvents: [],
    historyReceived: true,
    historyLoading: true,
    historyScheduled: true,
    document: {
      getElementById(id) { return id === 'messages' ? container : null; },
      createDocumentFragment() {
        return { children: [], appendChild(node) { this.children.push(node); }, querySelectorAll() { return []; } };
      },
      createElement() {
        return { dataset: {}, style: {}, classList: { add() {} }, appendChild() {}, querySelector() { return null; } };
      },
      querySelector() { return null; }
    },
    maybeInsertDateDivider() {},
    getColor() { return '#123456'; },
    resolveAgent() { return null; },
    getAvatarSvg() { return ''; },
    todoStatusLabel() { return ''; },
    styleHashtags(value) { return value; },
    renderMarkdown(value) { return value; },
    addCodeCopyButtons() {},
    RecipientPreview: { appendReceipt() {} },
    escapeHtml(value) { return String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;'); },
    setHistoryIndicator() {},
    scrollToBottom() {},
    handleServerEvent() {}
  };
  sandbox.window = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(core, sandbox);
  sandbox.agentDisplayLabels = { 'cli-12345678-': 'Codex Sol' };
  vm.runInContext(appendSource + '\n' + historySource, sandbox);
  let error = null;
  try { vm.runInContext('renderHistoryBatch()', sandbox); } catch (caught) { error = caught; }
  return { sandbox, rendered, error };
}

const stale = run(staleCore);
assert(stale.error instanceof Error || stale.error?.name === 'ReferenceError', 'stale core should reproduce the missing display helper failure');
assert.equal(stale.sandbox.historyLoading, true, 'failed batch leaves history marked as loading');

const current = run(coreSource);
assert.equal(current.error, null, current.error?.stack);
assert.equal(current.sandbox.historyLoading, false, 'successful history render clears the loading state');
assert.equal(current.rendered.length, 1, 'history message is appended');
assert(current.rendered[0].innerHTML.includes('Codex Sol'), 'history shows the friendly sender label');
assert(current.rendered[0].innerHTML.includes('message one'), 'history shows message text');

const html = fs.readFileSync(root + '/static/index.html', 'utf8');
assert(!html.includes('/static/core.js?v=223'), 'index must not reuse the stale Desktop core URL');
"""
        result = subprocess.run(
            ["node", "-e", script, str(ROOT)], capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
