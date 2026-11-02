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
  this._value='';this._selected=false;this.checked=false;this.open=false;this._text='';this.listeners={};this.className='';this.parentElement=null;
  this.classList={contains:n=>this.className.split(/\s+/).includes(n),add:(...n)=>{this.className=(this.className+' '+n.join(' ')).trim()},
   remove:(...n)=>{this.className=this.className.split(/\s+/).filter(c=>c&&!n.includes(c)).join(' ')},
   toggle:(n,f)=>{const has=this.classList.contains(n),want=f===undefined?!has:!!f;if(want&&!has)this.classList.add(n);if(!want&&has)this.classList.remove(n);return want}};}
 set id(v){this._id=v;nodes.set(v,this)} get id(){return this._id}
 set textContent(v){for(const c of this.children)c.parentElement=null;this.children=[];this._text=String(v)}
 get textContent(){return this._text+this.children.map(c=>c.textContent).join('')}
 set innerHTML(v){throw Error('pre-flight UI must use textContent/DOM nodes, never innerHTML')}
 get value(){if(this.tagName==='SELECT')return this.querySelectorAll('option').find(option=>option._selected)?.value||'';return this._value}
 set value(value){const next=String(value);if(this.tagName==='SELECT'){let matched=false;for(const option of this.querySelectorAll('option')){
   option._selected=!matched&&option.value===next;if(option._selected)matched=true}}else this._value=next}
 append(...items){for(const c of items){this.children.push(c);c.parentElement=this;const select=this.tagName==='SELECT'?this:this.closest('select');
   if(select&&!select.querySelectorAll('option').some(option=>option._selected)){const first=select.querySelector('option');if(first)first._selected=true}}}
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
  if(call.url==='/api/preflight/models/refresh')return response({providers:seatsSnapshot().providers});
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

    def test_cli_seat_summary_names_the_template_default_model(self):
        # A blank CLI model uses the template default_model; API blanks stay "provider default".
        self.run_js(r"""
const base=responder;
responder=async call=>{
 if(call.url==='/api/preflight/seats'){const s=seatsSnapshot();
  s.providers.push({id:'c1',name:'Agy',adapter:'cli',default_model:'m-medium',models:['m-high','m-medium'],supports_model:true,reasoning_efforts:[],secret_ref:''});
  s.packages=[{...TEAM,seats:[{...TEAM.seats[0],provider:'c1',adapter:'cli',secret_ref:''},TEAM.seats[1]]}];return response(s)}
 return base(call);
};
await boot();
assert(seatCard('alpha').querySelector('.pf-seat-summary').textContent.includes('default model m-medium'),
 seatCard('alpha').querySelector('.pf-seat-summary').textContent);
assert(seatCard('beta').querySelector('.pf-seat-summary').textContent.includes('provider default model'));
""")

    def test_model_dropdown_options_save_the_selected_model_id(self):
        self.run_js(r"""
const base=responder;
responder=async call=>{
 if(call.url==='/api/preflight/seats'){
  const s=seatsSnapshot();
  s.providers[0]={...s.providers[0],models:['m1','m2'],default_model:'m1'};
  s.packages=[{...TEAM,seats:TEAM.seats.map(seat=>seat.id==='alpha'?{...seat,model:'m1'}:seat)}];
  return response(s);
 }
 if(call.url==='/api/preflight/packages'){
  TEAM.seats[0].model=call.body.seats[0].model;
  return response({id:'team'});
 }
 return base(call);
};
launchReply=()=>readyState('s1');
await boot();
const model=seatCard('alpha').querySelectorAll('select')[2];
assert.strictEqual(model.tagName,'SELECT');
assert.deepStrictEqual(model.children.map(option=>option.value),['','m1','m2']);
const configurationLabel=seatCard('alpha').querySelectorAll('label').find(label=>label.textContent.includes('Client configuration'));
assert(configurationLabel&&configurationLabel.textContent.includes('Choose the launch client/provider preset'));
model.value='m2';
await model.dispatch('change');
await goButton().click();
await until(()=>assigned.length>0,'redirect');
const saved=posts().find(call=>call.url==='/api/preflight/packages');
assert.strictEqual(saved.body.seats[0].model,'m2','the selected model ID must be saved unchanged');
""")

    def test_dynamic_catalog_uses_friendly_names_and_model_specific_efforts(self):
        self.run_js(r"""
const base=responder;
const catalog={dynamic:true,source:'Codex local model catalog',checked_at:'2026-11-01T12:00:00Z',
 catalog_fetched_at:'2026-11-01T12:00:00Z',complete:true,authoritative:true,refreshing:false,error:null,
 models:[
  {id:'gpt-6.1-sol',name:'GPT-6.1-Sol',available:true,reasoning_known:true,
   reasoning_efforts:['low','medium','high','xhigh','max','ultra']},
  {id:'gpt-6-luna',name:'GPT-6-Luna',available:true,reasoning_known:true,
   reasoning_efforts:['low','medium','high','xhigh','max']}
 ]};
responder=async call=>{
 if(call.url==='/api/preflight/seats'){
  const s=seatsSnapshot();
  s.providers[0]={...s.providers[0],models:['stale-config-only'],reasoning_efforts:['ultra'],model_catalog:catalog};
  s.packages=[{...TEAM,seats:TEAM.seats.map(seat=>seat.id==='alpha'?
   {...seat,model:'gpt-6.1-sol',reasoning:'ultra'}:seat)}];
  return response(s);
 }
 if(call.url==='/api/preflight/models/refresh')return response({providers:[{...seatsSnapshot().providers[0],
  adapter:'openai-compatible',name:'Prov One',models:['stale-config-only'],model_catalog:catalog}]});
 return base(call);
};
await boot();
await until(()=>posts().some(call=>call.url==='/api/preflight/models/refresh'),'automatic catalog refresh');
const alpha=seatCard('alpha');
const model=alpha.querySelectorAll('select')[2], effort=alpha.querySelectorAll('select')[3];
assert.deepStrictEqual(model.children.map(option=>option.value),['','gpt-6.1-sol','gpt-6-luna'],
 'a dynamic catalog must replace, not union with, stale configured model IDs');
assert.strictEqual(model.children[1].textContent,'GPT-6.1-Sol');
assert.strictEqual(model.value,'gpt-6.1-sol','catalog labels must not replace saved slug values');
assert.deepStrictEqual(effort.children.map(option=>option.value),['','low','medium','high','xhigh','max','ultra']);
model.value='gpt-6-luna';
await model.dispatch('change');
assert.deepStrictEqual(effort.children.map(option=>option.value),['','low','medium','high','xhigh','max']);
assert.strictEqual(effort.value,'','ultra must not carry to a model that does not declare it');
""")

    def test_duplicate_catalog_display_names_keep_ids_distinguishable(self):
        self.run_js(r"""
const base=responder;
const catalog={dynamic:true,source:'claude-native-initialize',complete:true,authoritative:true,
 refreshing:false,error:null,models:[
  {id:'sonnet',name:'Current',available:true,reasoning_known:true,reasoning_efforts:['low','high']},
  {id:'model-current',name:'Current',available:true,reasoning_known:true,reasoning_efforts:['low','high']},
  {id:'small',name:'small',available:true,reasoning_known:true,reasoning_efforts:[]}
 ]};
responder=async call=>{
 if(call.url==='/api/preflight/seats'){
  const s=seatsSnapshot();
  s.providers[0]={...s.providers[0],models:[],model_catalog:catalog};
  s.packages=[{...TEAM,seats:TEAM.seats.map(seat=>seat.id==='alpha'?{...seat,model:'model-current'}:seat)}];
  return response(s);
 }
 if(call.url==='/api/preflight/models/refresh')return response({providers:[{...seatsSnapshot().providers[0],
  adapter:'openai-compatible',name:'Claude',models:[],model_catalog:catalog}]});
 return base(call);
};
await boot();
const model=seatCard('alpha').querySelectorAll('select')[2];
assert.deepStrictEqual(model.children.map(option=>option.value),['','sonnet','model-current','small']);
assert.strictEqual(model.children[1].textContent,'Current (sonnet)');
assert.strictEqual(model.children[2].textContent,'Current (model-current)');
assert.strictEqual(model.value,'model-current','display labels must not rewrite saved catalog IDs');
""")

    def test_catalog_rerender_preserves_saved_and_in_progress_reasoning_effort(self):
        self.run_js(r"""
const base=responder;
const catalog={dynamic:true,source:'Codex local model catalog',checked_at:'2026-11-01T12:00:00Z',
 catalog_fetched_at:'2026-11-01T12:00:00Z',complete:true,authoritative:true,refreshing:false,error:null,
 models:[{id:'gpt-6.1-sol',name:'GPT-6.1-Sol',available:true,reasoning_known:true,
  reasoning_efforts:['low','medium','high']}]};
let refreshCount=0;
responder=async call=>{
 if(call.url==='/api/preflight/seats'){
  const s=seatsSnapshot();
  s.providers[0]={...s.providers[0],models:[],model_catalog:catalog};
  s.packages=[{...TEAM,seats:TEAM.seats.map(seat=>seat.id==='alpha'?
   {...seat,model:'gpt-6.1-sol',reasoning:'high'}:seat)}];
  return response(s);
 }
 if(call.url==='/api/preflight/models/refresh'){
  refreshCount++;
  return response({providers:[{...seatsSnapshot().providers[0],model_catalog:catalog}]});
 }
 return base(call);
};
await boot();
await until(()=>refreshCount===1,'automatic catalog refresh');
const alpha=seatCard('alpha'), effort=alpha.querySelectorAll('select')[3];
assert.strictEqual(effort.value,'high','catalog refresh must retain a saved reasoning effort');
effort.value='low';
const refresh=alpha.querySelectorAll('button').find(button=>button.textContent==='Refresh models');
await refresh.click();
await until(()=>refreshCount===2,'manual catalog refresh');
assert.strictEqual(effort.value,'low','catalog refresh must retain an in-progress reasoning edit');
""")

    def test_saved_provider_that_disappears_keeps_an_unavailable_option(self):
        self.run_js(r"""
const base=responder;
responder=async call=>{
 if(call.url==='/api/preflight/seats'){
  const s=seatsSnapshot();
  s.providers=[];
  s.packages=[TEAM];
  return response(s);
 }
 if(call.url==='/api/preflight/packages')return response({id:'team'});
 return base(call);
};
launchReply=()=>readyState('s1');
await boot();
const alpha=seatCard('alpha'), provider=alpha.querySelectorAll('select')[1];
assert.strictEqual(provider.value,'p1','a missing saved provider must remain selected');
assert(provider.children.some(option=>option.value==='p1'&&option.textContent.includes('saved, unavailable')),
 'the missing provider should be visibly labeled');
const [name]=textInputs(alpha);
name.value='Edited team';
await name.dispatch('input');
await goButton().click();
await until(()=>posts().some(call=>call.url==='/api/preflight/packages'),'save of edited team');
assert.strictEqual(posts().find(call=>call.url==='/api/preflight/packages').body.seats[0].provider,'p1',
 'saving another field must preserve the unavailable provider ID');
""")

    def test_stale_seat_get_does_not_replace_newer_catalog_refresh(self):
        self.run_js(r"""
const base=responder;
const oldCatalog={dynamic:true,source:'Codex local model catalog',complete:true,authoritative:true,
 retirement_authoritative:true,refreshing:false,error:null,models:[{id:'old-model',name:'Old',available:true,
 reasoning_known:true,reasoning_efforts:['low']}]};
const newCatalog={...oldCatalog,models:[{id:'new-model',name:'New',available:true,
 reasoning_known:true,reasoning_efforts:['high']}]};
let releaseStaleSeats, holdNextSeats=false;
responder=async call=>{
 if(call.url==='/api/preflight/seats'){
  const s=seatsSnapshot();
  s.providers[0]={...s.providers[0],models:[],model_catalog:oldCatalog};
  s.packages=[{...TEAM,seats:TEAM.seats.map(seat=>seat.id==='alpha'?{...seat,model:'new-model'}:seat)}];
  if(holdNextSeats){holdNextSeats=false;return await new Promise(resolve=>{releaseStaleSeats=()=>{
   releaseStaleSeats=null;resolve(response(s))}})}
  return response(s);
 }
 if(call.url==='/api/preflight/models/refresh')return response({providers:[{...seatsSnapshot().providers[0],
  model_catalog:newCatalog}]});
 return base(call);
};
await boot();
await until(()=>posts().some(call=>call.url==='/api/preflight/models/refresh'),'initial catalog refresh');
let release;
holdNextSeats=true;
page['refresh'].click();
await until(()=>typeof releaseStaleSeats==='function','stale seats request start');
release=releaseStaleSeats;
const alpha=seatCard('alpha'),refresh=alpha.querySelectorAll('button').find(button=>button.textContent==='Refresh models');
await refresh.click();
assert(alpha.querySelectorAll('select')[2].children.some(option=>option.value==='new-model'),
 'the newer catalog response should be visible before the older GET completes');
release();
await until(()=>!releaseStaleSeats,'stale seats request completion');
assert(alpha.querySelectorAll('select')[2].children.some(option=>option.value==='new-model'),
 'a GET started before the catalog refresh must not overwrite newer provider catalog data');
""")

    def test_successful_provider_refresh_clears_prior_wildcard_error(self):
        self.run_js(r"""
const base=responder;
const catalog={dynamic:true,source:'Codex local model catalog',complete:true,authoritative:true,
 retirement_authoritative:true,refreshing:false,error:null,models:[{id:'m1',name:'Model 1',available:true,
 reasoning_known:true,reasoning_efforts:['low']}]};
let refreshCount=0;
responder=async call=>{
 if(call.url==='/api/preflight/seats'){
  const s=seatsSnapshot();
  s.providers[0]={...s.providers[0],models:[],model_catalog:catalog};
  return response(s);
 }
 if(call.url==='/api/preflight/models/refresh'){
  refreshCount++;
  if(refreshCount===1)throw Error('temporary fetch error');
  return response({providers:[{...seatsSnapshot().providers[0],model_catalog:catalog}]});
 }
 return base(call);
};
await boot();
await until(()=>refreshCount===1&&seatCard('alpha').querySelector('.pf-dim').textContent.includes('temporary fetch error'),
 'initial catalog error');
const alpha=seatCard('alpha'),refresh=alpha.querySelectorAll('button').find(button=>button.textContent==='Refresh models');
await refresh.click();
await until(()=>refreshCount===2,'successful provider refresh');
assert(!alpha.querySelector('.pf-dim').textContent.includes('temporary fetch error'),
 'a successful refresh must clear the previous wildcard error');
""")

    def test_manual_catalog_refresh_preserves_form_edits_and_last_good_model(self):
        self.run_js(r"""
const base=responder;
const first={dynamic:true,source:'Codex local model catalog',checked_at:'2026-11-01T12:00:00Z',
 catalog_fetched_at:'2026-11-01T12:00:00Z',complete:true,authoritative:true,retirement_authoritative:true,refreshing:false,error:null,
 models:[{id:'gpt-6.1-sol',name:'GPT-6.1-Sol',available:true,reasoning_known:true,
  reasoning_efforts:['low','medium','high','xhigh','max','ultra']}]};
const failed={...first,source:'Codex local model catalog',checked_at:'2026-11-01T12:01:00Z',
 complete:false,authoritative:true,refreshing:false,error:'catalog command exited 1'};
let refreshCount=0;
responder=async call=>{
 if(call.url==='/api/preflight/seats'){
  const s=seatsSnapshot();
  s.providers[0]={...s.providers[0],models:['stale-config-only'],reasoning_efforts:['ultra'],model_catalog:first};
  s.packages=[{...TEAM,seats:TEAM.seats.map(seat=>seat.id==='alpha'?{...seat,model:'removed-model',reasoning:'ultra'}:seat)}];
  return response(s);
 }
 if(call.url==='/api/preflight/models/refresh'){
  refreshCount++;
  const catalog=refreshCount===1?first:failed;
  return response({providers:[{...seatsSnapshot().providers[0],adapter:'openai-compatible',name:'Prov One',
   model_catalog:catalog}]});
 }
 return base(call);
};
await boot();
await until(()=>refreshCount===1,'one automatic model refresh');
const alpha=seatCard('alpha');
const model=alpha.querySelectorAll('select')[2];
const effort=alpha.querySelectorAll('select')[3];
assert(model.children.some(option=>option.value==='removed-model'&&option.textContent.includes('unavailable')),
 'only an authoritative complete catalog may label a saved missing model unavailable');
assert.strictEqual(model.value,'removed-model');
assert.deepStrictEqual(effort.children.map(option=>option.value),['','ultra']);
assert(effort.children[1].textContent.includes('saved, unverified'));
assert(effort.disabled,'an unknown model must not inherit template-wide effort choices');
const [name]=textInputs(alpha);
name.value='Draft edit survives catalog refresh';
await name.dispatch('input');
const refreshButton=alpha.querySelectorAll('button').find(button=>button.textContent==='Refresh models');
assert(refreshButton&&!refreshButton.disabled);
await refreshButton.click();
await until(()=>refreshCount===2&&alpha.querySelector('.pf-dim').textContent.includes('catalog command exited 1'),
 'failed refresh status');
assert.strictEqual(name.value,'Draft edit survives catalog refresh');
assert.strictEqual(model.value,'removed-model','failed refresh must retain the selected saved model');
assert(model.children.some(option=>option.value==='removed-model'&&option.textContent.includes('saved, unverified')),
 'a failed refresh cannot newly retire a saved model');
assert(alpha.querySelector('.pf-dim').textContent.includes('Last complete catalog'));
assert.strictEqual(refreshCount,2,'catalog refresh must be once on entry plus the explicit click');
""")

    def test_first_use_dynamic_catalog_shows_loading_without_fabricated_models(self):
        self.run_js(r"""
const base=responder;
responder=async call=>{
 if(call.url==='/api/preflight/seats'){
  const s=seatsSnapshot();
  s.providers[0]={...s.providers[0],models:['must-not-appear'],model_catalog:{dynamic:true,
   source:'Codex local model catalog',models:[],complete:false,authoritative:false,refreshing:true,error:null}};
  return response(s);
 }
 return base(call);
};
await boot();
const alpha=seatCard('alpha');
const model=alpha.querySelectorAll('select')[2];
const refresh=alpha.querySelectorAll('button').find(button=>button.textContent==='Refresh models');
assert.deepStrictEqual(model.children.map(option=>option.value),[''],'first-use must not expose static guesses as discovered models');
assert(alpha.querySelector('.pf-dim').textContent.includes('Checking'));
assert(refresh.disabled,'avoid starting a duplicate scan while the catalog is already refreshing');
assert.strictEqual(posts().filter(call=>call.url==='/api/preflight/models/refresh').length,0);
""")

    def test_dynamic_discovery_failure_uses_explicit_configured_model_fallback(self):
        self.run_js(r"""
const base=responder;
const catalog={dynamic:true,source:'Codex local model catalog',models:[],configured_models:['gpt-6.1-sol'],
 checked_at:'2026-11-01T12:00:00Z',catalog_fetched_at:null,complete:false,authoritative:false,
 refreshing:false,error:'model metadata unavailable'};
responder=async call=>{
 if(call.url==='/api/preflight/seats'){
  const s=seatsSnapshot();
  s.providers[0]={...s.providers[0],models:[],model_catalog:catalog};
  s.packages=[{...TEAM,seats:TEAM.seats.map(seat=>seat.id==='alpha'?{...seat,model:'gpt-6.1-sol'}:seat)}];
  return response(s);
 }
 if(call.url==='/api/preflight/models/refresh')return response({providers:[{...seatsSnapshot().providers[0],
  adapter:'openai-compatible',name:'Prov One',models:[],model_catalog:catalog}]});
 return base(call);
};
await boot();
await until(()=>posts().some(call=>call.url==='/api/preflight/models/refresh'),'automatic catalog refresh');
const alpha=seatCard('alpha'), model=alpha.querySelectorAll('select')[2];
assert.deepStrictEqual(model.children.map(option=>option.value),['','gpt-6.1-sol']);
assert(model.children[1].textContent.includes('configured fallback'));
assert.strictEqual(model.value,'gpt-6.1-sol','configured model fallback keeps the saved model ID');
const status=alpha.querySelectorAll('p').find(p=>p.textContent.includes('model metadata unavailable'));
assert(status&&status.textContent.includes('discovery is unavailable'));
""")

    def test_catalog_capability_note_is_shown_near_model_picker(self):
        self.run_js(r"""
const base=responder;
const note='This provider catalog does not declare chat compatibility for every model. Verify the selected model supports chat completions.';
const catalog={dynamic:true,source:'Muse models endpoint',complete:true,authoritative:true,refreshing:false,error:null,
 capability_note:note,models:[{id:'muse-basic',name:'Muse Basic',available:true,reasoning_known:false,reasoning_efforts:[]}]};
responder=async call=>{
 if(call.url==='/api/preflight/seats'){
  const s=seatsSnapshot();
  s.providers[0]={...s.providers[0],models:[],model_catalog:catalog};
  return response(s);
 }
 if(call.url==='/api/preflight/models/refresh')return response({providers:[{...seatsSnapshot().providers[0],model_catalog:catalog}]});
 return base(call);
};
await boot();
const alpha=seatCard('alpha');
const status=alpha.querySelectorAll('p').find(p=>p.classList.contains('pf-dim')&&p.textContent.includes('models endpoint'));
assert(status&&status.textContent.includes(note),'catalog capability context must be visible by the model picker');
""")

    def test_default_only_cli_preset_is_grouped_and_explained(self):
        self.run_js(r"""
const base=responder;
const noModel={id:'codex',name:'Codex',adapter:'cli',supports_model:false,models:[],reasoning_efforts:[],
 model_selection_note:'This preset uses the native client default. Choose a model-enabled preset to set a model.',
 model_catalog:{dynamic:true,models:[],configured_models:[],source:'codex cache',complete:false,authoritative:false,refreshing:false,error:null}};
const managed={id:'codex-release',name:'Codex CLI',adapter:'cli',supports_model:true,models:['gpt-6.1-sol'],
 reasoning_efforts:[],model_catalog:{dynamic:true,models:[{id:'gpt-6.1-sol',name:'GPT-6.1-Sol',available:true,
 reasoning_known:true,reasoning_efforts:['low']}],configured_models:['gpt-6.1-sol'],source:'codex cache',
 complete:true,authoritative:true,refreshing:false,error:null}};
responder=async call=>{
 if(call.url==='/api/preflight/seats'){
  const s=seatsSnapshot();
  s.providers=[noModel,managed];
  s.packages=[{...TEAM,seats:TEAM.seats.map(seat=>seat.id==='alpha'?
   {...seat,provider:'codex',adapter:'cli',secret_ref:''}:
   {...seat,provider:'codex-release',adapter:'cli',secret_ref:''})}];
  return response(s);
 }
 if(call.url==='/api/preflight/models/refresh')return response({providers:[noModel,managed]});
 return base(call);
};
await boot();
const alpha=seatCard('alpha');
const provider=alpha.querySelectorAll('select')[1];
assert.strictEqual(provider.value,'codex','an existing legacy provider selection must remain selected');
const group=provider.children.find(node=>node.tagName==='OPTGROUP');
assert(group&&group.label==='Legacy/default-only clients');
const legacy=group.children.find(option=>option.value==='codex');
assert(legacy&&legacy.textContent.includes('native default only'));
assert(provider.children.some(option=>option.value==='codex-release'),'managed choice remains a primary option');
assert(alpha.querySelectorAll('select')[2].disabled);
const note=alpha.querySelectorAll('p').find(p=>p.textContent.includes('Choose a model-enabled preset'));
assert(note,'backend model_selection_note should appear beside the model control');
""")

    def test_saved_model_missing_from_template_stays_selectable_and_is_preserved(self):
        self.run_js(r"""
const base=responder;
responder=async call=>{
 if(call.url==='/api/preflight/seats'){
  const s=seatsSnapshot();
  s.providers[0]={...s.providers[0],models:['m1'],default_model:'m1'};
  s.packages=[{...TEAM,seats:TEAM.seats.map(seat=>seat.id==='alpha'?{...seat,model:'legacy-model'}:seat)}];
  return response(s);
 }
 if(call.url==='/api/preflight/packages'){
  TEAM.seats[0].model=call.body.seats[0].model;
  return response({id:'team'});
 }
 return base(call);
};
launchReply=()=>readyState('s1');
await boot();
const alpha=seatCard('alpha');
const model=alpha.querySelectorAll('select')[2];
const legacy=model.children.find(option=>option.value==='legacy-model');
assert(legacy,'saved model missing from current template should remain an explicit option');
assert(legacy.textContent.includes('saved, unverified'));
assert.strictEqual(model.value,'legacy-model','opening a saved team must not silently select Provider default');
const [name]=textInputs(alpha);
name.value='Alpha edited';
await name.dispatch('input');
await goButton().click();
await until(()=>assigned.length>0,'redirect');
const saved=posts().find(call=>call.url==='/api/preflight/packages');
assert.strictEqual(saved.body.seats[0].model,'legacy-model','unlisted saved model ID must survive an unrelated edit');
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
const [name,,secret]=textInputs(alpha);
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
