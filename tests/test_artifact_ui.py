"""Reduced20 ROOT UI reds. Actual JS in Node vm, unit DOM/fetch/clock only.

Missing artifacts.js is infrastructure evidence; later assertions are unobserved
until the module exists. Existing Stop renderer cases are behavioral reds.
Rendered/browser/transport acceptance remains a separate guarded deliverable.
"""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

BOOT = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const root=process.argv[1], nodes=new Map(), timers=new Map(), calls=[], watchers=new Map(), hubs=new Map();
let timerID=0, responder;
class Element {
 constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.dataset={};this.style={};this.hidden=false;this.disabled=false;this.value='';this._text='';this.listeners={};this.className='';this.isConnected=true;
 this.classList={add:(...names)=>{this.className += ' '+names.join(' ')},remove:()=>{},toggle:()=>{},contains:n=>this.className.split(' ').includes(n)};}
 set id(v){this._id=v;nodes.set(v,this)} get id(){return this._id}
 set textContent(v){this._text=String(v);this.children=[]} get textContent(){return this._text+this.children.map(c=>typeof c==='string'?c:c.textContent).join(' ')}
 set innerHTML(v){throw Error('UI must build safe DOM/text, not interpolate HTML')}
 append(...items){for(const c of items){this.children.push(c);if(typeof c!=='string')c.parentElement=this}}
 appendChild(c){this.append(c);return c} replaceChildren(...items){this.children=[];this._text='';this.append(...items)}
 after(...items){this.parentElement?.append(...items)} remove(){this.isConnected=false;if(this.parentElement)this.parentElement.children=this.parentElement.children.filter(c=>c!==this)}
 setAttribute(k,v){this[k]=String(v)} getAttribute(k){return this[k]??null}
 addEventListener(k,fn){(this.listeners[k]??=[]).push(fn)} removeEventListener(){}
 async dispatch(kind){const e={preventDefault(){},stopPropagation(){},target:this,currentTarget:this};if(this.disabled)return;
  const fn=this['on'+kind];if(fn)await fn(e);for(const listener of this.listeners[kind]||[])await listener(e);}
 async click(){if(this.tagName==='A')downloads.push({href:this.href,download:this.download});return this.dispatch('click')}
 focus(){document.activeElement=this}
 querySelectorAll(selector){const result=[];for(const c of this.children){if(typeof c==='string')continue;
 const match=selector.startsWith('#')?c.id===selector.slice(1):selector.startsWith('.')?c.className.split(' ').includes(selector.slice(1)):c.tagName.toLowerCase()===selector.toLowerCase();
 if(match)result.push(c);result.push(...c.querySelectorAll(selector));}return result}
 querySelector(s){return this.querySelectorAll(s)[0]||null}
}
const document={body:new Element('body'),activeElement:null,createElement:t=>new Element(t),
 getElementById:id=>nodes.get(id)||null,querySelector:s=>s.startsWith('#')?nodes.get(s.slice(1)):document.body.querySelector(s),querySelectorAll:s=>document.body.querySelectorAll(s)};
for(const [id,tag] of [['session-bar','div'],['session-launch-btn','button'],['artifact-documents-open','button']]){const e=new Element(tag);e.id=id;document.body.append(e)}
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
 json:async()=>JSON.parse(JSON.stringify(data)),blob:async()=>new Blob([typeof data==='string'?data:JSON.stringify(data)],{type:headers['Content-Type']||'text/markdown'}),text:async()=>String(data)});
const session={session_id:1,run_id:'b'.repeat(32),title:'Completed source',state:'complete',started_at:10,source_so_far:false,title_truncated:false};
let current={request_id:'a'.repeat(32),channel:'review',state:'queued',reason:'queued',label:'queued',author_name:'Fixture author',created_at:1,updated_at:1,version_id:null,needs_resume:false,warning:null,
 source:{session_id:1,run_id:session.run_id,message_count:2,packet_bytes:512,scope_sha256:'e'.repeat(64),input_revision:'f'.repeat(64),source_so_far:false}};
let markdown='# café\r\n<script>alert(1)</script>\n<img src=x onerror=evil()>\n[jump](javascript:evil())';
responder=async(url,options)=>{
 if(url.includes('/sessions?'))return response({sessions:[session],offset:0,has_more:false});
 if(url.endsWith('/requests')&&options.method==='POST'){current={...current,request_id:JSON.parse(options.body).request_id};return response({request:current,durability:'recorded',transport_settled:false},202)}
 if(url.endsWith('/cancel')){current={...current,state:'cancelled',reason:'operator_cancelled',label:'failed'};return response({request:current,durability:'recorded',transport_settled:false})}
 if(url.endsWith('/download'))return response(markdown,200,{'Content-Type':'text/markdown; charset=utf-8'});
 if(url.endsWith('/document')||url.includes('/versions/'))return response({version:{id:current.version_id},markdown});
 return response(current);
};
const context=vm.createContext({window,document,Hub,Store,sessionStorage,console,crypto:window.crypto,
 URL:URLClass,Blob,Headers,AbortController,TextEncoder,setTimeout:later,clearTimeout:clear,setInterval:()=>0,clearInterval(){},
 fetch:async(url,options={})=>{url=String(url);calls.push({url,...options});return responder(url,options)}});
