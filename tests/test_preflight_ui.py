"""Pre-flight page UI: the actual static/preflight.js + static/api_seats.js run in
Node `vm` against a small fake DOM, fake fetch and fake timers. The fake DOM's
innerHTML setter throws, so any untrusted-text path that bypasses textContent fails.
"""
from pathlib import Path
import json
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

BOOT = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const root=process.argv[2], nodes=new Map(), timers=new Map(), calls=[], assigned=[];
let timerID=0, responder;
const store=new Map();
class Element {
 constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.dataset={};this.style={};this.attrs={};this.hidden=false;this.disabled=false;
  this.value='';this.checked=false;this.open=false;this._text='';this.listeners={};this.className='';this.parentElement=null;
  this.classList={contains:n=>this.className.split(/\s+/).includes(n),add:(...n)=>{this.className=(this.className+' '+n.join(' ')).trim()},
   remove:(...n)=>{this.className=this.className.split(/\s+/).filter(c=>c&&!n.includes(c)).join(' ')},
   toggle:(n,f)=>{const has=this.classList.contains(n),want=f===undefined?!has:!!f;if(want&&!has)this.classList.add(n);if(!want&&has)this.classList.remove(n);return want}};}
 set id(v){this._id=v;nodes.set(v,this)} get id(){return this._id}
 set textContent(v){for(const c of this.children)c.parentElement=null;this.children=[];this._text=String(v)}
 get textContent(){return this._text+this.children.map(c=>c.textContent).join('')}
 set innerHTML(v){throw Error('pre-flight UI must use textContent/DOM nodes, never innerHTML')}
 append(...items){for(const c of items){this.children.push(c);c.parentElement=this}}
 appendChild(c){this.append(c);return c}
 replaceChildren(...items){for(const c of this.children)c.parentElement=null;this.children=[];this._text='';this.append(...items)}
 remove(){if(this.parentElement)this.parentElement.children=this.parentElement.children.filter(c=>c!==this);this.parentElement=null;
  if(this.id&&nodes.get(this.id)===this)nodes.delete(this.id)}
 setAttribute(k,v){this.attrs[k]=String(v)} getAttribute(k){return this.attrs[k]??null}
 addEventListener(k,fn){(this.listeners[k]??=[]).push(fn)} removeEventListener(){}
 closest(tag){for(let n=this;n;n=n.parentElement)if(n.tagName===tag.toUpperCase())return n;return null}
 focus(){}
 async dispatch(kind,extra={}){if(kind==='click'&&this.disabled)return;let stop=false;
  const e={type:kind,target:this,preventDefault(){},stopPropagation(){stop=true},...extra};
  for(let n=this;n&&!stop;n=n.parentElement){e.currentTarget=n;for(const fn of n.listeners[kind]||[])await fn(e)}}
 click(){return this.dispatch('click')}
 matches(sel){if(sel[0]==='#')return this.id===sel.slice(1);const m=/^([a-z0-9]*)(?:\.([\w-]+))?$/i.exec(sel);if(!m)return false;
  return (!m[1]||this.tagName===m[1].toUpperCase())&&(!m[2]||this.classList.contains(m[2]))}
 querySelectorAll(sel){const out=[];for(const c of this.children){if(c.matches(sel))out.push(c);out.push(...c.querySelectorAll(sel))}return out}
 querySelector(sel){return this.querySelectorAll(sel)[0]||null}
}
const body=new Element('body');
const document={body,getElementById:id=>nodes.get(id)||null,createElement:t=>new Element(t),
 createTextNode:t=>{const n=new Element('#text');n.textContent=t;return n}};
const PAGE_IDS=[['server-status','p'],['refresh','button'],['agents','div'],['checked-at','span'],['api-seat-status','p'],['api-package-select','select'],
 ['api-package-id','input'],['api-package-name','input'],['api-package-form','form'],['api-seat-editors','div'],['team-go','button'],['team-launch','button'],
 ['team-chat','button'],['team-launch-status','p'],['api-package-reload','button'],['api-package-new','button'],['api-seat-add','button'],
 ['agents-details','details'],['agents-summary','summary']];
