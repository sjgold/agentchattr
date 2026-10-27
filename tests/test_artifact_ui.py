"""Reduced20 ROOT UI reds. Actual JS in Node vm, unit DOM/fetch/clock only.

Missing artifacts.js is infrastructure evidence; later assertions are unobserved
until the module exists. Existing Stop renderer cases are behavioral reds.
Rendered/browser/transport acceptance remains a separate guarded deliverable.
"""
from pathlib import Path
import shutil
import json
from html.parser import HTMLParser
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

BOOT = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const root=process.argv[2], nodes=new Map(), timers=new Map(), calls=[], watchers=new Map(), hubs=new Map();
let timerID=0, responder;
class Element {
 constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.dataset={};this.style={};this.hidden=false;this.disabled=false;this.value='';this._text='';this.textWrites=0;this.listeners={};this.className='';this.isConnected=true;
 this.classList={add:(...names)=>{this.className += ' '+names.join(' ')},remove:()=>{},toggle:()=>{},contains:n=>this.className.split(' ').includes(n)};}
 set id(v){this._id=v;nodes.set(v,this)} get id(){return this._id}
 set textContent(v){this.textWrites++;for(const c of [...this.children])if(typeof c!=='string')c.remove();this._text=String(v);this.children=[]} get textContent(){return this._text+this.children.map(c=>typeof c==='string'?c:c.textContent).join(' ')}
 set innerHTML(v){throw Error('UI must build safe DOM/text, not interpolate HTML')}
 append(...items){for(const c of items){this.children.push(c);if(typeof c!=='string')c.parentElement=this}}
 appendChild(c){this.append(c);return c} replaceChildren(...items){for(const c of [...this.children])if(typeof c!=='string')c.remove();this.children=[];this._text='';this.append(...items)}
 after(...items){this.parentElement?.append(...items)} remove(){for(const c of [...this.children])if(typeof c!=='string')c.remove();this.isConnected=false;if(this.id&&nodes.get(this.id)===this)nodes.delete(this.id);if(this.parentElement)this.parentElement.children=this.parentElement.children.filter(c=>c!==this)}
 setAttribute(k,v){this[k]=String(v)} getAttribute(k){return this[k]??null}
 addEventListener(k,fn){(this.listeners[k]??=[]).push(fn)} removeEventListener(){}
 async dispatch(kind,extra={}){const e={preventDefault(){},stopPropagation(){},target:this,currentTarget:this,...extra};if(this.disabled)return;
  const fn=this['on'+kind];if(fn)await fn(e);for(const listener of this.listeners[kind]||[])await listener(e);}
 async click(){if(this.tagName==='A')downloads.push({href:this.href,download:this.download});return this.dispatch('click')}
 focus(){document.activeElement=this}
 querySelectorAll(selector){const result=[];for(const c of this.children){if(typeof c==='string')continue;
 const match=selector.startsWith('#')?c.id===selector.slice(1):selector.startsWith('.')?c.className.split(' ').includes(selector.slice(1)):c.tagName.toLowerCase()===selector.toLowerCase();
 if(match)result.push(c);result.push(...c.querySelectorAll(selector));}return result}
 querySelector(s){return this.querySelectorAll(s)[0]||null}
}
class Option extends Element {constructor(text,value){super('option');this.textContent=text;this.value=value}}
const document={hidden:false,listeners:{},addEventListener(kind,fn){(this.listeners[kind]??=[]).push(fn)},createTextNode:text=>{const item=new Element('#text');item.textContent=text;return item},body:new Element('body'),activeElement:null,createElement:t=>new Element(t),
 getElementById:id=>nodes.get(id)||null,querySelector:s=>s.startsWith('#')?nodes.get(s.slice(1)):document.body.querySelector(s),querySelectorAll:s=>document.body.querySelectorAll(s)};
for(const [id,tag] of [['session-bar','div'],['session-launch-btn','button'],['artifact-documents-open','button']]){const e=new Element(tag);e.id=id;document.body.append(e)}
const intervals=[];
const storage=new Map(), downloads=[], blobs=new Map(), revoked=[];
const sessionStorage={getItem:k=>storage.get(k)??null,setItem:(k,v)=>storage.set(k,String(v)),removeItem:k=>storage.delete(k)};
const Hub={on:(k,f)=>{(hubs.get(k)||hubs.set(k,[]).get(k)).push(f)},emit:(k,v)=>(hubs.get(k)||[]).forEach(f=>f(v))};
const Store={watch:(k,f)=>{(watchers.get(k)||watchers.set(k,[]).get(k)).push(f)}};
const URLClass=URL;URLClass.createObjectURL=blob=>{const id='blob:fixture-'+blobs.size;blobs.set(id,blob);return id};URLClass.revokeObjectURL=id=>revoked.push(id);
const window={activeChannel:'review',SESSION_TOKEN:'OPERATOR_ONLY',escapeHtml:v=>String(v),Hub,Store,sessionStorage,
 ChannelLifecycle:{canWrite:()=>true,ownerAvailable:()=>true},URL:URLClass,crypto:require('crypto').webcrypto};
const later=(fn,delay)=>{timers.set(++timerID,{fn,delay});return timerID},clear=id=>timers.delete(id);
Object.assign(window,{setTimeout:later,clearTimeout:clear});
const response=(data,status=200,headers={})=>({ok:status>=200&&status<300,status,headers:new Headers(headers),
 json:async()=>JSON.parse(JSON.stringify(data)),blob:async()=>new Blob([typeof data==='string'?data:JSON.stringify(data)],{type:headers['Content-Type']||'text/markdown'}),text:async()=>new TextDecoder().decode(new TextEncoder().encode(String(data)))});
const session={session_id:1,run_id:'b'.repeat(32),title:'Completed source',state:'complete',started_at:10,source_so_far:false,title_truncated:false};
let current={request_id:'a'.repeat(32),channel:'review',state:'queued',reason:'queued',label:'queued',author_name:'Fixture author',created_at:1,updated_at:1,version_id:null,needs_resume:false,warning:null,
 source:{session_id:1,run_id:session.run_id,message_count:2,packet_bytes:512,scope_sha256:'e'.repeat(64),input_revision:'f'.repeat(64),source_so_far:false}};
