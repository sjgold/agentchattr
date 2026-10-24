// Actual-source Node VM/component checks only, not browser/native acceptance.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');
const read = name => fs.readFileSync(path.join(root, name), 'utf8');
const tests = [];
const test = (name, run) => tests.push({name, run});
const plain = value => JSON.parse(JSON.stringify(value));
const flush = async () => { for (let n = 0; n < 16; n++) await Promise.resolve(); };
const deferred = () => { let resolve, reject; const promise = new Promise((a,b) => { resolve=a; reject=b; }); return {promise, resolve, reject}; };
const descendants = element => element.children.flatMap(child => [child, ...descendants(child)]);

class Element {
  constructor(tag='div') {
    this.tagName=tag.toUpperCase(); this.children=[]; this.parentNode=null; this.dataset={};
    this.attributes={}; this.style={}; this.listeners={}; this.value=''; this.className='';
    this.disabled=false; this.hidden=false; this.isConnected=true; this._text='';
    this.classList={contains: name=>this.className.split(/\s+/).includes(name),
      add: name=>{this.className=[...new Set([...this.className.split(/\s+/),name])].join(' ').trim();},
      remove: name=>{this.className=this.className.split(/\s+/).filter(x=>x!==name).join(' ');}, toggle:()=>{}};
  }
  set textContent(value) { this._text=String(value); this.children=[]; }
  get textContent() { return this._text+this.children.map(x=>x.textContent||'').join(' '); }
  set innerHTML(value) { this._html=String(value); this.children=[]; this._text=''; }
  get innerHTML() { return this._html||''; }
  appendChild(child) { child.remove?.(); child.parentNode=this; child.isConnected=this.isConnected; this.children.push(child); return child; }
  append(...children) { for(const child of children) this.appendChild(typeof child==='string'?{textContent:child}:child); }
  replaceChildren(...children) { this.children=[]; this._text=''; this.append(...children); }
  remove() { if(this.parentNode) this.parentNode.children=this.parentNode.children.filter(x=>x!==this); this.parentNode=null; this.isConnected=false; }
  setAttribute(name,value) { this.attributes[name]=String(value); if(name==='id')this.id=String(value); }
  getAttribute(name) { return this.attributes[name]??null; }
  removeAttribute(name) { delete this.attributes[name]; }
  addEventListener(name,fn) { (this.listeners[name]||=[]).push(fn); }
  removeEventListener(name,fn) { this.listeners[name]=(this.listeners[name]||[]).filter(x=>x!==fn); }
  dispatchEvent(event) { event.target||=this; for(const fn of this.listeners[event.type]||[])fn(event); return true; }
  click() { if(!this.disabled){this.onclick?.({target:this,stopPropagation(){},preventDefault(){}});this.dispatchEvent({type:'click'});} }
  focus(){this.focused=true;} select(){this.focus();}
  showModal(){this.open=true;} close(){this.open=false;this.dispatchEvent({type:'close'});}
  get lastElementChild(){return this.children.at(-1)||null;}
  closest(selector){let node=this;while(node){if(node.matches?.(selector))return node;node=node.parentNode;}return null;}
  contains(child){return child===this||descendants(this).includes(child);}
  insertAdjacentElement(position,child){assert.equal(position,'afterend'); const p=this.parentNode; child.parentNode=p;p.children.splice(p.children.indexOf(this)+1,0,child);}
  matches(selector) {
    const attr=selector.match(/\[([^=\]]+)(?:=["']?([^"'\]]+)["']?)?\]/);
    const base=selector.replace(/\[[^\]]+\]/g,'');
    if(attr){const key=attr[1];const actual=key.startsWith('data-')?this.dataset[key.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]:this[key]??this.getAttribute(key);if(attr[2]!==undefined?String(actual)!==attr[2]:actual===undefined)return false;}
    if(base.startsWith('#'))return this.id===base.slice(1);
    if(base.startsWith('.'))return base.slice(1).split('.').every(x=>this.classList.contains(x));
    return !base||base==='*'||this.tagName.toLowerCase()===base.toLowerCase();
  }
  querySelectorAll(selector){let roots=[this];for(const part of selector.trim().split(/\s+/))roots=[...new Set(roots.flatMap(x=>descendants(x).filter(e=>e.matches?.(part))))];return roots;}
  querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
}
function environment(){
  const body=new Element('body'), sends=[], opens=[], requests=[], timers=new Map();let clock=0,id=0;
  const document={body,createElement:tag=>new Element(tag),createTextNode:text=>({textContent:text}),
    getElementById:name=>descendants(body).find(x=>x.id===name)||null,
    querySelector:selector=>body.querySelector(selector),querySelectorAll:selector=>body.querySelectorAll(selector),
    addEventListener(){},removeEventListener(){}};
  const context=vm.createContext({console,document,AbortController,URL,URLSearchParams,TextEncoder,
    DOMException,Event:class{constructor(type,options={}){this.type=type;Object.assign(this,options);}},
    CustomEvent:class{constructor(type,options={}){this.type=type;Object.assign(this,options);}},
    setTimeout(fn,delay=0){const key=++id;timers.set(key,{at:clock+delay,fn});return key;},clearTimeout(key){timers.delete(key);},
    fetch(url,options={}){const result=deferred();const request={url,options,...result};requests.push(request);options.signal?.addEventListener('abort',()=>result.reject(new DOMException('Aborted','AbortError')));return result.promise;},
    localStorage:{setItem(){}},Store:{set(){}},crypto:{randomUUID:()=> '12345678-1234-4234-8234-123456789abc'}});
  context.window=context;context.SESSION_TOKEN='private-vm-token';context.activeChannel='review';context.channelList=['general','review','peer'];
  context.ws={send:value=>sends.push(JSON.parse(value))};context._setActiveChannel=name=>{context.activeChannel=name;};
  context.switchChannel=name=>{context.activeChannel=name;};context.ChannelLifecycle={openManage:options=>opens.push(plain(options))};
  context.addEventListener=()=>{};context.removeEventListener=()=>{};context.dispatchEvent=()=>{};
  function add(tag,attrs={},parent=body){const element=new Element(tag);Object.assign(element,attrs);parent.appendChild(element);return element;}
  return {context,document,body,add,sends,opens,requests,timers,async tick(ms){const end=clock+ms;while(true){const pending=[...timers].filter(([,t])=>t.at<=end).sort((a,b)=>a[1].at-b[1].at)[0];if(!pending)break;timers.delete(pending[0]);clock=pending[1].at;pending[1].fn();await flush();}clock=end;await flush();}};
}
function extractFunction(file,name){const source=read(file);let start=source.indexOf('function '+name+'(');assert.ok(start>=0,'Actual function '+name+' must exist');if(source.slice(start-6,start)==='async ')start-=6;const next=source.slice(start+1).search(/\n(?:async )?function /);return next<0?source.slice(start):source.slice(start,start+1+next);}
function block(file,begin,end){const source=read(file);const start=source.indexOf(begin),finish=source.indexOf(end,start+begin.length);assert.ok(start>=0&&finish>start,'Actual markers '+begin);return source.slice(start+begin.length,finish);}
const counts=()=>({messages:3,todos:1,jobs:2,schedules:1,sessions:1,summaries:1,uploads:4});
const catalogCounts=()=>({...counts(),queue:0});
function catalog(revision=1,changes={}){return {revision,channels:[{name:'general',state:'active',counts:catalogCounts(),overdue_schedules:0,errors:{}},{name:'review',state:'active',counts:catalogCounts(),overdue_schedules:1,errors:{}},{name:'peer',state:'active',counts:catalogCounts(),overdue_schedules:0,errors:{}},{name:'archive',state:'archived',counts:catalogCounts(),overdue_schedules:1,errors:{}},{name:'gone',state:'retired',counts:catalogCounts(),overdue_schedules:0,errors:{}}],intent:null,...changes};}
function jobsHeld(revision=3){return catalog(revision,{channels:catalog().channels.map(row=>row.name==='review'?{...row,counts:{...row.counts,jobs:null},errors:{jobs:'Cannot confirm contents; repair storage first.'}}:row)});}
function preview(op='delete',extra={}){return {op,channel:'review',new_name:op==='rename'?'renamed':null,revision:1,state:'active',counts:counts(),blockers:[],queued_dispatch_ids:[],overdue_schedules:1,preview_token:'a'.repeat(64),...extra};}
function retained(extra={}){return {channel:'archive',state:'archived',summary:null,jobs:[],sessions:[],schedules:[],uploads:[],counts:{jobs:0,sessions:0,schedules:0,uploads:0},truncated:{jobs:false,sessions:false,schedules:false,uploads:false},errors:{},...extra};}
function answer(request,value,status=200){request.settled=true;request.resolve({ok:status>=200&&status<300,status,json:async()=>plain(value),text:async()=>JSON.stringify(value)});}
function moduleEnv(){const env=environment();vm.runInContext(read('static/channel-lifecycle.js'),env.context);env.api=env.context.ChannelLifecycle;return env;}
function pending(env,part){return env.requests.filter(r=>!r.settled&&String(r.url).includes(part));}
async function refreshed(env,value=catalog()){const result=env.api.refresh();await flush();const req=pending(env,'/api/channels').find(r=>!String(r.url).includes('/retained'));assert.ok(req,'refresh must GET catalog');answer(req,value);return await result;}
async function settleReads(env,value=catalog(),packet=retained()){for(let n=0;n<8;n++){await flush();const reads=env.requests.filter(r=>!r.settled&&(!r.options.method||r.options.method==='GET'));if(!reads.length)break;for(const req of reads)answer(req,String(req.url).includes('/retained')?packet:value);}await flush();}
async function manage(env,op='delete',channel='review'){const dialog=env.api.openManage({channel,op});assert.equal(dialog.tagName,'DIALOG');await settleReads(env);return dialog;}
function control(env,id){const element=env.document.getElementById(id);assert.ok(element,'control '+id);return element;}
function input(element,value){element.value=value;element.dispatchEvent({type:'input'});element.dispatchEvent({type:'change'});}
async function getPreview(env,data=preview()){control(env,'channel-manager-preview').click();await flush();const requests=pending(env,'/api/channels/preview');assert.equal(requests.length,1);answer(requests[0],data);await flush();return requests[0];}