const page={};
for(const [id,tag] of PAGE_IDS){const e=new Element(tag);e.id=id;body.append(e);page[id]=e}
page['agents-details'].open=true;
const form=page['api-package-form'];form.reportValidity=()=>true;
form.append(page['api-package-name'],page['api-package-id'],page['api-seat-editors']);
page['team-go'].disabled=true;
const later=(fn,ms)=>{timers.set(++timerID,{fn,ms});return timerID};
const window={__SESSION_TOKEN__:'TOKEN-123',location:{origin:'http://127.0.0.1:49960',assign:u=>assigned.push(u)}};
const localStorage={getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)};
const response=(data,status=200)=>({ok:status>=200&&status<300,status,json:async()=>JSON.parse(JSON.stringify(data))});
const context=vm.createContext({window,document,localStorage,console,crypto:require('crypto').webcrypto,AbortSignal,Promise,Date,Object,JSON,Set,URL,
 setTimeout:later,clearTimeout:id=>timers.delete(id),
 fetch:async(url,options={})=>{url=String(url);const call={url,method:options.method||'GET',headers:options.headers||{},
  body:options.body===undefined?undefined:JSON.parse(options.body)};calls.push(call);return responder(call)}});
function load(){for(const f of ['static/preflight.js','static/api_seats.js'])vm.runInContext(fs.readFileSync(root+'/'+f,'utf8'),context,{filename:f})}
const flush=()=>new Promise(r=>setImmediate(r));
// Flush microtasks, firing the earliest fake timer whenever the condition is not yet true.
async function until(cond,what){for(let i=0;i<300;i++){await flush();if(cond())return;const next=timers.entries().next().value;
 if(next){timers.delete(next[0]);next[1].fn()}}assert(cond(),'Timed out waiting for '+what)}
const posts=()=>calls.filter(c=>c.method==='POST');
const seatCard=id=>page['api-seat-editors'].children.find(e=>e.dataset.savedId===id);
const textInputs=card=>card.querySelectorAll('input').filter(i=>i.type!=='checkbox');
const goButton=()=>page['team-go'];

const TEAM={id:'team',name:'Team',seats:[
 {id:'alpha',name:'Alpha',provider:'p1',adapter:'openai-compatible',model:null,reasoning:null,secret_ref:'KEY_ENV'},
 {id:'beta',name:'Beta',provider:'p1',adapter:'openai-compatible',model:null,reasoning:null,secret_ref:'KEY_ENV'}]};
let seatsSnapshot, launches, launchReply, statusReply, chatReply;
function resetFixture(){
 launches={};launchReply=null;statusReply=null;chatReply={url:'/chat/team'};
 seatsSnapshot=()=>({providers:[{id:'p1',name:'Prov One',adapter:'openai-compatible',models:['m1'],default_model:'m1',reasoning_efforts:[],secret_ref:'KEY_ENV'}],
  packages:[TEAM],package_revisions:{team:'r1'},package_launches:launches,runtime:{}});
 responder=async call=>{
  if(call.url==='/api/preflight')return response({checked_at:'2026-10-27T00:00:00Z',agents:[]});
  if(call.url==='/api/preflight/seats')return response(seatsSnapshot());
  if(call.url==='/api/preflight/packages')return response({id:'team'});
  if(call.url==='/api/preflight/packages/team/launch'){launches.team=launchReply(call.body);return response(launches.team)}
  if(call.url==='/api/preflight/packages/team/status'){launches.team=statusReply();return response(launches.team)}
  if(call.url==='/api/preflight/packages/team/chat')return response(chatReply);
  return response({error:'unexpected '+call.url},404);
 };
}
resetFixture();
const readyState=(selection,omitted=[])=>({selection_id:selection,ready:true,state:'ready',omitted_seats:omitted,
 seats:Object.fromEntries(TEAM.seats.filter(s=>!omitted.includes(s.id)).map(s=>[s.id,{state:'ready',name:s.id}]))});