function load(file){vm.runInContext(fs.readFileSync(root+'/'+file,'utf8'),context,{filename:file})}
function element(id){const value=nodes.get(id);assert(value,'Missing control '+id);return value}
async function activate(id){await element(id).click();await flush()}
async function flush(){await new Promise(resolve=>setImmediate(resolve))}
async function open(){load('static/artifacts.js');assert(window.ArtifactDocuments,'Missing frozen UI entry');window.ArtifactDocuments.init();await window.ArtifactDocuments.open();await flush();
 element('artifact-session-select').value='1';await element('artifact-session-select').dispatch('change');await flush();}
async function submit(){element('artifact-instruction').value='PRIVATE_INSTRUCTION';await activate('artifact-submit')}
async function fire(){const next=timers.entries().next().value;assert(next,'Missing poll timer');timers.delete(next[0]);await next[1].fn();await flush()}
"""


class ArtifactUITests(unittest.TestCase):
    def run_js(self, body, *, module=True):
        node = shutil.which('node')
        self.assertIsNotNone(node, 'Node is required for the actual JS UI tests')
        if module:
            (ROOT / 'static/artifacts.js').read_text(encoding='utf-8')
        script = BOOT + '\n(async()=>{\n' + body + '\n})().catch(error=>{console.error(error.stack);process.exitCode=1});'
        result = subprocess.run([node, '-e', script, str(ROOT)], cwd=ROOT,
                                capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

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

    def test_completed_session_list_and_more_are_authenticated(self):
        self.run_js(r"""
let page=0;const original=responder;responder=async(url,options)=>url.includes('/sessions?')?
 response({sessions:[{...session,session_id:++page}],offset:page===1?0:20,has_more:page===1}):original(url,options);
await open();assert(element('artifact-session-select').textContent.includes('Completed source'));
await activate('artifact-more-sessions');assert(calls.some(c=>c.url.includes('offset=20')));
for(const call of calls){assert(!call.url.includes('token='));assert.strictEqual(new Headers(call.headers).get('X-Session-Token'),'OPERATOR_ONLY')}
""")

    def test_create_exact_intent_and_fresh_id_for_each_new_submit(self):
        self.run_js(r"""
await open();await submit();let posts=calls.filter(c=>c.method==='POST');assert.strictEqual(posts.length,1);
const first=JSON.parse(posts[0].body);assert.deepStrictEqual(Object.keys(first).sort(),['channel','instruction','request_id','run_id','session_id']);
assert(/^[0-9a-f]{32}$/.test(first.request_id));assert.strictEqual(first.instruction,'PRIVATE_INSTRUCTION');
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
element('artifact-instruction').value='PRIVATE_INSTRUCTION';const first=element('artifact-submit').click();const second=element('artifact-submit').click();await flush();
assert.strictEqual(calls.filter(c=>c.method==='POST').length,1);const id=JSON.parse(calls.find(c=>c.method==='POST').body).request_id;
finish();await Promise.all([first,second]);await flush();responder=original;current={...current,request_id:id};
await activate('artifact-refresh');assert(calls.some(c=>c.url.endsWith('/requests/'+id)&&c.method!=='POST'));
assert.strictEqual(calls.filter(c=>c.method==='POST').length,1);
""")

    def test_poll_backoff_terminal_and_close_dispose_timers(self):
        self.run_js(r"""
await open();await submit();assert([...timers.values()].some(t=>t.delay===2000));
const original=responder;responder=async()=>{throw Error('offline')};
for(const delay of [4000,8000,16000,30000]){await fire();assert([...timers.values()].some(t=>t.delay===delay))}
responder=original;await fire();assert([...timers.values()].some(t=>t.delay===2000));
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
await activate('artifact-download');assert.strictEqual(downloads.length,1);assert.strictEqual(downloads[0].download,'document.md');
assert.strictEqual(await blobs.get(downloads[0].href).text(),markdown);for(const timer of [...timers.values()])if(timer.delay===0)await timer.fn();
assert(revoked.includes(downloads[0].href));assert(calls.filter(c=>c.url.endsWith('/download')).every(c=>new Headers(c.headers).get('X-Session-Token')==='OPERATOR_ONLY'));
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
resolve(response({...current,state:'fulfilled',label:'ready',version_id:'c'.repeat(32)}));await refresh;await flush();
assert(element('artifact-documents-panel').hidden);assert.strictEqual(timers.size,0);
assert(element('artifact-reader').hidden||element('artifact-reader').textContent==='');
""")

    def test_ui_load_and_init_hooks_are_reachable(self):
        html=(ROOT/'static/index.html').read_text(encoding='utf-8')
        sessions=(ROOT/'static/sessions.js').read_text(encoding='utf-8')
        self.assertIn('/static/artifacts.js',html)
        self.assertIn('artifact-documents-open',html)
        self.assertIn('ArtifactDocuments.init',sessions)