test('shared facade exists and exposes authority/management methods without evaluation effects',async()=>{
  assert.ok(fs.existsSync(path.join(root,'static/channel-lifecycle.js')),'shared channel-lifecycle module missing');
  const env=environment();vm.runInContext(read('static/channel-lifecycle.js'),env.context);
  for(const name of ['refresh','state','canWrite','guardWrite','openManage','handleEvent','ownerAvailable'])assert.equal(typeof env.context.ChannelLifecycle[name],'function',name);
  assert.equal(env.requests.length,0);assert.equal(env.sends.length,0);
  await catalogAuthority();
});

test('both actual top/sidebar rename and delete entrypoints delegate without optimistic actions',()=>{
  const results=[];
  for(const name of ['showChannelRenameDialog','_showSidebarRenameDialog','deleteChannel','_sidebarConfirmDelete']){
    const env=environment();const tabs=env.add('div',{id:'channel-tabs'});const list=env.add('div',{id:'channel-sidebar-list'});
    const parent=name.includes('Sidebar')||name.includes('sidebar')?list:tabs;
    const row=env.add('button',{className:parent===list?'channel-sidebar-row':'channel-tab',dataset:{channel:'review'}},parent);
    const label=env.add('span',{className:parent===list?'channel-sidebar-row-label':'channel-tab-label',textContent:'# review'},row);
    env.add('span',{className:parent===list?'channel-sidebar-row-actions':'channel-tab-actions'},row);
    vm.runInContext(extractFunction('static/channels.js',name),env.context);
    env.context[name]('review',row,label);
    // Exercise the incumbent one-click confirmation path if it is still present.
    const input=env.body.querySelector('input');if(input)input.value='renamed';
    const confirm=descendants(env.body).find(x=>x.tagName==='BUTTON'&&['Rename','Confirm delete'].includes(x.title));
    confirm?.click();
    results.push({name,sends:env.sends,selection:env.context.activeChannel,opens:env.opens});
  }
  assert.deepEqual(results,results.map(({name})=>({name,sends:[],selection:'review',opens:[{channel:'review',op:name.toLowerCase().includes('delete')?'delete':'rename'}]})));
});