async function boot(){load();await until(()=>goButton().disabled===false||page['api-seat-status'].textContent!==''||page['team-launch-status'].textContent!=='','initial render')}
"""


class PreflightUITests(unittest.TestCase):
    def run_js(self, body):
        node = shutil.which('node')
        self.assertIsNotNone(node, 'Node is required for the actual JS UI tests')
        script = BOOT + '\n(async()=>{\n' + body + '\nprocess.stdout.write("PREFLIGHT_UI_CASE_COMPLETED\\n");\n})().catch(e=>{console.error(e.stack);process.exitCode=1});'
        result = subprocess.run([node, '-', str(ROOT)], input=script, cwd=ROOT, capture_output=True,
                                text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count('PREFLIGHT_UI_CASE_COMPLETED'), 1, result.stderr)

    # 1. Agents list --------------------------------------------------------
    def test_agents_render_honest_chips_and_send_session_token(self):
        self.run_js(r"""
const base=responder;
responder=async call=>call.url==='/api/preflight'?response({checked_at:'2026-10-27T00:00:00Z',agents:[
 {name:'api1',label:'Hosted API',client_type:'api',authentication:'unknown',ready:false},
 {name:'cli1',label:'Local CLI',client_type:'cli',executable_found:false,authentication:'unknown',ready:false},
 {name:'cli2',label:'Ready CLI',client_type:'cli',executable_found:true,executable:'C:/x.exe',version:'1.2',authentication:'ok',ready:true}]}):base(call);
await boot();
const cards=page['agents'].querySelectorAll('.pf-agent');
assert.strictEqual(cards.length,3);
const chips=card=>card.querySelectorAll('.pf-chip').map(c=>c.textContent);
assert(chips(cards[0]).includes('Program: not needed'),chips(cards[0]).join('|'));
assert(chips(cards[1]).includes('Program: not found on PATH'),chips(cards[1]).join('|'));
assert(chips(cards[0]).includes('Sign-in: unknown'));
assert(chips(cards[1]).includes('Sign-in: unknown'));
assert(chips(cards[0]).includes('Ready: not verified'));
assert(chips(cards[1]).includes('Ready: not verified'));
assert(chips(cards[2]).includes('Ready: yes'));
assert(chips(cards[2]).includes('Program: found'));
assert.strictEqual(page['server-status'].textContent,'Local server running');
assert(calls.length>0);
for(const c of calls)assert.strictEqual(c.headers['x-session-token'],'TOKEN-123',c.url+' missing session token');
""")

    def test_empty_agent_list_shows_message_and_config_hint(self):
        self.run_js(r"""
await boot();
const empty=page['agents'].querySelector('.pf-empty');
assert(empty,'no empty state');
assert(empty.textContent.includes('No agents configured yet.'));
assert(empty.textContent.includes('config.toml'));
assert.strictEqual(page['agents'].querySelectorAll('.pf-agent').length,0);
""")

    def test_fetch_failure_reports_server_checks_failed(self):
        self.run_js(r"""
const base=responder;
responder=async call=>call.url==='/api/preflight'?response({error:'nope'},500):base(call);
await boot();
assert.strictEqual(page['server-status'].textContent,'Server checks failed');
assert(page['server-status'].classList.contains('error'));
assert(page['agents'].textContent.includes('Checks failed.'));
assert.strictEqual(page['refresh'].disabled,false);
""")

    # 1b. Agents summary + collapse, exited seats, wrapper launch commands ----
    def test_agents_summary_counts_available_and_missing(self):
        self.run_js(r"""
const base=responder;
const set=agents=>{responder=async call=>call.url==='/api/preflight'?response({checked_at:'2026-10-27T00:00:00Z',agents}):base(call)};
set([{name:'api1',label:'Hosted API',client_type:'api',authentication:'unknown',ready:false},
 {name:'cli1',label:'Local CLI',client_type:'cli',executable_found:false,authentication:'unknown',ready:false}]);
await boot();
await until(()=>page['agents'].querySelectorAll('.pf-agent').length===2,'agent cards');
assert.strictEqual(page['agents-summary'].textContent,'Available agents: 2 \u00b7 1 not found');
""")
        self.run_js(r"""
const base=responder;
responder=async call=>call.url==='/api/preflight'?response({checked_at:'2026-10-27T00:00:00Z',agents:[
 {name:'a',client_type:'api'},{name:'b',client_type:'cli',executable_found:true,executable:'C:/bin/b.exe'},{name:'c',client_type:'api'}]}):base(call);
