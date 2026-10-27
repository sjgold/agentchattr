"""Help guide in static/chat.js (docked panel + first-visit welcome card).

Only the block between '// --- Help Guide' and '// --- Start ---' is extracted and
run in a Node `vm` with a tiny fake DOM, so the rest of chat.js is not loaded.
"""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

BOOT = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const root=process.argv[2], nodes=new Map(), timers=[], store=new Map(), docListeners={};
class Element {
 constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.attrs={};this.className='';this.parentElement=null;this._text='';this._html='';this.listeners={}}
 set id(v){this._id=v;nodes.set(v,this)} get id(){return this._id}
 set textContent(v){this._text=String(v);this.children=[]} get textContent(){return this._text+this.children.map(c=>c.textContent).join('')}
 set innerHTML(v){this._html=String(v)} get innerHTML(){return this._html}
 appendChild(c){this.children.push(c);c.parentElement=this;return c}
 remove(){if(this.parentElement)this.parentElement.children=this.parentElement.children.filter(c=>c!==this);this.parentElement=null;if(this.id&&nodes.get(this.id)===this)nodes.delete(this.id)}
 setAttribute(k,v){this.attrs[k]=String(v)} getAttribute(k){return this.attrs[k]??null}
 addEventListener(k,fn){(this.listeners[k]??=[]).push(fn)}
 focus(){}
 contains(n){for(;n;n=n.parentElement)if(n===this)return true;return false}
 hasClass(c){return this.className.split(/\s+/).includes(c)}
 all(){return this.children.flatMap(c=>[c,...c.all()])}
 querySelector(sel){return this.all().find(e=>sel[0]==='#'?e.id===sel.slice(1):sel[0]==='.'?e.hasClass(sel.slice(1)):e.tagName===sel.toUpperCase())||null}
}
const body=new Element('body');
const document={body,createElement:t=>new Element(t),getElementById:id=>nodes.get(id)||null,
 addEventListener(k,fn){(docListeners[k]??=[]).push(fn)},removeEventListener(k,fn){docListeners[k]=(docListeners[k]||[]).filter(f=>f!==fn)}};
const helpBtn=new Element('button');helpBtn.id='help-btn';body.appendChild(helpBtn);
const outside=new Element('div');body.appendChild(outside);
const localStorage={getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)};
let timerID=0;
const context=vm.createContext({document,localStorage,console,setTimeout:(fn,ms)=>{timers.push({id:++timerID,fn,ms});return timerID},window:{}});
const src=fs.readFileSync(root+'/static/chat.js','utf8');
const a=src.indexOf('// --- Help Guide'),b=src.indexOf('// --- Start ---');
assert(a>=0&&b>a,'help block markers not found');
vm.runInContext(src.slice(a,b),context,{filename:'static/chat.js#help'});
const run=code=>vm.runInContext(code,context);
const guide=()=>document.getElementById('help-guide');
const fireTimers=ms=>{for(const t of timers.filter(t=>ms===undefined||t.ms===ms)){timers.splice(timers.indexOf(t),1);t.fn()}};
const fireDoc=(kind,e)=>(docListeners[kind]||[]).slice().forEach(fn=>fn(e));
const noBackdrop=()=>{assert(!body.all().some(e=>e.hasClass('hg-backdrop')||e.innerHTML.includes('hg-backdrop')),'blocking backdrop present')};
"""


class HelpOverlayTests(unittest.TestCase):
    def run_js(self, body):
        node = shutil.which('node')
        self.assertIsNotNone(node, 'Node is required for the actual JS UI tests')
        script = BOOT + '\n' + body + '\nprocess.stdout.write("HELP_UI_CASE_COMPLETED\\n");'
        result = subprocess.run([node, '-', str(ROOT)], input=script, cwd=ROOT, capture_output=True,
                                text=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count('HELP_UI_CASE_COMPLETED'), 1, result.stderr)

    def test_first_visit_schedules_welcome_card_without_backdrop(self):
        self.run_js(r"""
run('initHelpTour()');
assert.strictEqual(timers.length,1);assert.strictEqual(timers[0].ms,2500);
assert.strictEqual(guide(),null,'nothing opens before the delay');
fireTimers(2500);
assert(guide(),'welcome card missing');
assert(guide().hasClass('help-guide--welcome'));assert(!guide().hasClass('help-guide--panel'));
noBackdrop();
""")

    def test_returning_visitor_gets_no_welcome(self):
        self.run_js(r"""
localStorage.setItem('help_seen','1');
run('initHelpTour()');
assert.strictEqual(timers.length,0);assert.strictEqual(guide(),null);
""")

    def test_panel_has_close_button_and_preflight_module(self):
        self.run_js(r"""
run('openHelp()');
const g=guide();
assert(g.hasClass('help-guide--panel'));noBackdrop();
const close=g.all().find(e=>e.tagName==='BUTTON'&&e.getAttribute('aria-label')==='Close guide');
assert(close,'close button missing');
const first=g.querySelector('.hg-module');
assert.strictEqual(first.id,'hg-preflight');
assert(first.innerHTML.includes('href="/preflight"'),first.innerHTML);
""")

    def test_escape_closes_and_remembers(self):
        self.run_js(r"""
run('openHelp()');localStorage.removeItem('help_seen');
fireDoc('keydown',{key:'Enter'});assert(guide(),'only Escape closes');
fireDoc('keydown',{key:'Escape'});
assert.strictEqual(guide(),null);assert.strictEqual(localStorage.getItem('help_seen'),'1');
""")

    def test_outside_mousedown_closes_but_help_button_and_inside_do_not(self):
        self.run_js(r"""
run('openHelp()');fireTimers(0);
fireDoc('mousedown',{target:helpBtn});assert(guide(),'help button press is handled by toggleHelp');
fireDoc('mousedown',{target:guide().querySelector('.hg-module')});assert(guide(),'click inside must not close');
fireDoc('mousedown',{target:outside});
assert.strictEqual(guide(),null);assert.strictEqual(localStorage.getItem('help_seen'),'1');
""")

    def test_toggle_opens_then_closes_panel(self):
        self.run_js(r"""
run('toggleHelp()');assert(guide()&&guide().hasClass('help-guide--panel'));
run('toggleHelp()');assert.strictEqual(guide(),null);
""")


if __name__ == '__main__':
    unittest.main()