async function catalogAuthority(){
  const env=moduleEnv();assert.equal(env.api.state('review'),'unavailable');assert.equal(env.api.canWrite('review'),false);
  const value=await refreshed(env);assert.equal(env.api.state('review'),'active');assert.equal(env.api.canWrite('review'),true);
  value.channels.find(row=>row.name==='review').state='retired';assert.equal(env.api.canWrite('review'),true);
  assert.equal(env.api.state('missing'),'unregistered');assert.equal(env.api.canWrite('archive'),false);assert.equal(env.api.canWrite('gone'),false);
  const held=catalog(2,{intent:{op:'rename',old:'review',new:'next',request_id:'b'.repeat(32),completed_steps:[]}});
  await refreshed(env,held);assert.equal(env.api.state('review'),'held');assert.equal(env.api.state('next'),'held');assert.equal(env.api.canWrite('next'),false);assert.equal(env.api.canWrite('peer'),true);
  assert.equal(env.api.guardWrite('review'),false);assert.equal(env.api.guardWrite('peer'),true);assert.equal(env.sends.length,0);
  await refreshed(env,jobsHeld());assert.equal(env.api.state('review'),'active');assert.equal(env.api.canWrite('review'),true);assert.equal(env.api.ownerAvailable('jobs','review'),false);assert.equal(env.api.ownerAvailable('messages','review'),true);assert.equal(env.api.ownerAvailable('jobs','peer'),true);assert.equal(env.api.canWrite('peer'),true);assert.equal(env.api.ownerAvailable('jobs','missing'),false);
  const unregistered=catalog(4);unregistered.channels.push({name:'data-only',state:'unregistered',counts:null,overdue_schedules:0,errors:{}});await refreshed(env,unregistered);assert.equal(env.api.ownerAvailable('jobs','data-only'),false);
  const scheduleHeld=catalog(5,{channels:catalog().channels.map(row=>row.name==='review'?{...row,counts:{...row.counts,schedules:null},overdue_schedules:null,errors:{schedules:'Cannot confirm contents; repair storage first.'}}:row)});await refreshed(env,scheduleHeld);assert.equal(env.api.canWrite('review'),true);assert.equal(env.api.ownerAvailable('schedules','review'),false);assert.equal(env.api.ownerAvailable('schedules','peer'),true);
}