await boot();
await until(()=>page['agents'].querySelectorAll('.pf-agent').length===3,'agent cards');
assert.strictEqual(page['agents-summary'].textContent,'Available agents: 3');
""")
        self.run_js(r"""
await boot();
await until(()=>page['agents'].querySelector('.pf-empty'),'empty state');
assert.strictEqual(page['agents-summary'].textContent,'No agents configured');
""")

    def test_agents_details_collapses_when_saved_team_autoloads(self):
        self.run_js(r"""
await boot();
await until(()=>page['agents-summary'].textContent!=='','summary text');
assert.strictEqual(page['agents-details'].open,false,'saved team present: agents section should collapse');
""")

    def test_agents_details_stays_open_without_saved_teams(self):
        self.run_js(r"""
const base=seatsSnapshot;seatsSnapshot=()=>({...base(),packages:[],package_revisions:{}});
await boot();
await until(()=>page['agents-summary'].textContent!=='','summary text');
assert.strictEqual(page['agents-details'].open,true);
""")

    def test_exited_seat_chip_says_not_running_launch_again(self):
        self.run_js(r"""
const base=seatsSnapshot;
seatsSnapshot=()=>({...base(),runtime:{'team/alpha':{state:'exited'}}});
await boot();
assert.strictEqual(seatCard('alpha').runtime.stateChip.textContent,'Not running (launch again)');
""")
        self.run_js(r"""
launches.team={selection_id:'s1',ready:false,state:'action_required',omitted_seats:[],seats:{alpha:{state:'exited'},beta:{state:'ready'}}};
await boot();
assert.strictEqual(seatCard('alpha').runtime.stateChip.textContent,'Not running (launch again)');
""")

    def test_wrapper_launch_command_is_labelled_honestly(self):
        self.run_js(r"""
const base=responder;
responder=async call=>call.url==='/api/preflight'?response({checked_at:'2026-10-27T00:00:00Z',agents:[
 {name:'wrap1',label:'Wrapped',client_type:'cli',executable_found:true,executable:'C:/Tools/Python/python.exe',version:'3.12',authentication:'ok',ready:true},
 {name:'real1',label:'Real',client_type:'cli',executable_found:true,executable:'C:/bin/claude.exe',version:'1.0',authentication:'ok',ready:true}]}):base(call);
await boot();
const cards=page['agents'].querySelectorAll('.pf-agent');
assert.strictEqual(cards.length,2);
const chips=card=>card.querySelectorAll('.pf-chip').map(c=>c.textContent);
const dd=(card,name)=>{const l=card.querySelector('dl').children,i=l.findIndex(e=>e.tagName==='DT'&&e.textContent===name);return i<0?null:l[i+1].textContent};
assert(chips(cards[0]).includes('Launch command: found (wrapper)'),chips(cards[0]).join('|'));
assert(!chips(cards[0]).includes('Program: found'),chips(cards[0]).join('|'));
assert.strictEqual(dd(cards[0],'Launch command (wrapper)'),'C:/Tools/Python/python.exe');
assert.strictEqual(dd(cards[0],'Client'),'Wrapped (wrap1)');
assert(chips(cards[1]).includes('Program: found'),chips(cards[1]).join('|'));
assert.strictEqual(dd(cards[1],'Executable'),'C:/bin/claude.exe');
assert.strictEqual(dd(cards[1],'Launch command (wrapper)'),null);
""")

    # 2. Untrusted text -----------------------------------------------------
    def test_untrusted_strings_are_text_only(self):
        self.run_js(r"""