let markdown='\ufeff# café\r\n<script>alert(1)</script>\n<img src=x onerror=evil()>\n[jump](javascript:evil())';
responder=async(url,options)=>{
 if(url.includes('/sessions?'))return response({sessions:[session],offset:0,has_more:false});
 if(url.endsWith('/requests')&&options.method==='POST'){current={...current,request_id:JSON.parse(options.body).request_id};return response({request:current,durability:'recorded',transport_settled:false},202)}
 if(url.endsWith('/cancel')){current={...current,state:'cancelled',reason:'operator_cancelled',label:'failed'};return response({request:current,durability:'recorded',transport_settled:false})}
 if(url.endsWith('/download'))return response(markdown,200,{'Content-Type':'text/markdown; charset=utf-8'});
 if(url.endsWith('/document')||url.includes('/versions/'))return response({version:{id:current.version_id},markdown});
 return response(current);
};
const context=vm.createContext({window,document,Hub,Store,sessionStorage,console,crypto:window.crypto,
 URL:URLClass,Blob,Headers,AbortController,TextEncoder,Option,setTimeout:later,clearTimeout:clear,setInterval:(fn,delay)=>{intervals.push(delay);return 0},clearInterval(){},
 fetch:async(url,options={})=>{url=String(url);calls.push({url,...options});return responder(url,options)}});
function load(file){vm.runInContext(sourceOverrides[file]??fs.readFileSync(root+'/'+file,'utf8'),context,{filename:file})}
function element(id){const value=nodes.get(id);assert(value,'Missing control '+id);return value}
async function activate(id){await element(id).click();await flush()}
async function flush(){await new Promise(resolve=>setImmediate(resolve))}
async function open(){load('static/artifacts.js');assert(window.ArtifactDocuments,'Missing frozen UI entry');window.ArtifactDocuments.init();await window.ArtifactDocuments.open();await flush();
 element('artifact-session-select').value='1';await element('artifact-session-select').dispatch('change');await flush();}
async function submit(){element('artifact-instruction').value='PRIVATE_INSTRUCTION';await activate('artifact-submit')}
async function fire(){const next=timers.entries().next().value;assert(next,'Missing poll timer');timers.delete(next[0]);await next[1].fn();await flush()}
"""


class ArtifactUITests(unittest.TestCase):
    source_overrides = {}
    def run_js(self, body, *, module=True):
        node = shutil.which('node')
        self.assertIsNotNone(node, 'Node is required for the actual JS UI tests')
        if module:
            (ROOT / 'static/artifacts.js').read_text(encoding='utf-8')
        script = 'const sourceOverrides=' + json.dumps(self.source_overrides) + ';\n' + BOOT + '\n(async()=>{\n' + body + '\nprocess.stdout.write("ARTIFACT_UI_CASE_COMPLETED\\n");\n})().catch(error=>{console.error(error.stack);process.exitCode=1});'
        result = subprocess.run([node, '-', str(ROOT)], input=script, cwd=ROOT,
                                capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count('ARTIFACT_UI_CASE_COMPLETED'),1,'Async test body did not reach completion: '+result.stderr)

    def allow_inflight_reentry(self, old, new):
        """VM-only fault injection makes a redundant serial guard reachable."""
        name='static/artifacts.js'
        source=self.source_overrides.get(name,(ROOT/name).read_text(encoding='utf-8'))
        self.assertEqual(source.count(old),1)
        self.source_overrides={**self.source_overrides,name:source.replace(old,new,1)}

    def test_switching_selected_session_labels_card_source_without_changing_saved_request(self):
        self.run_js(r"""
const original=responder;
responder=async(url,options)=>url.includes('/sessions?')?response({sessions:[session,{...session,session_id:2,run_id:'d'.repeat(32),title:'Other source'}],offset:0,has_more:false}):original(url,options);
await open();await submit();current={...current,state:'fulfilled',version_id:'c'.repeat(32)};
await activate('artifact-refresh');await activate('artifact-read');
const saved=storage.get('artifact-request:review'), count=calls.length;
element('artifact-session-select').value='2';await element('artifact-session-select').dispatch('change');
assert(element('artifact-status').textContent.includes('Latest request: Completed source'));
assert(element('artifact-status').textContent.includes('Ready'));
assert.strictEqual(storage.get('artifact-request:review'),saved);assert.strictEqual(calls.length,count);
assert.strictEqual(element('artifact-reader').textContent,markdown);
element('artifact-session-select').value='1';await element('artifact-session-select').dispatch('change');
assert.strictEqual(element('artifact-status').textContent,'Ready');
""")

    def test_selected_session_has_no_choose_prompt_but_empty_list_keeps_it(self):
        self.run_js(r"""
await open();assert.strictEqual(element('artifact-session-select').value,'1');
assert.strictEqual(element('artifact-status').textContent,'');
window.ArtifactDocuments.close();const original=responder;
responder=async(url,options)=>url.includes('/sessions?')?response({sessions:[],offset:0,has_more:false}):original(url,options);
await window.ArtifactDocuments.open();
assert.strictEqual(element('artifact-status').textContent,'Choose a session to write from');
""")

    def test_stop_warning_is_literal_and_distinct_from_review_outcome(self):
        self.run_js(r"""
load('static/sessions.js');const panel=new Element('section');
context.panel=panel;context.s={id:1,state:'stopped',stop_id:'s',admitted_events:[],cancellation_receipts:[],termination_offers:[],quarantined_events:[],
 artifact_cancellation:{warning:'artifact_fence_failed',unconfirmed_dispatch_ids:['a'.repeat(32)]}};
vm.runInContext('renderStopControls(panel,s)',context);
assert(panel.textContent.toLowerCase().includes('document'),'Missing document cancellation warning');
assert(panel.textContent.toLowerCase().includes('unconfirmed'),'No false confirmation');
assert(panel.textContent.includes('Review stopped locally'),'Artifact warning must not change review outcome');
assert.strictEqual(panel.querySelectorAll('script').length,0);
""", module=False)

    def test_stop_warning_only_update_invalidates_render_cache(self):
        self.run_js(r"""
load('static/sessions.js');const panel=new Element('section');context.panel=panel;
context.s={id:1,state:'stopped',admitted_events:[],cancellation_receipts:[],termination_offers:[],quarantined_events:[],artifact_cancellation:{warning:null,unconfirmed_dispatch_ids:[]}};
vm.runInContext('renderStopControls(panel,s)',context);const before=panel.dataset.key;
context.s.artifact_cancellation={warning:'unconfirmed_overflow',unconfirmed_dispatch_ids:[]};
vm.runInContext('renderStopControls(panel,s)',context);assert.notStrictEqual(panel.dataset.key,before);
""", module=False)

    def test_stop_warning_null_codes_count_and_polled_updates(self):
        self.run_js(r"""