test('strict catalog failures stale revisions and eight-second abort stay fail-closed',async()=>{
  const env=moduleEnv();await refreshed(env,catalog(5));await refreshed(env,catalog(4,{channels:catalog().channels.map(row=>({...row,state:row.name==='review'?'retired':row.state}))}));assert.equal(env.api.canWrite('review'),true);
  for(const value of [{revision:true,channels:[],intent:null},{revision:6,channels:[{name:'review',state:'invented'}],intent:null},catalog(6,{channels:catalog().channels.map(row=>row.name==='review'?{...row,counts:{...row.counts,jobs:null}}:row)})]){
    const result=env.api.refresh().catch(error=>error);await flush();answer(pending(env,'/api/channels').at(-1),value);await result;assert.equal(env.api.canWrite('review'),false);
  }
  const result=env.api.refresh().catch(error=>error);await flush();const request=pending(env,'/api/channels').at(-1);await env.tick(8000);const error=await result;assert.ok(error instanceof Error||error?.message);assert.equal(request.options.signal.aborted,true);assert.equal(env.api.state('review'),'unavailable');
});

test('fresh typed preview gates apply with synchronous single-flight and exact request intent',async()=>{
  const env=moduleEnv();await manage(env);const apply=()=>control(env,'channel-manager-apply');assert.equal(apply().disabled,true);
  input(control(env,'channel-manager-confirm'),'review');assert.equal(apply().disabled,true);
  const call=await getPreview(env);assert.deepEqual(JSON.parse(call.options.body),{op:'delete',channel:'review'});
  input(control(env,'channel-manager-confirm'),'Review');assert.equal(apply().disabled,true);input(control(env,'channel-manager-confirm'),'review');assert.equal(apply().disabled,false);
  apply().click();apply().click();await flush();const requests=pending(env,'/api/channels/apply');assert.equal(requests.length,1);
  const body=JSON.parse(requests[0].options.body);assert.equal(body.confirmation,'review');assert.equal(body.preview_token,'a'.repeat(64));assert.match(body.request_id,/^[0-9a-f]{32}$/);assert.equal(body.op,'delete');
  assert.equal(env.context.activeChannel,'review');assert.equal(env.sends.length,0);answer(requests[0],{ok:true,op:'delete',channel:'review',state:'retired'});await settleReads(env,catalog(2,{channels:catalog().channels.map(row=>({...row,state:row.name==='review'?'retired':row.state}))}));assert.equal(env.context.activeChannel,'review');assert.equal(env.api.canWrite('review'),false);
  const partial=moduleEnv();await manage(partial);await getPreview(partial);input(control(partial,'channel-manager-confirm'),'review');assert.equal(control(partial,'channel-manager-apply').disabled,false);await refreshed(partial,jobsHeld());assert.equal(partial.api.canWrite('review'),true);assert.equal(partial.api.ownerAvailable('jobs','review'),false);assert.equal(control(partial,'channel-manager-apply').disabled,true);assert.match(partial.body.textContent,/Cannot confirm contents; repair storage first/i);assert.equal(partial.requests.filter(r=>String(r.url).includes('/apply')).length,0);
});