const evil='<img src=x onerror=alert(1)>';
const base=responder;
responder=async call=>{
 if(call.url==='/api/preflight')return response({checked_at:'2026-10-27T00:00:00Z',agents:[{name:'x',label:evil,client_type:'cli',executable_found:false,authentication:'unknown'}]});
 if(call.url==='/api/preflight/seats'){const s=seatsSnapshot();s.packages=[{...TEAM,seats:[{...TEAM.seats[0],name:evil},TEAM.seats[1]]}];
  s.package_launches={team:{selection_id:'s1',ready:false,state:'action_required',omitted_seats:[],seats:{alpha:{state:'failed',error:evil},beta:{state:'ready'}}}};return response(s)}
 return base(call);
};
await boot();
// innerHTML throws in this DOM: a successful render with the string visible proves textContent was used.
assert.strictEqual(page['server-status'].textContent,'Local server running');
assert.strictEqual(page['agents'].querySelector('h3').textContent,evil);
const alpha=seatCard('alpha');
assert.strictEqual(alpha.querySelector('strong').textContent,evil);
assert.strictEqual(alpha.runtime.problemText.textContent,evil);
assert.strictEqual(alpha.runtime.problem.hidden,false);
""")

    def test_server_error_text_is_not_interpreted_as_html(self):
        self.run_js(r"""
const evil='<img src=x onerror=alert(1)>';
const base=responder;
responder=async call=>call.url==='/api/preflight'?response({error:evil},500):call.url==='/api/preflight/seats'?response({error:evil},500):base(call);
await boot();
assert(page['agents'].textContent.includes('Checks failed.'));
assert(page['api-seat-status'].textContent.includes('Agent seats unavailable.'));
""")

    # 3. Launch-and-go ------------------------------------------------------
    def test_launch_and_go_polls_status_then_opens_chat(self):
        self.run_js(r"""
launchReply=()=>({selection_id:'s1',ready:false,state:'starting',omitted_seats:[],seats:{alpha:{state:'starting'},beta:{state:'starting'}}});
let polls=0;statusReply=()=>(++polls<2)?launchReply():readyState('s1');
await boot();
assert.strictEqual(goButton().disabled,false);
goButton().click(); // not awaited: the handler sleeps on a fake timer that until() fires
await until(()=>assigned.length>0,'redirect');
const launch=calls.find(c=>c.url.endsWith('/launch'));
assert(launch,'no launch POST');
assert.deepStrictEqual(launch.body,{revision:'r1',omitted_seats:[]});
assert.strictEqual(launch.headers['x-session-token'],'TOKEN-123');
const statuses=calls.filter(c=>c.url==='/api/preflight/packages/team/status');
assert(statuses.length>=2,'expected polling, got '+statuses.length);
assert(statuses.every(c=>c.method==='GET'));
const chat=calls.find(c=>c.url.endsWith('/chat'));
assert(chat,'no chat POST');
assert.deepStrictEqual(chat.body,{selection_id:'s1'});
assert.deepStrictEqual(assigned,['/chat/team']);
assert(calls.indexOf(launch)<calls.indexOf(chat));
assert.strictEqual(posts().filter(c=>c.url==='/api/preflight/packages').length,0,'clean draft must not re-save');
""")

    # 3b. Chat handoff URL must be a same-origin relative path ----------------
    HOSTILE_URLS = ['javascript:alert(1)', '//evil.example/', 'https://evil.example/', '/\\evil.example/']

    def test_launch_and_go_refuses_non_relative_chat_url(self):
        for url in self.HOSTILE_URLS:
            with self.subTest(url=url):
                self.run_js(r"""
launchReply=()=>readyState('s1');
chatReply={url:%s};
await boot();
goButton().click();
await until(()=>page['api-seat-status'].textContent.includes('unexpected address'),'refusal message');
assert.deepStrictEqual(assigned,[]);
assert.strictEqual(page['api-seat-status'].textContent,'Could not open chat: unexpected address');
""" % json.dumps(url))

    def test_open_chat_with_team_refuses_non_relative_chat_url(self):
        for url in self.HOSTILE_URLS:
            with self.subTest(url=url):
                self.run_js(r"""
launches.team=readyState('s1');
chatReply={url:%s};
await boot();
await until(()=>page['team-chat'].disabled===false,'team-chat enabled');
page['team-chat'].click();
await until(()=>page['api-seat-status'].textContent.includes('unexpected address'),'refusal message');
assert.deepStrictEqual(assigned,[]);
""" % json.dumps(url))

    def test_relative_chat_url_navigates_on_both_paths(self):
        self.run_js(r"""
