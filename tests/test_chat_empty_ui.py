"""Chat empty states in static/chat.js.

Only the block between '// --- Empty states ---' and '// --- End empty states ---'
is extracted and run in a Node `vm` with a tiny fake DOM (innerHTML throws, so any
text path that bypasses textContent/DOM nodes fails).
"""
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
START = '// --- Empty states ---'
END = '// --- End empty states ---'

BOOT = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const root=process.argv[2], nodes=new Map();
class Element {
 constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.dataset={};this.attrs={};this.hidden=false;this._text='';this.className='';this.parentElement=null;this.href='';
  this.classList={contains:n=>this.className.split(/\s+/).includes(n)}}
 set id(v){this._id=v;nodes.set(v,this)} get id(){return this._id}
 set textContent(v){this.children=[];this._text=String(v)}
 get textContent(){return this._text+this.children.map(c=>c.textContent).join('')}
 set innerHTML(v){throw Error('empty states must use textContent/DOM nodes, never innerHTML')}
 get childElementCount(){return this.children.length} get firstElementChild(){return this.children[0]||null} get firstChild(){return this.children[0]||null}
 hasChildNodes(){return this.children.length>0}
 append(...items){for(const c of items){this.children.push(c);c.parentElement=this}}
 appendChild(c){this.append(c);return c}
 setAttribute(k,v){this.attrs[k]=String(v)} getAttribute(k){return this.attrs[k]??null}
}
const document={getElementById:id=>nodes.get(id)||null,createElement:t=>new Element(t),createTextNode:t=>{const n=new Element('#text');n.textContent=t;return n}};
const win={activeChannel:'general'};
const context=vm.createContext({document,window:win,console,agentConfig:{}});
const src=fs.readFileSync(root+'/static/chat.js','utf8');
const a=src.indexOf('// --- Empty states ---'),b=src.indexOf('// --- End empty states ---');
assert(a>=0&&b>a,'empty-state block markers missing from static/chat.js');
vm.runInContext(src.slice(a,b),context,{filename:'static/chat.js#empty'});
const run=code=>vm.runInContext(code,context);
const make=(tag,id)=>{const e=new Element(tag);if(id)e.id=id;return e};
const empty=make('div','chat-empty'),messages=make('div','messages'),loader=make('div','loading-indicator');
loader.className='hidden';
const addMsg=(id,channel)=>{const m=make('div');m.dataset.id=String(id);if(channel!==undefined)m.dataset.channel=channel;messages.appendChild(m);return m};
const setAgents=obj=>{context.agentConfig=obj};
"""


class ChatEmptyStateTests(unittest.TestCase):
    def run_js(self, body):
        node = shutil.which('node')
        self.assertIsNotNone(node, 'Node is required for the actual JS UI tests')
        source = (ROOT / 'static/chat.js').read_text(encoding='utf-8')
        self.assertIn(START, source, 'empty-state block marker missing from static/chat.js: ' + START)
        self.assertIn(END, source, 'empty-state block marker missing from static/chat.js: ' + END)
        script = BOOT + '\n' + body + '\nprocess.stdout.write("CHAT_EMPTY_CASE_COMPLETED\\n");'
        result = subprocess.run([node, '-', str(ROOT)], input=script, cwd=ROOT, capture_output=True,
                                text=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count('CHAT_EMPTY_CASE_COMPLETED'), 1, result.stderr)

    # 1. No-agents hint ------------------------------------------------------
    def test_no_agents_hint_added_to_empty_container(self):
        self.run_js(r"""
const c=make('div');
run('renderNoAgentsHint')(c);
assert.strictEqual(c.children.length,1);
const link=c.children[0];
assert.strictEqual(link.tagName,'A');
assert.strictEqual(link.className,'no-agents-hint');
assert.strictEqual(link.href,'/preflight');
assert.strictEqual(link.textContent,'No agents running · Seats & launch');
""")

    def test_no_agents_hint_skipped_when_container_has_children(self):
        self.run_js(r"""
const c=make('div');c.appendChild(make('div'));
run('renderNoAgentsHint')(c);
assert.strictEqual(c.children.length,1,'must not add a hint next to existing pills');
assert.notStrictEqual(c.children[0].className,'no-agents-hint');
""")

    # 12. Empty chat state ---------------------------------------------------
    def test_empty_chat_shows_mention_prompt_with_first_agent_label(self):
        self.run_js(r"""
setAgents({claude:{label:'Claude Prime'},codex:{}});
run('updateChatEmptyState')();
assert.strictEqual(empty.hidden,false);
assert.strictEqual(empty.textContent,'No messages yet. Mention @Claude Prime, or press the play button to start a session');
setAgents({codex:{}});
run('updateChatEmptyState')();
assert.strictEqual(empty.textContent,'No messages yet. Mention @codex, or press the play button to start a session');
""")

    def test_empty_chat_without_agents_gives_generic_prompt(self):
        self.run_js(r"""
setAgents({});
run('updateChatEmptyState')();
assert.strictEqual(empty.hidden,false);
assert.strictEqual(empty.textContent,'No messages yet. Mention an agent with @, or press the play button to start a session');
""")

    def test_empty_state_hidden_when_active_channel_has_messages(self):
        self.run_js(r"""
setAgents({claude:{}});
addMsg(1);  // no dataset.channel means general
run('updateChatEmptyState')();
assert.strictEqual(empty.hidden,true);
""")

    def test_messages_in_other_channels_do_not_count(self):
        self.run_js(r"""
setAgents({claude:{}});
addMsg(1,'review');
run('updateChatEmptyState')();
assert.strictEqual(empty.hidden,false,'other-channel message must not hide the empty state');
win.activeChannel='review';
run('updateChatEmptyState')();
assert.strictEqual(empty.hidden,true);
win.activeChannel='general';
run('updateChatEmptyState')();
assert.strictEqual(empty.hidden,false);
""")

    def test_children_without_message_id_do_not_count(self):
        self.run_js(r"""
setAgents({claude:{}});
messages.appendChild(make('div'));  // e.g. a date divider
run('updateChatEmptyState')();
assert.strictEqual(empty.hidden,false);
""")

    def test_empty_state_hidden_while_loading(self):
        self.run_js(r"""
setAgents({claude:{}});
loader.className='';
run('updateChatEmptyState')();
assert.strictEqual(empty.hidden,true,'loading indicator visible: stay hidden');
loader.className='hidden';
run('updateChatEmptyState')();
assert.strictEqual(empty.hidden,false);
""")

    # Static wiring ----------------------------------------------------------
    def test_build_status_pills_renders_no_agents_hint(self):
        source = (ROOT / 'static/chat.js').read_text(encoding='utf-8')
        start = source.index('function buildStatusPills')
        end = source.index('\n}\n', start)
        self.assertIn('renderNoAgentsHint(container)', source[start:end])

    def test_index_has_chat_empty_inside_timeline(self):
        html = (ROOT / 'static/index.html').read_text(encoding='utf-8')
        main = re.search(r'<main\b[^>]*\bid="timeline"[^>]*>.*?</main>', html, re.S)
        self.assertIsNotNone(main, '<main id="timeline"> not found')
        self.assertRegex(main.group(0), r'\bid="chat-empty"')


if __name__ == '__main__':
    unittest.main()