test('rename destination edits invalidate preview and conflict retains exact drafts without resend',async()=>{
  const env=moduleEnv();await manage(env,'rename');input(control(env,'channel-manager-name'),'renamed');await getPreview(env,preview('rename'));input(control(env,'channel-manager-confirm'),'review');assert.equal(control(env,'channel-manager-apply').disabled,false);
  input(control(env,'channel-manager-name'),'different');assert.equal(control(env,'channel-manager-apply').disabled,true);
  await getPreview(env,preview('rename',{new_name:'different'}));input(control(env,'channel-manager-confirm'),'review');control(env,'channel-manager-apply').click();await flush();const req=pending(env,'/apply')[0];answer(req,{error:'PRIVATE server exception'},409);await settleReads(env,catalog(2));
  assert.equal(control(env,'channel-manager-name').value,'different');assert.equal(control(env,'channel-manager-confirm').value,'review');assert.equal(env.requests.filter(r=>String(r.url).includes('/apply')).length,1);assert.doesNotMatch(env.body.textContent,/PRIVATE server exception/);assert.equal(env.context.activeChannel,'review');
});

test('storage and network management failures are generic retain draft and never auto-repeat',async()=>{
  for(const kind of ['503','network']){
    const env=moduleEnv();await manage(env,'rename');input(control(env,'channel-manager-name'),'renamed');await getPreview(env,preview('rename'));input(control(env,'channel-manager-confirm'),'review');control(env,'channel-manager-apply').click();await flush();const request=pending(env,'/apply')[0];
    if(kind==='503')answer(request,{error:'C:\\PRIVATE\\secret-token'},503);else{request.settled=true;request.reject(new TypeError('C:\\PRIVATE\\secret-token'));}
    await flush();assert.equal(control(env,'channel-manager-name').value,'renamed');assert.equal(control(env,'channel-manager-confirm').value,'review');assert.doesNotMatch(env.body.textContent,/PRIVATE|secret-token/);assert.ok(control(env,'channel-manager-status').textContent.trim());assert.equal(env.requests.filter(r=>String(r.url).includes('/apply')).length,1);assert.equal(env.context.activeChannel,'review');
  }
});

test('queued cancellation is separate from deletion and pending operation offers explicit repair',async()=>{
  const env=moduleEnv();await manage(env,'cancel_queued');await getPreview(env,preview('cancel_queued',{queued_dispatch_ids:['d'.repeat(32)]}));input(control(env,'channel-manager-confirm'),'review');control(env,'channel-manager-apply').click();await flush();const request=pending(env,'/apply')[0];assert.equal(JSON.parse(request.options.body).op,'cancel_queued');answer(request,{ok:true,op:'cancel_queued',channel:'review'});await settleReads(env,catalog(2));assert.equal(env.requests.filter(r=>r.options.method==='POST').length,2);
  const pendingCatalog=catalog(3,{intent:{op:'delete',old:'review',new:null,request_id:'e'.repeat(32),completed_steps:['todos']}});await refreshed(env,pendingCatalog);env.api.openManage({channel:'review'});await settleReads(env,pendingCatalog);
  assert.equal(env.api.state('review'),'held');assert.equal(env.requests.filter(r=>String(r.url).includes('/retry')).length,0);const repair=descendants(env.body).find(el=>el.tagName==='BUTTON'&&/retry|repair/i.test(el.textContent));assert.ok(repair,'explicit pending repair action');
});