launchReply=()=>readyState('s1');
chatReply={url:'/?package_launch=abc'};
await boot();
goButton().click();
await until(()=>assigned.length>0,'redirect');
assert.deepStrictEqual(assigned,['/?package_launch=abc']);
await until(()=>page['team-chat'].disabled===false,'team-chat enabled');
page['team-chat'].click();
await until(()=>assigned.length>1,'second redirect');
assert.deepStrictEqual(assigned,['/?package_launch=abc','/?package_launch=abc']);
""")

    def test_seat_toggles_share_one_row(self):
        # Idea 2: "Configure" and "Status details" sit side by side instead of stacking.
        self.run_js(r"""
await boot();
const card=seatCard('alpha');
const row=card.runtime.config.parentElement;
assert(row&&row.classList.contains('pf-seat-toggles'),'toggles row missing');
assert.strictEqual(card.runtime.statusDetails.parentElement,row);
assert.strictEqual(row.parentElement,card);
""")

    # 4. Failure path -------------------------------------------------------
    def test_failed_seat_blocks_chat_and_offers_retry_or_leave_out(self):
        self.run_js(r"""
launchReply=body=>body.omitted_seats.includes('beta')?readyState('s2',['beta']):
 ({selection_id:'s1',ready:false,state:'action_required',omitted_seats:[],seats:{alpha:{state:'ready'},beta:{state:'failed',error:'Beta could not start'}}});
await boot();
await goButton().click();
await until(()=>!seatCard('beta').runtime.problem.hidden,'beta problem card');
assert.strictEqual(calls.filter(c=>c.url.endsWith('/chat')).length,0);
assert.strictEqual(assigned.length,0);
const beta=seatCard('beta'),alpha=seatCard('alpha');
assert.strictEqual(beta.runtime.problemText.textContent,'Beta could not start');
const labels=beta.runtime.problemActions.children.map(b=>b.textContent);
assert.deepStrictEqual(labels,['Retry this seat and continue','Leave it out and continue']);
assert.strictEqual(alpha.runtime.problem.hidden,true);
const leave=beta.runtime.problemActions.children.find(b=>b.textContent==='Leave it out and continue');
await leave.click();
await until(()=>assigned.length>0,'redirect after leaving seat out');
const launches=calls.filter(c=>c.url.endsWith('/launch'));
assert.strictEqual(launches.length,2);
assert.deepStrictEqual(launches[1].body.omitted_seats,['beta']);
assert.deepStrictEqual(calls.find(c=>c.url.endsWith('/chat')).body,{selection_id:'s2'});
""")

    def test_seat_chips_keep_updating_after_launch_stops_on_a_problem(self):
        # Regression: a seat still 'starting' when launch-and-go stopped kept showing
        # 'Starting…' until the page was reloaded.
        self.run_js(r"""
const stopped={selection_id:'s1',ready:false,state:'action_required',omitted_seats:[],
 seats:{alpha:{state:'starting'},beta:{state:'failed',error:'Beta could not start'}}};
launchReply=()=>stopped;
await boot();
await goButton().click();
await until(()=>!seatCard('beta').runtime.problem.hidden,'beta problem card');
assert.strictEqual(seatCard('alpha').runtime.stateChip.textContent,'Starting…');
launches.team={...stopped,seats:{alpha:{state:'ready'},beta:stopped.seats.beta}};
await until(()=>seatCard('alpha').runtime.stateChip.textContent==='Ready for chat','alpha chip to settle without a reload');
""")

    def test_sticky_bars_reserve_scroll_padding_for_keyboard_focus(self):
        # Regression: at 1280x720, Tab focus landed on controls hidden under the
        # sticky launch bar. scroll-padding keeps focused controls in view.
        css = (ROOT / 'static/preflight.css').read_text(encoding='utf-8')
        rule = re.search(r'html:has\(\.preflight-page\)\s*\{([^}]*)\}', css)
        self.assertIsNotNone(rule, 'preflight.css must set scroll padding on the scrolling element')
        self.assertRegex(rule.group(1), r'scroll-padding-bottom:\s*\d+px')
        self.assertRegex(rule.group(1), r'scroll-padding-top:\s*\d+px')

    # 5. Draft dirty --------------------------------------------------------
    def test_dirty_draft_saves_before_launch_and_sends_only_secret_ref(self):
        self.run_js(r"""
