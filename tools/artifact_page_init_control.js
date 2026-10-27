/* Actual page scripts, one VM. Stub DOM/network only, never browser proof. */
'use strict';
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const ids = new Map(), fetches = [], sockets = [], tasks = [], timers = new Map(), logs = [];
let clock = 0, timerId = 0, activeFile = 'bootstrap', optionsCalls = 0;
function events(object) {
    object.listeners = {};
    object.addEventListener = (kind, fn) => (object.listeners[kind] ||= []).push(fn);
    object.removeEventListener = (kind, fn) => object.listeners[kind] = (object.listeners[kind] || []).filter(f => f !== fn);
    object.dispatched=[];
    object.dispatchEvent = e => {object.dispatched.push(e.type);for (const fn of [...(object.listeners[e.type] || [])]) fn(e);return true;};
    return object;
}
class Element {
    constructor(tag) {
        this.tagName = tag.toUpperCase(); this.children = []; this.attributes = {}; this.dataset = {};
        this._id = ''; this._text = ''; this.className = ''; this.value = ''; this.hidden = false;
        this.style = {setProperty(k,v){this[k]=v},removeProperty(k){delete this[k]}};
        this.scrollTop = 0; this.scrollLeft = 0; this.scrollHeight = 0; this.clientHeight = 100;
        this.checked = false; this.disabled = false; events(this);
        this.classList = {contains:c=>this.className.split(/\s+/).includes(c),
            add:(...cs)=>this.className=[...new Set([...this.className.split(/\s+/).filter(Boolean),...cs])].join(' '),
            remove:(...cs)=>this.className=this.className.split(/\s+/).filter(c=>!cs.includes(c)).join(' '),
            toggle:(c,on)=>{on=on??!this.classList.contains(c);this.classList[on?'add':'remove'](c);return on}};
    }
    set id(v){if(this._id)ids.delete(this._id);this._id=String(v);if(v)ids.set(this._id,this)} get id(){return this._id}
    get childNodes(){return this.children} get childElementCount(){return this.children.length}
    get firstChild(){return this.children[0]||null} get lastChild(){return this.children.at(-1)||null}
    get firstElementChild(){return this.firstChild} get parentNode(){return this.parentElement||null}
    get options(){return this.children} get selectedOptions(){return this.children.filter(n=>n.value===this.value)}
    get isConnected(){return !!this.parentElement||this===document.documentElement}
    get offsetParent(){return this.hidden||this.classList.contains('hidden')?null:this.parentElement}
    get offsetHeight(){return 30} get offsetWidth(){return 100}
    set textContent(v){this._text=String(v??'');this.children=[]} get textContent(){return this._text+this.children.map(c=>c.textContent).join('')}
    get innerText(){return this.textContent} set innerText(v){this.textContent=v}
    set innerHTML(v){this.replaceChildren();parseFragment(String(v),this)} get innerHTML(){return this.textContent}
    appendChild(n){if(n.tagName==='#FRAGMENT'){for(const c of [...n.children])this.appendChild(c);return n}if(n.parentElement)n.remove();this.children.push(n);n.parentElement=this;return n}
    append(...nodes){for(let n of nodes){if(typeof n==='string'){const t=new Element('#text');t.textContent=n;n=t}this.appendChild(n)}}
    prepend(n){this.appendChild(n);this.children.unshift(this.children.pop())}
    replaceChildren(...nodes){for(const c of [...this.children])c.remove();this._text='';this.append(...nodes)}
    remove(){if(this.parentElement)this.parentElement.children=this.parentElement.children.filter(n=>n!==this);this.parentElement=null;if(this.id)ids.delete(this.id)}
    after(n){this.parentElement?.appendChild(n)}
    insertBefore(n,b){if(!b)return this.appendChild(n);this.appendChild(n);this.children.pop();this.children.splice(this.children.indexOf(b),0,n);return n}
    insertAdjacentElement(position,n){if(position==='afterbegin')this.prepend(n);else if(position==='beforeend')this.appendChild(n);else this.parentElement?.appendChild(n);return n}
    setAttribute(k,v){v=String(v);this.attributes[k]=v;if(k==='id')this.id=v;else if(k==='class')this.className=v;else if(k==='value')this.value=v;else if(k.startsWith('data-'))this.dataset[k.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=v;else if(['checked','disabled','hidden'].includes(k))this[k]=true;else this[k]=v}
    getAttribute(k){return k==='id'?this.id:k==='class'?this.className:this.attributes[k]??null}
    removeAttribute(k){delete this.attributes[k];if(['disabled','hidden'].includes(k))this[k]=false}
    hasAttribute(k){return Object.hasOwn(this.attributes,k)}
    contains(n){return n===this||this.children.some(c=>c.contains(n))}
    matches(selector){
        if(selector.includes(','))return selector.split(',').some(s=>this.matches(s.trim()));
        const last=selector.trim().split(/\s+|>/).filter(Boolean).at(-1)||'';
        const tag=last.match(/^[a-z][\w-]*/i);if(tag&&this.tagName!==tag[0].toUpperCase())return false;
        for(const id of last.matchAll(/#([\w-]+)/g))if(this.id!==id[1])return false;
        for(const cl of last.matchAll(/\.([\w-]+)/g))if(!this.classList.contains(cl[1]))return false;
        for(const a of last.matchAll(/\[([\w-]+)(?:=["']?([^\]"']+)["']?)?\]/g))if(!this.hasAttribute(a[1])||(a[2]!==undefined&&this.getAttribute(a[1])!==a[2]))return false;
        return !!last;
    }
    querySelectorAll(s){const all=[];for(const c of this.children){if(c.matches(s))all.push(c);all.push(...c.querySelectorAll(s))}return all}
    querySelector(s){return this.querySelectorAll(s)[0]||null}
    getElementsByClassName(s){return this.querySelectorAll('.'+s)} getElementsByTagName(s){return this.querySelectorAll(s)}
    closest(s){for(let n=this;n;n=n.parentElement)if(n.matches(s))return n;return null}
    focus(){document.activeElement=this} blur(){if(document.activeElement===this)document.activeElement=null}
    click(){const e={type:'click',target:this,preventDefault(){},stopPropagation(){}};this.onclick?.(e);this.dispatchEvent(e)}
    getBoundingClientRect(){return {x:0,y:0,top:0,left:0,right:100,bottom:30,width:100,height:30}}
    scrollIntoView(){} scrollTo(){} select(){} setSelectionRange(){} play(){return Promise.resolve()} pause(){} load(){}
}
function attributes(source,node){for(const a of source.matchAll(/([\w:-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g))node.setAttribute(a[1],a[2]??a[3]??a[4]??'')}
function parseFragment(source,parent){const stack=[parent];for(const token of source.matchAll(/<\/?[\w-]+[^>]*>|[^<]+/g)){const s=token[0];if(s.startsWith('</')){if(stack.length>1)stack.pop();continue}if(s.startsWith('<')){const tag=s.match(/^<([\w-]+)/)[1];const n=new Element(tag);attributes(s.slice(tag.length+1,-1),n);stack.at(-1).appendChild(n);if(!/^(input|img|br|hr|meta|link)$/i.test(tag)&&!s.endsWith('/>'))stack.push(n)}else{const n=new Element('#text');n.textContent=s;stack.at(-1).appendChild(n)}}}
const document=events({hidden:true,visibilityState:'hidden',hasFocus:()=>false,readyState:'loading',activeElement:null,
    createElement:t=>new Element(t),createElementNS:(_,t)=>new Element(t),
    createTextNode:t=>{const n=new Element('#text');n.textContent=t;return n},createDocumentFragment:()=>new Element('#fragment'),
    getElementById:id=>ids.get(id)||null,querySelector:s=>document.documentElement.querySelector(s),
    querySelectorAll:s=>document.documentElement.querySelectorAll(s),getElementsByClassName:s=>document.documentElement.getElementsByClassName(s),
    getSelection:()=>({removeAllRanges(){}})});
const built=input.nodes.map(row=>{const n=new Element(row.tag);for(const [k,v]of Object.entries(row.attrs))n.setAttribute(k,v??'');return n});
for(let i=0;i<built.length;i++){const p=input.nodes[i].parent;if(p!==null)built[p].appendChild(built[i])}
document.documentElement=built.find(n=>n.tagName==='HTML');document.body=built.find(n=>n.tagName==='BODY');document.head=built.find(n=>n.tagName==='HEAD');
function storage(){const map=new Map();return {getItem:k=>map.get(k)??null,setItem:(k,v)=>map.set(k,String(v)),removeItem:k=>map.delete(k),clear:()=>map.clear(),get length(){return map.size},key:i=>[...map.keys()][i]??null}}
class Socket{constructor(url){this.url=url;this.readyState=1;sockets.push(this)}send(){}close(){this.readyState=3}addEventListener(){} }Socket.OPEN=1;
class Channel{constructor(){this.port1={onmessage:null};this.port2={postMessage:v=>tasks.push(()=>this.port1.onmessage?.({data:v}))}}}
const counts=['messages','todos','jobs','schedules','sessions','summaries','uploads','queue','artifacts','artifact_versions','artifact_requests','artifact_source_bytes'];
const catalog={revision:1,intent:null,channels:[{name:'general',state:'active',counts:Object.fromEntries(counts.map(k=>[k,0])),errors:{},overdue_schedules:0}]};
const context=vm.createContext(events({document,location:{protocol:'http:',host:'127.0.0.1:1',hostname:'127.0.0.1',origin:'http://127.0.0.1:1',href:'http://127.0.0.1:1/',reload(){}},
    navigator:{platform:'Win32',userAgent:'node-vm-control',mediaDevices:{}},localStorage:storage(),sessionStorage:storage(),
    console:Object.fromEntries(['log','warn','error','info','debug'].map(k=>[k,(...args)=>logs.push({level:k,text:args.map(String).join(' ')})])),
    WebSocket:Socket,MessageChannel:Channel,Element,HTMLElement:Element,HTMLInputElement:Element,Node:Element,
    AbortController,Headers,Blob,URL,TextEncoder,TextDecoder,Event,CustomEvent,crypto:require('crypto').webcrypto,
    innerWidth:1280,innerHeight:850,devicePixelRatio:1,performance:{now:()=>clock},
    setTimeout:(fn,ms)=>{timers.set(++timerId,{fn,ms});return timerId},clearTimeout:id=>timers.delete(id),
    setInterval:()=>++timerId,clearInterval(){},requestAnimationFrame:fn=>{tasks.push(fn);return ++timerId},cancelAnimationFrame(){},
    matchMedia:()=>({matches:false,addEventListener(){},removeEventListener(){},addListener(){}}),
    getComputedStyle:()=>({getPropertyValue:()=>'',height:'30px',fontSize:'14px'}),
    MutationObserver:class{observe(){}disconnect(){}},ResizeObserver:class{observe(){}disconnect(){}},IntersectionObserver:class{observe(){}unobserve(){}disconnect(){}},
    fetch:async url=>{url=String(url);fetches.push(url);let value={};if(url==='/api/channels')value=catalog;
        else if(url==='/api/sessions/active-all')value=[];else if(url.startsWith('/api/sessions/active?'))value=null;else if(url==='/api/sessions/templates')value=[];
        else if(url==='/api/session-capacity')value={limits_text:'Fixture limits'};
        else if(/roles|rules|jobs|hats|schedules/.test(url))value=[];
        return {ok:true,status:200,json:async()=>structuredClone(value),text:async()=>JSON.stringify(value),headers:new Headers({'Content-Type':'application/json'})}},
    alert:()=>{throw Error('Unexpected alert in init control')},confirm:()=>false,prompt:()=>null,
    Audio:class{play(){return Promise.resolve()}},AudioContext:class{},CSS:{escape:s=>s},Option:class extends Element{constructor(t,v){super('option');this.textContent=t;this.value=v}}
}));
context.window=context;context.self=context;
const failures=[];
process.on('unhandledRejection',e=>failures.push({file:activeFile,error:String(e.stack||e)}));
async function flush(){for(let i=0;i<12;i++){while(tasks.length){const fn=tasks.shift();try{fn()}catch(e){failures.push({file:activeFile,error:e.stack})}}await new Promise(r=>setImmediate(r))}}
(async()=>{
    let observerSyntax=false,beforeProduct=false;
    for(const script of input.scripts){
        activeFile=script.name;
        if(script.name.startsWith('static/')&&!beforeProduct){
            assert.equal(typeof context.__artifactFixtureEvidence,'function','visibility must be installed before first product script');
            const visibility=context.__artifactFixtureEvidence().visibility;
            assert.equal(visibility.native_hidden,true,'native hidden must be recorded');
            assert.equal(visibility.native_visibilityState,'hidden','native visibility state must be recorded');
            assert.equal(visibility.native_hasFocus,false,'native focus must be recorded');
            assert.equal(visibility.visibility_simulated,!!input.simulateVisibility);
            assert.equal(document.hidden,!input.simulateVisibility,'visibility flag must control document.hidden');
            assert.equal(document.visibilityState,input.simulateVisibility?'visible':'hidden','visibility flag must control document.visibilityState');
            assert.equal(typeof Object.getOwnPropertyDescriptor(document,'hidden').get,input.simulateVisibility?'function':'undefined','OFF must leave document instance untouched');
            beforeProduct=true;
        }
        const compiled=new vm.Script(script.code,{filename:script.name});
        if(script.observer)observerSyntax=true;
        compiled.runInContext(context,{timeout:1000});
        if(context.marked?.setOptions&&!context.marked.setOptions._counted){const original=context.marked.setOptions;context.marked.setOptions=(...args)=>{optionsCalls++;return original(...args)};context.marked.setOptions._counted=true}
    }
    document.readyState='complete';activeFile='DOMContentLoaded / static/chat.js';
    document.dispatchEvent({type:'DOMContentLoaded',target:document});await flush();
    assert.equal(document.getElementById('__not_an_index_id__'),null,'DOM ids must not auto-create');
    assert.equal(context.localStorage.getItem('help_seen'),'1','fixture must suppress first-visit help overlay');
    assert(!document.getElementById('help-guide'),'help overlay must be absent');
    assert.equal(sockets.length,1,'real init must construct one WebSocket');
    assert.equal(sockets[0].url,'ws://127.0.0.1:1/ws?token=T');sockets[0].onopen?.();
    for(const event of [{type:'settings',data:{username:'fixture',channels:['general']}},{type:'agents',data:{}},{type:'history',messages:[]},{type:'history_complete'}]){
        activeFile='WebSocket '+event.type;sockets[0].onmessage({data:JSON.stringify(event)});await flush();
    }
    assert(optionsCalls>0,'marked.setOptions must execute');
    for(const path of ['/api/channels','/api/sessions/active-all','/api/session-capacity'])assert(fetches.includes(path),'missing init fetch '+path);
    assert(context.ChannelLifecycle.canWrite('general'),'mock catalog rejected by real validator');
    assert(document.getElementById('channel-tabs').childElementCount>0,'channel tabs not initialized');
    assert(document.getElementById('loading-indicator').classList.contains('hidden'),'history loader not hidden');
    assert.equal(typeof document.getElementById('artifact-documents-open').onclick,'function','Documents not initialized');
    assert(observerSyntax,'observer not syntax-compiled');assert.deepEqual(failures,[],'script/async init errors');
    assert(!document.dispatched.includes('visibilitychange'),'observer must not dispatch synthetic visibility events');
    assert.deepEqual(logs.filter(row=>row.level==='error'),[],'caught init errors');
    process.stdout.write(JSON.stringify({pass:true,scripts:input.scripts.map(s=>s.name),optionsCalls,ws:sockets[0].url,fetches,loadingHidden:true,channelTabs:document.getElementById('channel-tabs').childElementCount,catalogAccepted:true,documentsClick:true,observerSyntax,helpSeed:true,visibility:context.__artifactFixtureEvidence().visibility,visibilityBeforeProduct:beforeProduct,uncaughtErrors:failures.length,errorLogs:logs.filter(row=>row.level==='error').length,claims:'init globals/throws only; no layout/CSP/focus/browser proof'})+'\n');
})().catch(e=>{process.stdout.write(JSON.stringify({pass:false,file:activeFile,error:e.stack,failures,logs,fetches})+'\n');process.exitCode=1});