load('static/sessions.js');const panel=new Element('section');context.panel=panel;
context.s={id:1,state:'stopped',channel:'review',updated_at:1,admitted_events:[],cancellation_receipts:[],termination_offers:[],quarantined_events:[],artifact_cancellation:{warning:null,unconfirmed_dispatch_ids:[]}};
vm.runInContext('updateSessionBar=()=>renderStopControls(panel,activeSession);handleSessionEvent("update",s)',context);
assert.strictEqual(panel.querySelector('.session-artifact-warning'),null);const before=panel.dataset.key;
vm.runInContext('renderStopControls(panel,s)',context);assert.strictEqual(panel.dataset.key,before);
context.s.updated_at=999;vm.runInContext('renderStopControls(panel,s)',context);assert.strictEqual(panel.dataset.key,before);
for(const warning of ['storage_unavailable','artifact_fence_failed','transport_unconfirmed','unconfirmed_overflow']){
 context.s={...context.s,artifact_cancellation:{warning,unconfirmed_dispatch_ids:['a'.repeat(32),'b'.repeat(32)]}};
 vm.runInContext('handleSessionEvent("update",s)',context);assert(panel.querySelector('.session-artifact-warning').textContent.includes('2 known'));
}
const prior=panel.dataset.key;context.s.artifact_cancellation.unconfirmed_dispatch_ids.push('c'.repeat(32));
vm.runInContext('handleSessionEvent("update",s)',context);assert.notStrictEqual(panel.dataset.key,prior);
""",module=False)

    def test_completed_session_list_and_more_are_authenticated(self):
        self.run_js(r"""
let page=0;const original=responder;responder=async(url,options)=>url.includes('/sessions?')?
 response({sessions:[{...session,session_id:++page}],offset:page===1?0:20,has_more:page===1}):original(url,options);
await open();assert(element('artifact-session-select').textContent.includes('Completed source'));
await activate('artifact-more-sessions');assert(calls.some(c=>c.url.includes('offset=20')));
assert(calls.some(c=>c.url.includes('channel=review')));for(const call of calls){assert(call.url.startsWith('/api/artifacts/'));assert.strictEqual(call.cache,'no-store');assert(!call.url.includes('token='));assert.strictEqual(new Headers(call.headers).get('X-Session-Token'),'OPERATOR_ONLY')}
""")

    def test_create_exact_intent_and_fresh_id_for_each_new_submit(self):
        self.run_js(r"""
await open();await submit();let posts=calls.filter(c=>c.method==='POST');assert.strictEqual(posts.length,1);
const first=JSON.parse(posts[0].body);assert.deepStrictEqual(Object.keys(first).sort(),['channel','instruction','request_id','run_id','session_id']);
assert(/^[0-9a-f]{32}$/.test(first.request_id));assert.strictEqual(first.instruction,'PRIVATE_INSTRUCTION');assert.strictEqual(new Headers(posts[0].headers).get('Content-Type'),'application/json');
assert.strictEqual(first.session_id,1);assert.strictEqual(first.run_id,session.run_id);
current={...current,state:'fulfilled',label:'ready',version_id:'c'.repeat(32)};await activate('artifact-refresh');
await submit();posts=calls.filter(c=>c.method==='POST');assert.strictEqual(posts.length,2);
assert.notStrictEqual(JSON.parse(posts[1].body).request_id,first.request_id);
for(const value of storage.values()){assert(!value.includes('OPERATOR_ONLY'));assert(!value.includes('PRIVATE_INSTRUCTION'));assert(!value.includes(markdown))}
""")

    def test_double_activation_and_unknown_effect_keep_same_request_id(self):
        self.run_js(r"""
await open();let finish;const original=responder;
responder=async(url,options)=>url.endsWith('/requests')?new Promise((resolve,reject)=>{finish=()=>reject(Error('lost response'))}):original(url,options);
element('artifact-instruction').value='PRIVATE_INSTRUCTION';const first=element('artifact-submit').click();assert(element('artifact-submit').disabled);const second=element('artifact-submit').click();await flush();
assert.strictEqual(calls.filter(c=>c.method==='POST').length,1);const id=JSON.parse(calls.find(c=>c.method==='POST').body).request_id;
finish();await Promise.all([first,second]);await flush();
responder=async(url,options)=>url.endsWith('/requests/'+id)?response({code:'not_found',error:'Not found.'},404):original(url,options);
await activate('artifact-refresh');assert(element('artifact-status').textContent.includes('Not found yet'));
responder=original;current={...current,request_id:id};await submit();
const posts=calls.filter(c=>c.method==='POST');assert.strictEqual(posts.length,2);assert.strictEqual(JSON.parse(posts[1].body).request_id,id);
current={...current,state:'active',label:'working'};await activate('artifact-refresh');assert(element('artifact-status').textContent.includes('Writing document'));
""")

    def test_poll_backoff_terminal_and_close_dispose_timers(self):
        self.run_js(r"""
await open();await submit();assert([...timers.values()].some(t=>t.delay===2000));
const original=responder;responder=async()=>{throw Error('offline')};
for(const delay of [4000,8000,16000,30000]){await fire();assert([...timers.values()].some(t=>t.delay===delay))}
await fire();assert([...timers.values()].some(t=>t.delay===30000));responder=original;await fire();assert([...timers.values()].some(t=>t.delay===2000));
window.ArtifactDocuments.close();assert.strictEqual(timers.size,0);assert.strictEqual(intervals.length,0);
await window.ArtifactDocuments.open();await flush();assert([...timers.values()].some(t=>t.delay===2000));
current={...current,state:'fulfilled',label:'ready',version_id:'c'.repeat(32)};await fire();assert.strictEqual(timers.size,0);
window.ArtifactDocuments.close();assert.strictEqual(timers.size,0);assert.strictEqual(document.activeElement,element('artifact-documents-open'));
""")

    def test_status_cancel_and_needs_recovery_have_honest_labels(self):
        self.run_js(r"""
await open();await submit();current={...current,state:'prepared',needs_resume:true,label:'unavailable'};
await activate('artifact-refresh');assert(element('artifact-status').textContent.includes('Needs recovery'));assert(!element('artifact-cancel').disabled);
await activate('artifact-cancel');const cancelled=calls.find(c=>c.url.endsWith('/cancel'));assert.deepStrictEqual(JSON.parse(cancelled.body),{});
assert(element('artifact-status').textContent.includes('Cancelled'));assert.strictEqual(timers.size,0);
""")

    def test_verified_reader_is_literal_and_download_is_exact_blob(self):
        self.run_js(r"""
await open();await submit();current={...current,state:'fulfilled',label:'ready',version_id:'c'.repeat(32)};await activate('artifact-refresh');
await activate('artifact-read');assert.strictEqual(element('artifact-reader').tagName,'PRE');assert.strictEqual(element('artifact-reader').textContent,markdown);
assert.strictEqual(document.body.querySelectorAll('script').length,0);assert.strictEqual(document.body.querySelectorAll('img').length,0);
element('artifact-reader').textContent='VISIBLE_EDIT';await activate('artifact-download');assert.strictEqual(downloads.length,1);assert.strictEqual(downloads[0].download,'document.md');
assert.deepStrictEqual(Buffer.from(await blobs.get(downloads[0].href).arrayBuffer()),Buffer.from(markdown,'utf8'));
for(const value of storage.values()){assert(!value.includes(markdown));assert(!value.includes('PRIVATE_INSTRUCTION'));}
for(const timer of [...timers.values()])if(timer.delay===1000)await timer.fn();
assert(revoked.includes(downloads[0].href));assert(calls.some(c=>c.url.endsWith('/download')));assert(calls.filter(c=>c.url.endsWith('/download')).every(c=>new Headers(c.headers).get('X-Session-Token')==='OPERATOR_ONLY'));
""")

    def test_capability_refusal_and_failed_read_keep_safe_text(self):
        self.run_js(r"""