test('retained groups render literal source safe upload links held errors and truncation counts',async()=>{
  const env=moduleEnv();const unsafe='<img src=x onerror=PRIVATE_LITERAL>';const packet=retained({summary:{text:unsafe,uid:'summary',author:'operator',updated_at:1,message_id:0},jobs:null,sessions:[{id:4,run_id:'f'.repeat(32),state:'stopped',channel:'archive',completion_protocol:1}],uploads:[{channel:'archive',message_id:0,message_uid:'source',timestamp:1,attachments:[{name:unsafe,url:'https://evil.invalid/x'},{name:'safe.txt',url:'/uploads/abc.txt'}],safe_links:[{name:'safe.txt',url:'/uploads/abc.txt'}]}],counts:{jobs:null,sessions:150,schedules:0,uploads:1},truncated:{jobs:null,sessions:true,schedules:false,uploads:false},errors:{jobs:'Saved records are held; repair storage and reload.'}});
  env.api.openManage({channel:'archive',op:'view'});await settleReads(env,catalog(),packet);assert.ok(env.body.textContent.includes(unsafe));assert.match(env.body.textContent,/150/);assert.match(env.body.textContent,/held|repair/i);assert.equal(env.api.canWrite('archive'),false);
  for(const element of descendants(env.body))assert.ok(!String(element.innerHTML).includes(unsafe),'source must use textContent/pre');const links=env.body.querySelectorAll('a');assert.ok(links.some(link=>(link.href||link.getAttribute('href'))==='/uploads/abc.txt'));assert.ok(links.every(link=>!String(link.href||link.getAttribute('href')).startsWith('https://evil.invalid')));
});

test('channel events refetch authority before cache rename and never select general on deletion/settings',async()=>{
  const env=moduleEnv();const renames=[];env.context.applyChannelRename=event=>renames.push(plain(event));await refreshed(env);const event={type:'channel_renamed',old_name:'review',new_name:'renamed'};const handled=env.api.handleEvent(event);await flush();assert.equal(env.api.state('review'),'active');assert.equal(renames.length,0);assert.equal(env.context.activeChannel,'review');
  await settleReads(env,catalog(2,{channels:catalog().channels.filter(row=>row.name!=='review').concat({name:'renamed',state:'active',counts:catalogCounts(),overdue_schedules:0,errors:{}})}));await handled;assert.equal(renames.length,1);
  const helper=block('static/chat.js','// CHANNEL LIFECYCLE CLIENT HELPERS BEGIN','// CHANNEL LIFECYCLE CLIENT HELPERS END');
  const stateEnv=environment();stateEnv.context.ChannelLifecycle={state:name=>name==='review'?'archived':'active',renderPolicy(){}};stateEnv.context.todos={};stateEnv.context.deleteSelected=new Set();stateEnv.context.renderTodosPanel=()=>{};stateEnv.context.channelUnread={review:2};stateEnv.context._channelMentions={review:['codex']};stateEnv.context.lastMessageDates={review:'today'};stateEnv.context.pendingChannelSwitch=null;stateEnv.context.filterMessagesByChannel=()=>{};stateEnv.context.renderChannelTabs=()=>{};stateEnv.context.updateChannelWriteState=()=>{};stateEnv.add('div',{id:'messages'});vm.runInContext(helper,stateEnv.context);stateEnv.context.applyChannelSettings(['general','peer']);assert.equal(stateEnv.context.activeChannel,'review');stateEnv.context.invalidateDeletedChannel('review');assert.equal(stateEnv.context.activeChannel,'review');
});

