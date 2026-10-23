"""Exercise actual session UI state and recovery actions in a minimal DOM."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('node'), 'Node required for actual sessions.js behavior')
class RestartUITests(unittest.TestCase):
    def test_interrupted_cold_run_stays_visible_and_saved_retry_is_explicit(self):
        script = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert');
class Element {
  constructor(tag) { this.tagName = tag; this.children = []; this.dataset = {}; this.style = {}; this.hidden = false; this._text = ''; }
  set textContent(value) { this._text = String(value); }
  get textContent() { return this._text + this.children.map(c => typeof c === 'string' ? c : c.textContent).join(' '); }
  append(...children) { this.children.push(...children); }
  appendChild(child) { this.children.push(child); return child; }
  replaceChildren(...children) { this.children = children; this._text = ''; }
  setAttribute(name, value) { this[name] = value; }
  querySelectorAll(selector) {
    const found = [];
    for (const child of this.children) if (typeof child !== 'string') {
      if (selector.startsWith('.') ? (child.className || '').split(' ').includes(selector.slice(1)) : child.tagName === selector) found.push(child);
      found.push(...child.querySelectorAll(selector));
    }
    return found;
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}
const nodes = new Map(), panel = new Element('section');
nodes.set('session-turn-controls', panel);
const context = vm.createContext({console, crypto: require('crypto').webcrypto, setInterval() {},
  window: {activeChannel: 'review', escapeHtml: text => text}, Hub: {on() {}}, Store: {watch() {}},
  document: {getElementById: id => nodes.get(id) || null, createElement: tag => new Element(tag)}, calls: []});
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), context);
context.fixture = {id: 1, channel: 'review', state: 'interrupted', completion_protocol: 1, legacy: false,
  restart_recovery: {boot_id: 'boot', status: 'interrupted'}, dispatch_eligible: false,
  turn_recovery: {checkpoint_id: 'checkpoint', attempt_id: 'old-attempt', status: 'stalled', reason: 'restart_unverified'},
  active_invocation: {attempt_id: 'old-attempt', expected_agent: 'old-seat', role: 'reviewer'},
  participant_bindings: {reviewer: {launch_provenance: {effective: {seat: {adapter: 'openai-compatible', name: 'Frozen reviewer'}}}}},
  admitted_events: [{kind: 'final', content: 'Prior work'}], recovery_policy: {ack_timeout: 30, response_timeout: 900}};
vm.runInContext('updateSessionBar = () => {}; handleSessionEvent("update", fixture); globalThis.selected = activeSession;', context);
assert.strictEqual(context.selected?.id, 1, 'recoverable interruption must remain selected after a live update');
vm.runInContext('renderSessionTurnControls({});', context);
assert.strictEqual(panel.hidden, false, 'interrupted run must expose recovery controls');
assert(panel.querySelectorAll('button').some(b => b.textContent === 'Retry this turn'));
assert(panel.querySelector('.session-recovery-status').textContent.includes('ownership'));
assert(panel.querySelector('.session-recovery-status').textContent.startsWith('Frozen reviewer'));
// Historical interruption without restart evidence retains its old dismissed semantics.
context.legacy = {...context.fixture, id: 2, restart_recovery: undefined};
vm.runInContext('handleSessionEvent("interrupt", legacy); globalThis.selected = activeSession;', context);
assert.strictEqual(context.selected, null);
context.fixture = {...context.fixture, id: 3,
  turn_recovery: {...context.fixture.turn_recovery, status: 'retrying'},
  pending_retry: {status: 'preparing_contexts', checkpoint_id: 'checkpoint', request_id: 'same-request',
    old_invocation: {attempt_id: 'old-attempt'}, context: {state: 'starting', launch_attempt: 'prepared-launch'}}};
vm.runInContext(`activeSession = fixture; renderSessionTurnControls({});
  restartRequest = async (id, action, body) => { calls.push({id, action, body}); return {...fixture, state: 'retrying'}; };
  refreshRecoveryStatus = async () => {};`, context);
const resume = panel.querySelectorAll('button').find(b => b.textContent === 'Resume saved retry');
assert(resume, 'old-boot pending preparation needs an explicit resume action');
assert.strictEqual(context.calls.length, 0, 'rendering must never submit a retry');
(async () => {
  await resume.onclick();
  assert.strictEqual(context.calls.length, 1);
  assert.strictEqual(context.calls[0].action, 'retry');
  assert.deepStrictEqual(JSON.parse(JSON.stringify(context.calls[0].body)), {
    checkpoint_id: 'checkpoint', attempt_id: 'old-attempt', request_id: 'same-request'});
  vm.runInContext('renderSessionTurnControls({});', context);
  assert(!panel.querySelectorAll('button').some(b => b.textContent === 'Resume saved retry'),
    'resume action must disappear once the same saved intent is retrying');
  console.log('restart-ui PASS');
})().catch(error => { console.error(error); process.exitCode = 1; });
'''
        result = subprocess.run([shutil.which('node'), '-e', script, str(ROOT / 'static/sessions.js')],
                                capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('restart-ui PASS', result.stdout)


if __name__ == '__main__':
    unittest.main()