await open();const original=responder;
responder=async(url,options)=>url.endsWith('/requests')?response({code:'no_author_available',cause:'capability_off',error:'Artifact authoring is not enabled.',durability:'not_recorded',request:null},409):original(url,options);
await submit();assert(element('artifact-error').textContent.includes('Artifact authoring is not enabled'));
responder=original;await submit();current={...current,state:'fulfilled',label:'ready',version_id:'c'.repeat(32)};await activate('artifact-refresh');await activate('artifact-read');
responder=async()=>response({code:'storage_unavailable',error:'Document storage is unavailable.'},503);await activate('artifact-read');
assert(element('artifact-reader').hidden||element('artifact-reader').textContent==='');assert(element('artifact-error').textContent.includes('storage'));
""")

    def test_channel_change_and_late_response_do_not_leak_other_channel(self):
        self.run_js(r"""
await open();await submit();const original=responder;let resolve;
responder=async(url,options)=>url.endsWith('/requests/'+current.request_id)?new Promise(r=>{resolve=r}):original(url,options);
const refresh=element('artifact-refresh').click();await flush();window.activeChannel='peer';for(const fn of watchers.get('activeChannel')||[])await fn('peer');
resolve(response({...current,state:'active',label:'working',author_name:'OLD_CHANNEL_STATUS'}));await refresh;await flush();
assert(element('artifact-documents-panel').hidden);assert.strictEqual(timers.size,0);assert(!element('artifact-status').textContent.includes('OLD_CHANNEL_STATUS'));
assert(element('artifact-reader').hidden||element('artifact-reader').textContent==='');
""")

    def test_ui_load_and_init_hooks_are_reachable(self):
        class Tags(HTMLParser):
            def __init__(self):
                super().__init__();self.tags=[]
            def handle_starttag(self,tag,attrs):self.tags.append((tag,dict(attrs)))
        parsed=Tags();parsed.feed((ROOT/'static/index.html').read_text(encoding='utf-8'))
        scripts=[a['src'].split('?')[0] for tag,a in parsed.tags if tag=='script' and 'src' in a]
        self.assertLess(scripts.index('/static/sessions.js'),scripts.index('/static/artifacts.js'))
        self.assertLess(scripts.index('/static/artifacts.js'),scripts.index('/static/chat.js'))
        self.assertTrue(any(tag=='link' and a.get('href','').split('?')[0]=='/static/artifacts.css' for tag,a in parsed.tags))
        self.assertTrue(any(tag=='button' and a.get('id')=='artifact-documents-open' for tag,a in parsed.tags))
        self.run_js(r"""
load('static/sessions.js');context.spy=[];window.ArtifactDocuments={init:()=>context.spy.push('init')};
vm.runInContext('fetchSessionTemplates=()=>{};fetchAllActiveSessions=()=>{};updateSessionBar=()=>{};fetchActiveSession=()=>{};_sessionsInit()',context);
assert.deepStrictEqual(context.spy,['init']);
""",module=False)

    def test_all_status_texts_and_cancel_warning_survive_manual_refresh(self):
        self.run_js(r"""
await open();await submit();
for(const [state,reason,version_id,needs_resume,text] of [
 ['queued','queued',null,false,'Queued'],['active',null,null,false,'Writing document'],
 ['fulfilled',null,'c'.repeat(32),false,'Ready'],['failed','source_packet_unavailable',null,false,'Document could not be completed'],
 ['cancelled','operator_cancelled',null,false,'Cancelled'],['cancelled','source_stopped',null,false,'Stopped'],
 ['quarantined','invalid_response',null,false,'Response rejected'],['imported',null,'c'.repeat(32),false,'Imported history'],
 ['imported',null,null,false,'Imported history, no document'],['prepared',null,null,true,'Needs recovery']]){
 current={...current,state,reason,version_id,needs_resume};await activate('artifact-refresh');assert(element('artifact-status').textContent.includes(text),text);
}
const original=responder;let finish;responder=async(url,options)=>url.endsWith('/cancel')?new Promise(resolve=>{finish=()=>{current={...current,state:'cancelled',reason:'operator_cancelled',needs_resume:false,warning:'transport_unconfirmed'};resolve(response({request:current,durability:'recorded',transport_settled:false}))}}):original(url,options);
const a=element('artifact-cancel').click(),b=element('artifact-cancel').click();await flush();assert.strictEqual(calls.filter(c=>c.url.endsWith('/cancel')).length,1);
finish();await Promise.all([a,b]);responder=original;current={...current,warning:null};await activate('artifact-refresh');
assert(element('artifact-source').textContent.includes('unconfirmed'));assert(element('artifact-status').textContent.includes('Cancelled'));
""")

    def test_deadline_get404_late_save_and_reload_keep_unknown_identity(self):
        self.run_js(r"""
await open();const original=responder;let finish;responder=async(url,options)=>url.endsWith('/requests')?new Promise(resolve=>{finish=()=>{current={...current,request_id:JSON.parse(options.body).request_id};resolve(response({request:current,durability:'recorded'},202))}}):original(url,options);
element('artifact-instruction').value='PRIVATE_INSTRUCTION';const pending=element('artifact-submit').click();
for(let i=0;i<20&&!finish;i++)await flush();assert(finish);const first=JSON.parse(calls.find(c=>c.method==='POST').body);
const deadline=[...timers.values()].find(t=>t.delay===20000);assert(deadline);deadline.fn();await pending;assert(!element('artifact-submit').disabled);
responder=async(url,options)=>url.endsWith('/requests/'+first.request_id)?response({code:'not_found',error:'Not found yet'},404):original(url,options);
await activate('artifact-refresh');assert(element('artifact-status').textContent.includes('Not found yet'));
window.ArtifactDocuments.close();load('static/artifacts.js');window.ArtifactDocuments.init();await window.ArtifactDocuments.open();await flush();
assert.strictEqual(calls.filter(c=>c.method==='POST').length,1);assert(element('artifact-status').textContent.includes('Not found yet'));
finish();responder=original;await activate('artifact-refresh');assert(element('artifact-status').textContent.includes('Queued'));
assert(calls.filter(c=>c.url.includes('/requests/')).every(c=>c.url.includes(first.request_id)));
""")

    def test_unknown_abandon_and_definitive_refusal_are_explicit(self):
        self.run_js(r"""