test('actual composer and session launcher refuse inactive context preserving drafts and no network',async()=>{
  const env=environment();const inputEl=env.add('textarea',{id:'input',value:'Exact retained draft'});env.context.ChannelLifecycle={canWrite:()=>false,guardWrite:()=>false};env.context.channelSendPending=null;env.context.channelRecipientPreview={prepare:async()=>{throw Error('inactive must precede preview');},state:'ready'};env.context.selectedAgents=new Set();env.context.username='operator';env.context.getSelectedAgents=()=>[];
  vm.runInContext(block('static/chat.js','// --- Recipient composer ---','// --- Image paste/drop ---'),env.context);await env.context.sendMessage();assert.equal(inputEl.value,'Exact retained draft');assert.equal(env.sends.length,0);assert.equal(env.requests.length,0);
  const modal=env.add('div',{id:'session-launcher-modal'});const editor=env.add('div',{className:'session-source-editor'},modal);modal._documentInput={state:'ready',requestFields:()=>({input_text:'Frozen draft'}),setSubmitting(){},dispose(){}};env.context.selectedRecoveryPolicy=()=>({ack_timeout:30,response_timeout:900});vm.runInContext(block('static/sessions.js','// DOCUMENT LAUNCHER HELPERS BEGIN','// DOCUMENT LAUNCHER HELPERS END'),env.context);await env.context.submitSessionStart({template_id:'review'});assert.equal(env.requests.length,0);assert.equal(modal.isConnected,true);assert.ok(editor);
});

test('actual job ordering excludes inactive IDs and rejects inactive drag source or target',async()=>{
  const env=environment();env.context.jobLoadError='';env.context.jobsData=[{id:1,status:'open',channel:'peer',sort_order:1},{id:2,status:'open',channel:'archive',sort_order:9},{id:3,status:'open',channel:'peer',sort_order:3}];env.context.ChannelLifecycle={canWrite:name=>name==='peer',ownerAvailable:()=>true};env.context._compareJobsForList=(a,b)=>b.sort_order-a.sort_order;for(const name of ['jobCanWrite','_orderedIdsForJobGroup','reorderJobWithinGroup'])vm.runInContext(extractFunction('static/jobs.js',name),env.context);
  assert.deepEqual(plain(env.context._orderedIdsForJobGroup('open')),[3,1]);assert.equal(env.context.jobCanWrite(env.context.jobsData[1]),false);await env.context.reorderJobWithinGroup('open',2,1,false);await env.context.reorderJobWithinGroup('open',1,2,false);assert.equal(env.requests.length,0);
  const source=read('static/jobs.js');assert.ok(!source.includes('card.draggable = true;'),'inactive cards need actual channel-dependent draggable state');assert.match(source,/jobCanWrite/);
});

test('script initialization order and scoped responsive styles retain native dialog close paths',()=>{
  const html=read('static/index.html');const moduleIndex=html.indexOf('channel-lifecycle.js');assert.ok(moduleIndex>=0);assert.ok(moduleIndex<html.indexOf('channels.js'));assert.match(html,/channel-lifecycle\.js\?v=\d+/);
  assert.match(extractFunction('static/channels.js','_channelsInit'),/ChannelLifecycle.*refresh|refresh.*ChannelLifecycle/);assert.ok(html.includes('Manage channels'));assert.ok(html.includes('channel-manage-btn')&&html.includes('channel-sidebar-manage'));
  const module=read('static/channel-lifecycle.js');assert.match(module,/(?:createElement|node)\(['"]dialog['"]/);assert.match(module,/cancel/);assert.match(module,/focus/);
  const css=read('static/channel-lifecycle.css');const scoped=css.slice(css.indexOf('.channel-manager'));assert.ok(scoped.length);assert.match(scoped,/font-size:\s*14px/);assert.match(scoped,/min-height:\s*44px/);assert.match(scoped,/padding:\s*12px/);assert.match(scoped,/390|480|600|640/);
});

(async()=>{let failures=0;for(const {name,run} of tests){try{await run();console.log('PASS '+name);}catch(error){failures++;console.error('FAIL '+name+'\n'+error.stack);}}console.log(JSON.stringify({cases:tests.length,failures,scope:'actual_source_vm_only'}));process.exitCode=failures?1:0;})();