launchReply=()=>readyState('s1');
await boot();
const alpha=seatCard('alpha');
const [name,,,secret]=textInputs(alpha);
assert.strictEqual(secret.value,'KEY_ENV');
name.value='Alpha renamed';
await name.dispatch('input');
await goButton().click();
await until(()=>assigned.length>0,'redirect');
const order=calls.filter(c=>c.method==='POST').map(c=>c.url);
assert.strictEqual(order[0],'/api/preflight/packages','save must come first: '+order);
assert.strictEqual(order[1],'/api/preflight/packages/team/launch');
const save=posts()[0];
assert.strictEqual(save.body.seats[0].name,'Alpha renamed');
assert.strictEqual(save.body.seats[0].secret_ref,'KEY_ENV');
for(const seat of save.body.seats){
 assert(!('api_key' in seat)&&!('secret' in seat)&&!('key' in seat),'credential value field present: '+Object.keys(seat));
}
assert(!JSON.stringify(save.body).includes('api_key'));
""")

    # 6. Use checkbox is not a draft edit -----------------------------------
    def test_unticking_use_omits_seat_without_marking_draft_dirty(self):
        self.run_js(r"""
launchReply=body=>readyState('s1',body.omitted_seats);
await boot();
const box=seatCard('beta').runtime.checkbox;
assert(box.classList.contains('pf-runtime-control'));
box.checked=false;
await box.dispatch('change');
await goButton().click();
await until(()=>assigned.length>0,'redirect');
assert.strictEqual(posts().filter(c=>c.url==='/api/preflight/packages').length,0,'Use checkbox must not trigger a save');
assert.deepStrictEqual(calls.find(c=>c.url.endsWith('/launch')).body.omitted_seats,['beta']);
""")

    # 7. Seat ID pattern ----------------------------------------------------
    def test_seat_id_pattern_compiles_under_v_flag(self):
        self.run_js(r"""
await boot();
const idInput=textInputs(seatCard('alpha')).find(i=>i.maxLength===48);
assert(idInput,'seat id input not found');
assert.strictEqual(idInput.pattern,'[a-z][a-z0-9\\-]{0,47}');
const re=new RegExp('^(?:'+idInput.pattern+')$','v');
assert(re.test('reviewer')&&re.test('a-b-1'));
assert(!re.test('Bad')&&!re.test('1abc')&&!re.test('a_b'));
""")

    def test_html_package_id_pattern_compiles_under_v_flag(self):
        html = (ROOT / 'static/preflight.html').read_text(encoding='utf-8')
        match = re.search(r'id="api-package-id"[^>]*\bpattern="([^"]*)"', html)
        self.assertIsNotNone(match, 'api-package-id has no pattern')
        node = shutil.which('node')
        script = ("const re=new RegExp('^(?:'+process.argv[1]+')$','v');"
                  "if(!re.test('daily-team')||re.test('Bad')||re.test('-x'))process.exit(3)")
        result = subprocess.run([node, '-e', script, match.group(1)], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(match.group(1), r'[a-z][a-z0-9\-]{0,47}')


class PageLinkTests(unittest.TestCase):
    def test_chat_header_links_to_preflight(self):
        html = (ROOT / 'static/index.html').read_text(encoding='utf-8')
        header = re.search(r'<header\b.*?</header>', html, re.S)
        self.assertIsNotNone(header)
        self.assertRegex(header.group(0), r'<a\b[^>]*\bid="preflight-link"[^>]*\bhref="/preflight"')

    def test_preflight_page_links_back_to_chat(self):
        html = (ROOT / 'static/preflight.html').read_text(encoding='utf-8')
        self.assertRegex(html, r'<a\b[^>]*\bid="back-to-chat"[^>]*\bhref="/"')
        self.assertRegex(html, r'<a\b[^>]*\bclass="open-chat"[^>]*\bhref="/"')


if __name__ == '__main__':
    unittest.main()