await open();const original=responder;responder=async()=>{throw Error('lost response')};await submit();
const first=JSON.parse(calls.find(c=>c.method==='POST').body).request_id;
await activate('artifact-abandon');assert(!element('artifact-abandon-warning').hidden);
assert(element('artifact-abandon-warning').textContent.includes('The earlier request may still finish and could create a second document.'));
await activate('artifact-abandon-confirm');responder=original;await submit();
assert.notStrictEqual(JSON.parse(calls.filter(c=>c.method==='POST').at(-1).body).request_id,first);
current={...current,state:'fulfilled',version_id:'c'.repeat(32),label:'ready'};await activate('artifact-refresh');
responder=async(url,options)=>url.endsWith('/requests')?response({code:'source_unavailable',error:'Source unavailable.',durability:'not_recorded'},409):original(url,options);
await submit();const refused=JSON.parse(calls.filter(c=>c.method==='POST').at(-1).body).request_id;responder=original;await submit();
assert.notStrictEqual(JSON.parse(calls.filter(c=>c.method==='POST').at(-1).body).request_id,refused);
""")

    def test_refusal_codes_causes_non_json_and_durability_are_visible(self):
        self.run_js(r"""
await open();const original=responder;
for(const code of ['source_unavailable','source_too_large','request_too_large','channel_inactive','channel_mismatch','session_unknown','run_unknown','boundary_held','request_conflict','not_ready','storage_unavailable','unexpected_failure']){
 responder=async()=>response({code,error:'Literal <b>'+code+'</b>',durability:'not_recorded'},409);await submit();
 assert(element('artifact-error').textContent.includes(code));assert(element('artifact-error').textContent.includes('not_recorded'));
}
for(const cause of ['capability_off','no_live_instance','no_agent_role','not_supported','unmanaged','binding_changed','runtime_unverified','ambiguous','producer_unavailable']){
 responder=async()=>response({code:'no_author_available',cause,error:'No author available',author_name:'<img author>',examined_roles:2,durability:'not_recorded'},409);await submit();
 // no_live_instance uses the approved plain-language sentence instead of the server text.
 assert(element('artifact-error').textContent.includes(cause==='capability_off'?'Artifact authoring is not enabled':
  cause==='no_live_instance'?'The agent that ran this session is no longer running.':'No author available'));
}
responder=async()=>response({code:'request_conflict',cause:'packet_exists',error:'Submit with a new request_id',durability:'not_recorded'},409);await submit();assert(element('artifact-error').textContent.includes('new request_id'));
responder=async()=>({ok:false,status:502,json:async()=>{throw Error('<html>PRIVATE_PROXY</html>')}});await submit();
assert(!element('artifact-error').textContent.includes('PRIVATE_PROXY'));assert(element('artifact-status').textContent.includes('Not confirmed'));
assert.strictEqual(document.body.querySelectorAll('img').length,0);
""")

    def test_archived_held_policy_labels_keyboard_and_latest_only_disclosure(self):
        self.run_js(r"""
await open();assert.strictEqual(document.activeElement,element('artifact-session-select'));
for(const id of ['artifact-session-select','artifact-instruction'])assert(document.body.querySelectorAll('label').some(label=>label.htmlFor===id));
assert.strictEqual(element('artifact-status').getAttribute('aria-live'),'polite');assert.strictEqual(element('artifact-error').getAttribute('role'),'alert');
await submit();await submit();assert(element('artifact-documents-panel').textContent.includes('Earlier requests are not listed'));
window.ChannelLifecycle.canWrite=()=>false;Hub.emit('channel_lifecycle',{});assert(element('artifact-submit').disabled);assert(!element('artifact-cancel').disabled);
assert(element('artifact-documents-panel').textContent.toLowerCase().includes('archived'));
window.ChannelLifecycle.canWrite=()=>true;window.ChannelLifecycle.ownerAvailable=()=>false;Hub.emit('channel_lifecycle',{});assert(element('artifact-submit').disabled);
await element('artifact-documents-panel').dispatch('keydown',{key:'Escape'});assert(element('artifact-documents-panel').hidden);assert.strictEqual(document.activeElement,element('artifact-documents-open'));
""")

    def test_deduplicated_pages_rename_delete_and_stale_list(self):
        self.run_js(r"""
let page=0;const original=responder;responder=async(url,options)=>url.includes('/sessions?')?response({sessions:page++?[session,{...session,session_id:2}]:[session],offset:0,has_more:page===1}):original(url,options);
await open();await activate('artifact-more-sessions');assert.strictEqual(element('artifact-session-select').children.length,2);assert(element('artifact-session-select').textContent.includes('complete'));
responder=original;await submit();Hub.emit('channel_renamed',{old_name:'review',new_name:'renamed'});assert(element('artifact-documents-panel').hidden);
assert(!storage.has('artifact-request:review'));assert(storage.has('artifact-request:renamed'));
Hub.emit('channel_deleted',{channel:'renamed'});assert(!storage.has('artifact-request:renamed'));
window.activeChannel='review';let finish;responder=async()=>new Promise(resolve=>{finish=resolve});const opening=window.ArtifactDocuments.open();await flush();
window.activeChannel='peer';for(const fn of watchers.get('activeChannel')||[])await fn('peer');finish(response({sessions:[{...session,title:'STALE_LIST'}],offset:0,has_more:false}));await opening;
assert(element('artifact-documents-panel').hidden);assert(!element('artifact-session-select').textContent.includes('STALE_LIST'));
""")

    def test_unknown_reload_retry_requires_original_instruction_and_lazy_token(self):
        self.run_js(r"""
await open();const original=responder;responder=async()=>{throw Error('lost response')};await submit();const first=JSON.parse(calls.find(c=>c.method==='POST').body);
window.ArtifactDocuments.close();responder=async(url,options)=>url.includes('/requests/')?response({code:'not_found',error:'Not found'},404):original(url,options);
load('static/artifacts.js');window.ArtifactDocuments.init();await window.ArtifactDocuments.open();await flush();
element('artifact-instruction').value='CHANGED INSTRUCTION';await activate('artifact-submit');assert.strictEqual(calls.filter(c=>c.method==='POST').length,1);
window.SESSION_TOKEN='ROTATED_TOKEN';responder=original;await submit();const posts=calls.filter(c=>c.method==='POST');assert.strictEqual(posts.length,2);
assert.deepStrictEqual(JSON.parse(posts[1].body),first);assert.strictEqual(new Headers(posts[1].headers).get('X-Session-Token'),'ROTATED_TOKEN');
""")

    def test_stale_create_read_and_unknown_rename_do_not_apply_old_content(self):
        self.run_js(r"""
await open();const original=responder;let finish;responder=async(url,options)=>url.endsWith('/requests')?new Promise(resolve=>{finish=resolve}):original(url,options);
element('artifact-instruction').value='PRIVATE_INSTRUCTION';const pending=element('artifact-submit').click();for(let i=0;i<20&&!finish;i++)await flush();assert(finish);
const first=JSON.parse(calls.find(c=>c.method==='POST').body);Hub.emit('channel_renamed',{old_name:'review',new_name:'renamed'});window.activeChannel='renamed';
finish(response({request:{...current,request_id:first.request_id,author_name:'STALE_CREATE'},durability:'recorded'},202));await pending;assert(element('artifact-documents-panel').hidden);
responder=async(url,options)=>url.includes('/sessions?')?response({sessions:[session],offset:0,has_more:false}):url.includes('/requests/')?response({code:'not_found',error:'Not found'},404):original(url,options);
await window.ArtifactDocuments.open();responder=async(url,options)=>{if(url.endsWith('/requests'))return response({request:{...current,channel:'renamed',request_id:first.request_id},durability:'recorded'},200);return original(url,options)};
await submit();const posts=calls.filter(c=>c.method==='POST');assert.strictEqual(JSON.parse(posts[1].body).channel,'review');assert.strictEqual(JSON.parse(posts[1].body).request_id,first.request_id);
current={...current,channel:'renamed',request_id:first.request_id,state:'fulfilled',label:'ready',version_id:'c'.repeat(32)};responder=original;await activate('artifact-refresh');
responder=async(url,options)=>url.endsWith('/document')?new Promise(resolve=>{finish=resolve}):original(url,options);
const reading=element('artifact-read').click();await flush();window.activeChannel='peer';for(const fn of watchers.get('activeChannel')||[])await fn('peer');
finish(response({version:{id:'c'.repeat(32)},markdown:'STALE_READ'}));await reading;
assert(element('artifact-reader').hidden);assert.strictEqual(element('artifact-reader').textContent,'');
""")

    def test_download_rejects_proxy_html_without_creating_a_file(self):
        self.run_js(r"""
await open();await submit();current={...current,state:'fulfilled',label:'ready',version_id:'c'.repeat(32)};await activate('artifact-refresh');
const original=responder;responder=async(url,options)=>url.endsWith('/download')?response('<html>PRIVATE_PROXY</html>',200,{'Content-Type':'text/html'}):original(url,options);
await activate('artifact-download');assert.strictEqual(downloads.length,0);assert(element('artifact-error').textContent);assert(!element('artifact-error').textContent.includes('PRIVATE_PROXY'));
""")

    def test_draft_survives_close_in_memory_without_browser_body_storage(self):
        self.run_js(r"""
await open();element('artifact-instruction').value='DRAFT_ONLY_IN_MEMORY';window.ArtifactDocuments.close();await window.ArtifactDocuments.open();
assert.strictEqual(element('artifact-instruction').value,'DRAFT_ONLY_IN_MEMORY');for(const value of storage.values())assert(!value.includes('DRAFT_ONLY_IN_MEMORY'));
""")

    def test_pre_effect_null_durability_refusals_clear_new_unknown_and_prechecks_preserve_text(self):
        self.run_js(r"""
await open();const original=responder;
for(const bad of ['', '   \t\r\n', 'bad\u0000text', 'bad\u007ftext', 'é'.repeat(16385)]){
 element('artifact-instruction').value=bad;await activate('artifact-submit');assert.strictEqual(calls.filter(c=>c.method==='POST').length,0);
 assert(element('artifact-error').textContent);assert(!element('artifact-submit').disabled);
}
for(const code of ['invalid_request','request_too_large','operator_forbidden','no_author_available','source_unavailable','source_too_large','session_unknown','run_unknown','channel_mismatch','channel_inactive']){
 responder=async(url,options)=>url.endsWith('/requests')?response({code,error:'Definitive '+code,durability:null,request:null},409):original(url,options);
 await submit();assert(!element('artifact-status').textContent.includes('Not confirmed'),code);assert(!element('artifact-submit').disabled);
 const previous=JSON.parse(calls.filter(c=>c.method==='POST').at(-1).body).request_id;
 responder=original;element('artifact-instruction').value='  keep\tthis\nexactly  ';await activate('artifact-submit');
 const next=JSON.parse(calls.filter(c=>c.method==='POST').at(-1).body);assert.notStrictEqual(previous,next.request_id);assert.strictEqual(next.instruction,'  keep\tthis\nexactly  ');
}
""")

    def test_live_regions_only_change_for_changed_text_and_focus_is_not_stolen(self):
        self.run_js(r"""
load('static/artifacts.js');window.ArtifactDocuments.init();let finish;const original=responder;
responder=async(url,options)=>url.includes('/sessions?')?new Promise(resolve=>{finish=resolve}):original(url,options);
const opening=window.ArtifactDocuments.open();await flush();element('artifact-instruction').focus();
finish(response({sessions:[session],offset:0,has_more:false}));await opening;assert.strictEqual(document.activeElement,element('artifact-instruction'));
responder=original;await submit();const names=['artifact-status','artifact-source','artifact-error'];
const counts=names.map(name=>element(name).textWrites);await activate('artifact-refresh');assert.deepStrictEqual(names.map(name=>element(name).textWrites),counts);
""")

    def test_digest_is_request_salted_and_every_path_id_is_encoded(self):
        self.run_js(r"""
const encoded=[];context.encodeURIComponent=value=>{encoded.push(value);return encodeURIComponent(value)};
await open();await submit();const first=JSON.parse([...storage.values()][0]);
assert.strictEqual(first.instruction_sha256,require('crypto').createHash('sha256').update(first.request_id+':PRIVATE_INSTRUCTION').digest('hex'));
current={...current,state:'fulfilled',version_id:'c'.repeat(32),label:'ready'};encoded.length=0;await activate('artifact-refresh');assert(encoded.includes(first.request_id));
encoded.length=0;await activate('artifact-read');assert(encoded.includes(first.request_id));
encoded.length=0;await activate('artifact-download');assert(encoded.includes(current.version_id));
current={...current,state:'queued',version_id:null};await activate('artifact-refresh');encoded.length=0;await activate('artifact-cancel');assert(encoded.includes(first.request_id));
await submit();const second=JSON.parse([...storage.values()][0]);assert.notStrictEqual(first.instruction_sha256,second.instruction_sha256);
current={...current,state:'fulfilled',version_id:'../not-a-version',label:'ready'};await activate('artifact-refresh');const before=downloads.length;
await activate('artifact-download');assert.strictEqual(downloads.length,before);assert(!calls.some(c=>c.url.includes('not-a-version')));
""")

    def test_url_revoke_is_delayed_and_close_cleans_it_up(self):
        self.run_js(r"""
await open();await submit();current={...current,state:'fulfilled',version_id:'c'.repeat(32),label:'ready'};await activate('artifact-refresh');await activate('artifact-download');
assert.strictEqual(revoked.length,0);assert([...timers.values()].some(timer=>timer.delay===1000));
window.ArtifactDocuments.close();assert.strictEqual(revoked.length,1);assert.strictEqual(timers.size,0);
""")

    def test_cancel_not_found_does_not_claim_a_running_worker_and_refresh_serializes(self):
        self.run_js(r"""
await open();await submit();const original=responder;let finish;
responder=async(url,options)=>url.endsWith('/cancel')?new Promise(resolve=>{finish=()=>resolve(response({code:'not_found',error:'Not found'},404))}):original(url,options);
const cancel=element('artifact-cancel').click();await flush();assert(element('artifact-refresh').disabled);
const gets=calls.filter(c=>c.method!=='POST').length;await activate('artifact-refresh');await element('artifact-refresh').onclick();assert.strictEqual(calls.filter(c=>c.method!=='POST').length,gets);
finish();await cancel;assert(!element('artifact-source').textContent.includes('worker may still be running'));
""")

    def test_hidden_document_pauses_polling_and_list_retry_clears_its_error(self):
        self.run_js(r"""
const original=responder;responder=async()=>response({code:'storage_unavailable',error:'LIST_UNAVAILABLE'},503);
await open();assert(element('artifact-error').textContent.includes('LIST_UNAVAILABLE'));responder=original;
assert(!element('artifact-more-sessions').hidden);await activate('artifact-more-sessions');assert.strictEqual(element('artifact-error').textContent,'');
await submit();document.hidden=true;for(const fn of document.listeners.visibilitychange||[])await fn();assert.strictEqual(timers.size,0);
document.hidden=false;for(const fn of document.listeners.visibilitychange||[])await fn();assert([...timers.values()].some(timer=>timer.delay===2000));
""")

    def test_stop_singular_and_zero_are_not_false_counts(self):
        self.run_js(r"""
load('static/sessions.js');context.panel=new Element('section');context.s={id:1,state:'stopped',admitted_events:[],cancellation_receipts:[],termination_offers:[],quarantined_events:[],artifact_cancellation:{warning:'transport_unconfirmed',unconfirmed_dispatch_ids:['a'.repeat(32)]}};
vm.runInContext('renderStopControls(panel,s)',context);assert(!context.panel.textContent.includes('1 known document dispatches'));
context.s.artifact_cancellation={warning:'storage_unavailable',unconfirmed_dispatch_ids:[]};vm.runInContext('renderStopControls(panel,s)',context);
assert(!context.panel.textContent.includes('0 known'));assert(context.panel.textContent.toLowerCase().includes('unconfirmed'));
""",module=False)

    def test_definitive_500_and_packet_exists_reset_but_unknown_500_does_not(self):
        self.run_js(r"""
await open();const original=responder;
for(const data of [{code:'unexpected_failure',error:'No effect',durability:'not_recorded'},{code:'request_conflict',cause:'packet_exists',error:'New request id',durability:null}]){
 responder=async(url,options)=>url.endsWith('/requests')?response(data,500):original(url,options);await submit();const id=JSON.parse(calls.filter(c=>c.method==='POST').at(-1).body).request_id;
 responder=original;await submit();assert.notStrictEqual(JSON.parse(calls.filter(c=>c.method==='POST').at(-1).body).request_id,id);
}
responder=async(url,options)=>url.endsWith('/requests')?response({code:'storage_unavailable',error:'Unknown effect',durability:null},503):original(url,options);await submit();const prior=JSON.parse(calls.filter(c=>c.method==='POST').at(-1).body).request_id;
await submit();assert.strictEqual(JSON.parse(calls.filter(c=>c.method==='POST').at(-1).body).request_id,prior);
""")

    def test_encoding_channel_and_ids_never_becomes_url_navigation(self):
        self.run_js(r"""
window.activeChannel='review?unexpected=1&more=2';await open();assert(calls[0].url.includes('channel=review%3Funexpected%3D1%26more%3D2'));
assert(!calls[0].url.includes('?unexpected='));assert(calls.every(call=>call.url.startsWith('/api/artifacts/')));
""")

    def test_errors_and_author_labels_are_literal_text(self):
        self.run_js(r"""
current={...current,author_name:'<img src=x onerror=evil()>'};await open();await submit();
assert(element('artifact-source').textContent.includes('<img src=x onerror=evil()>'));assert.strictEqual(document.body.querySelectorAll('img').length,0);
const original=responder;responder=async(url,options)=>url.endsWith('/requests')?response({code:'source_unavailable',error:'<b>LITERAL_ERROR</b>',durability:null},409):original(url,options);
await submit();assert(element('artifact-error').textContent.includes('<b>LITERAL_ERROR</b>'));assert.strictEqual(document.body.querySelectorAll('b').length,0);
""")

    def test_close_aborts_inflight_and_hidden_completion_does_not_schedule(self):
        self.run_js(r"""
await open();await submit();let finish;const original=responder;
responder=async(url,options)=>url.includes('/requests/')?new Promise(resolve=>{finish=resolve}):original(url,options);
const getting=element('artifact-refresh').click();await flush();const signal=calls.at(-1).signal;window.ArtifactDocuments.close();assert(signal.aborted);await getting;
assert.strictEqual(timers.size,0);finish(response(current));await flush();
responder=original;await window.ArtifactDocuments.open();await flush();
responder=async(url,options)=>url.includes('/requests/')?new Promise(resolve=>{finish=resolve}):original(url,options);
const hidden=element('artifact-refresh').click();await flush();document.hidden=true;for(const fn of document.listeners.visibilitychange||[])await fn();
finish(response(current));await hidden;assert.strictEqual(timers.size,0);
""")

    def test_stale_status_after_cancel_cannot_restore_working(self):
        self.run_js(r"""
await open();await submit();const original=responder;let finish;
responder=async(url,options)=>url.includes('/requests/')&&!url.endsWith('/cancel')?new Promise(resolve=>{finish=resolve}):original(url,options);
const getting=element('artifact-refresh').click();await flush();await activate('artifact-cancel');
finish(response({...current,state:'active',label:'working',reason:null}));await getting;
assert(element('artifact-status').textContent.includes('Cancelled'));
""")

    def test_stale_read_serial_is_independent_of_single_flight(self):
        self.allow_inflight_reentry('if (!active(s) || !s.row?.version_id || s.reading) return;',
                                   'if (!active(s) || !s.row?.version_id) return;')
        self.run_js(r"""
await open();await submit();current={...current,state:'fulfilled',version_id:'c'.repeat(32),label:'ready'};await activate('artifact-refresh');
const original=responder;const pending=[];responder=async(url,options)=>url.endsWith('/document')?new Promise(resolve=>pending.push(resolve)):original(url,options);
const older=element('artifact-read').onclick();await flush();const newer=element('artifact-read').onclick();await flush();assert.strictEqual(pending.length,2);
pending[1](response({markdown:'NEW_READ'}));await newer;pending[0](response({markdown:'OLD_READ'}));await older;
assert.strictEqual(element('artifact-reader').textContent,'NEW_READ');
""")

    def test_stale_list_serial_is_independent_of_single_flight(self):
        self.allow_inflight_reentry('if (!active(s) || s.listBusy) return;','if (!active(s)) return;')
        self.run_js(r"""
await open();const original=responder;const pending=[];
responder=async(url,options)=>url.includes('/sessions?')?new Promise(resolve=>pending.push(resolve)):original(url,options);
const older=element('artifact-more-sessions').onclick();await flush();const newer=element('artifact-more-sessions').onclick();await flush();
pending[1](response({sessions:[{...session,session_id:3,title:'NEW_LIST'}],offset:20,has_more:false}));await newer;
pending[0](response({sessions:[{...session,session_id:2,title:'OLD_LIST'}],offset:20,has_more:false}));await older;
assert(element('artifact-session-select').textContent.includes('NEW_LIST'));assert(!element('artifact-session-select').textContent.includes('OLD_LIST'));
""")

    def test_stale_create_identity_is_independent_of_single_flight(self):
        self.allow_inflight_reentry('if (!active(s) || s.submitting || !writable(s)) return;',
                                   'if (!active(s) || !writable(s)) return;')
        self.run_js(r"""
await open();const original=responder;const pending=[];
responder=async(url,options)=>url.endsWith('/requests')?new Promise(resolve=>pending.push({body:JSON.parse(options.body),resolve})):original(url,options);
element('artifact-instruction').value='PRIVATE_INSTRUCTION';const older=element('artifact-submit').onclick();for(let i=0;i<20&&pending.length<1;i++)await flush();
await activate('artifact-abandon');await activate('artifact-abandon-confirm');const newer=element('artifact-submit').onclick();for(let i=0;i<20&&pending.length<2;i++)await flush();assert.strictEqual(pending.length,2);
pending[1].resolve(response({request:{...current,request_id:pending[1].body.request_id,author_name:'NEW_CREATE'},durability:'recorded'},202));await newer;
pending[0].resolve(response({request:{...current,request_id:pending[0].body.request_id,author_name:'OLD_CREATE'},durability:'recorded'},202));await older;
assert(element('artifact-source').textContent.includes('NEW_CREATE'));assert(!element('artifact-source').textContent.includes('OLD_CREATE'));
""")

    def test_older_download_error_does_not_replace_new_request_status(self):
        self.run_js(r"""
await open();await submit();current={...current,state:'fulfilled',version_id:'c'.repeat(32),label:'ready'};await activate('artifact-refresh');
const original=responder;let fail;responder=async(url,options)=>url.endsWith('/download')?new Promise((resolve,reject)=>{fail=()=>reject(Error('OLD_DOWNLOAD_ERROR'))}):original(url,options);
const older=element('artifact-download').click();await flush();current={...current,state:'queued',version_id:null,label:'queued'};await submit();
const before=element('artifact-error').textContent;fail();await older;assert.strictEqual(element('artifact-error').textContent,before);
""")

    def test_session_options_include_start_time_so_same_titles_differ(self):
        self.run_js(r"""
const original=responder;
responder=async(url,options)=>url.includes('/sessions?')?response({sessions:[
 {...session,session_id:1,title:'Debate',state:'complete',started_at:1700000000},
 {...session,session_id:2,run_id:'d'.repeat(32),title:'Debate',state:'complete',started_at:1700086400}],offset:0,has_more:false}):original(url,options);
await open();
const texts=element('artifact-session-select').children.map(o=>o.textContent);
assert.strictEqual(texts.length,2);
assert.notStrictEqual(texts[0],texts[1],texts.join('|'));
const stamp=s=>new Date(s*1000).toLocaleString([],{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
assert.strictEqual(texts[0],'Debate (complete) · '+stamp(1700000000));
assert.strictEqual(texts[1],'Debate (complete) · '+stamp(1700086400));
""")

    def test_no_live_author_error_uses_plain_language(self):
        self.run_js(r"""
const original=responder;
responder=async(url,options)=>url.endsWith('/requests')&&options.method==='POST'?response({code:'no_author_available',cause:'no_live_instance',
 durability:'not_recorded',examined_roles:4,author_name:'x'},409):original(url,options);
await open();await submit();
assert.strictEqual(element('artifact-error').textContent,
 'The agent that ran this session is no longer running. Start a new session with your current team to write from it.');
""")

    def test_other_errors_keep_existing_suffixes(self):
        self.run_js(r"""
const original=responder;
responder=async(url,options)=>url.endsWith('/requests')&&options.method==='POST'?response({code:'invalid_request',durability:'not_recorded',examined_roles:2},400):original(url,options);
await open();await submit();
const text=element('artifact-error').textContent;
assert(text.includes('Agent roles checked: 2.')&&text.includes('Effect: not_recorded.'),text);
""")

    def test_read_document_scrolls_reader_into_view_once(self):
        self.run_js(r"""
await open();await submit();current={...current,state:'fulfilled',label:'ready',version_id:'c'.repeat(32)};await activate('artifact-refresh');
const scrolls=[];element('artifact-reader').scrollIntoView=arg=>scrolls.push(arg);
await activate('artifact-read');
assert.strictEqual(element('artifact-reader').textContent,markdown);
// The argument object comes from the vm realm, so compare by value.
assert.strictEqual(JSON.stringify(scrolls),JSON.stringify([{block:'nearest'}]));
""")

    def test_documents_panel_has_form_and_reader_columns(self):
        # Idea 3: the form sits in a left column and the document text in a right one.
        self.run_js(r"""
await open();
const panel=element('artifact-documents-panel');
const form=element('artifact-instruction').parentElement, side=element('artifact-reader').parentElement;
assert(form.className.includes('artifact-form'),form.className);
assert(side.className.includes('artifact-side'),side.className);
assert.strictEqual(form.parentElement,panel);assert.strictEqual(side.parentElement,panel);
for(const id of ['artifact-session-select','artifact-submit','artifact-status','artifact-error','artifact-refresh'])
 assert(form===element(id).parentElement||form.querySelectorAll('#'+id).length,'not in form column: '+id);
""")

    def test_empty_session_list_shows_disabled_placeholder(self):
        self.run_js(r"""
const original=responder;
responder=async(url,options)=>url.includes('/sessions?')?response({sessions:[],offset:0,has_more:false}):original(url,options);
await open();
const select=element('artifact-session-select');
assert.strictEqual(select.disabled,true);
assert.strictEqual(select.children.length,1);
assert.strictEqual(select.children[0].textContent,'No finished sessions yet');
assert.strictEqual(select.children[0].value,'');
assert.strictEqual(element('artifact-submit').disabled,true);
""")
