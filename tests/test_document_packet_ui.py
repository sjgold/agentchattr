"""Ticket23 actual document-input JS reds; tiny DOM, no browser/provider."""
from pathlib import Path
import json
import shutil
import subprocess
import unittest
from document_inputs import preview_document
from tests.test_document_packets import packet_fixture
ROOT=Path(__file__).resolve().parents[1]
BOOT=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Element {
 constructor(tag){this.tagName=tag.toLowerCase();this.children=[];this.listeners={};this.value='';this.className='';this.isConnected=true;this.disabled=false;this.hidden=false;this.textContent='';this.classList={add:(n)=>{this.className+=' '+n},remove:()=>{}}}
 set innerHTML(v){throw Error('Untrusted source preview must not write HTML')}
 append(...nodes){for(const n of nodes){this.children.push(n);n.parentElement=this}}
 insertBefore(node,before){const at=this.children.indexOf(before);this.children.splice(at<0?0:at,0,node);node.parentElement=this}
 replaceChildren(...nodes){this.children=[];this.append(...nodes)}
 setAttribute(k,v){this[k]=v}
 querySelectorAll(selector){const result=[];for(const child of this.children){if(selector.startsWith('.')?child.className.split(' ').includes(selector.slice(1)):child.tagName===selector)result.push(child);result.push(...child.querySelectorAll(selector))}return result}
 querySelector(s){return this.querySelectorAll(s)[0]||null}
 addEventListener(name,fn){(this.listeners[name]??=[]).push(fn)} removeEventListener(){}
 dispatchEvent(){return true} focus(){} remove(){if(this.parentElement)this.parentElement.children=this.parentElement.children.filter(x=>x!==this)}
 async click(){await this.onclick?.({preventDefault(){}});for(const fn of this.listeners.click||[])await fn({preventDefault(){}})}
}
const calls=[],timers=new Map();let tid=0;
const editor=new Element('section'),label=new Element('label'),input=new Element('textarea');editor.append(label,input);
const context={window:{SESSION_TOKEN:'FAKE_TOKEN'},document:{createElement:t=>new Element(t),createTextNode:t=>{const n=new Element('#text');n.textContent=t;return n}},TextEncoder,AbortController,CustomEvent:class {},console,
 setTimeout:fn=>{timers.set(++tid,fn);return tid},clearTimeout:id=>timers.delete(id)};
context.fetch=async(url,options)=>{calls.push({url,options});if(url.startsWith('/api/documents/preview?')){const name=new URL(url,'http://127.0.0.1').searchParams.get('filename');return {ok:true,status:200,json:async()=>members.find(row=>row.name===name)}}
 if(url==='/api/documents/packet-preview')return {ok:true,status:200,json:async()=>expectedPacket};throw Error('Unexpected preview URL')};
vm.createContext(context);vm.runInContext(fs.readFileSync(process.argv[2]+'/static/document-inputs.js','utf8'),context);
const facade=context.window.DocumentInput.attach(editor);const picker=editor.querySelector('input');
const selected=async()=>{picker.files=members.map(row=>({name:row.name,size:row.byte_length}));await picker.listeners.change[0]()};
const texts=node=>node.textContent+' '+node.children.map(texts).join(' ');
'''


class DocumentPacketUITests(unittest.TestCase):
    def run_js(self,body,files=None):
        files=files or [preview_document('a.py',b'a\r\n'),preview_document('b.py',b'b')]
        packet=packet_fixture(files)
        script='const members='+json.dumps(files,ensure_ascii=True)+';const expectedPacket='+json.dumps(packet,ensure_ascii=True)+';\n'+BOOT+'\n(async()=>{'+body+'})().catch(e=>{console.error(e);process.exitCode=1});'
        result=subprocess.run([shutil.which('node'),'-',str(ROOT)],input=script,capture_output=True,text=True,encoding='utf-8',timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_picker_allows_multiple_files(self):
        self.run_js('assert.strictEqual(picker.multiple,true);')

    def test_actual_two_file_preview_submits_frozen_packet_and_lists_ids(self):
        self.run_js(r'''
await selected();assert.strictEqual(facade.state,'file');
assert.deepStrictEqual(JSON.parse(JSON.stringify(facade.requestFields())),{source_file:expectedPacket});
assert.strictEqual(calls.filter(x=>x.url.startsWith('/api/documents/preview?')).length,2);
const assembled=calls.find(x=>x.url==='/api/documents/packet-preview');assert(assembled);
assert.strictEqual(assembled.options.headers['X-Session-Token'],'FAKE_TOKEN');
assert(!assembled.url.includes('FAKE_TOKEN'));
const shown=texts(editor);for(const part of ['f1','f2','a.py','b.py'])assert(shown.includes(part),part);
assert.strictEqual(timers.size,0);
''')

    def test_untrusted_names_are_literal_and_no_file_body_is_persisted(self):
        self.run_js(r'''
await selected();assert.strictEqual(facade.state,'file');
assert(texts(editor).includes('<img src=x onerror=alert(1)>.py'));
const value=facade.requestFields();value.source_file.files[0].name='changed';
assert.strictEqual(facade.requestFields().source_file.files[0].name,'<img src=x onerror=alert(1)>.py');
facade.dispose();assert.strictEqual(timers.size,0);assert.throws(()=>facade.requestFields());
''',[preview_document('<img src=x onerror=alert(1)>.py',b'literal'),preview_document('b.py',b'b')])

    def test_remove_rebuilds_remaining_snapshot(self):
        self.run_js(r"""
await selected();assert.strictEqual(facade.state,'file');
const remove=editor.querySelectorAll('button').find(b=>/^Remove/.test(b.textContent));assert(remove,'File list needs explicit removal');
await remove.click();
const current=facade.requestFields().source_file;
const names=current.kind==='file'?[current.name]:current.files.map(row=>row.name);
assert.deepStrictEqual(JSON.parse(JSON.stringify(names)),['b.py']);
""")

    def test_bad_packet_response_cannot_enable_start(self):
        self.run_js(r"""
const normal=context.fetch;
context.fetch=async(url,options)=>url==='/api/documents/packet-preview'?{ok:true,json:async()=>({...expectedPacket,byte_length:0})}:normal(url,options);
await selected();
assert(calls.some(x=>x.url.startsWith('/api/documents/preview?')),'Must reach per-file preview');
assert.strictEqual(facade.state,'error');assert.throws(()=>facade.requestFields());
""")

    def test_aggregate_refuses_before_any_file_read(self):
        self.run_js(r"""
picker.files=[{name:'a.py',size:262144},{name:'b.py',size:262145}];
await picker.listeners.change[0]();
assert.strictEqual(facade.state,'error');assert.strictEqual(calls.length,0);
assert(/aggregate|combined|total/i.test(texts(editor)),'Explain the combined size refusal');
""")

    def test_dispose_during_preview_aborts_and_late_result_cannot_restore(self):
        self.run_js(r"""
let release,signal;context.fetch=(url,options)=>{signal=options.signal;return new Promise(r=>release=r)};
picker.files=members.map(row=>({name:row.name,size:row.byte_length}));
const pending=picker.listeners.change[0]();
assert.strictEqual(facade.state,'reading');assert.strictEqual(timers.size,1);
facade.dispose();assert.strictEqual(timers.size,0);assert(signal.aborted);
release({ok:true,json:async()=>members[0]});await pending;
assert.throws(()=>facade.requestFields());
""")

    def test_new_selection_wins_over_late_old_file_response(self):
        self.run_js(r"""
const normal=context.fetch;let release,first=true;
context.fetch=(url,options)=>{if(first){first=false;return new Promise(r=>release=r)}return normal(url,options)};
picker.files=members.map(row=>({name:row.name,size:row.byte_length}));const old=picker.listeners.change[0]();
picker.files=[{name:members[1].name,size:members[1].byte_length}];await picker.listeners.change[0]();
assert.strictEqual(facade.requestFields().source_file.name,'b.py');
release({ok:true,json:async()=>members[0]});await old;
assert.strictEqual(facade.requestFields().source_file.name,'b.py');assert.strictEqual(timers.size,0);
""")

    def test_timed_out_packet_response_cannot_enable_start_later(self):
        self.run_js(r"""
const normal=context.fetch;let release;
context.fetch=(url,options)=>url==='/api/documents/packet-preview'?new Promise(r=>release=r):normal(url,options);
const pending=selected();for(let i=0;i<15&&!release;i++)await Promise.resolve();assert(release);
const [id,fire]=[...timers][0];timers.delete(id);fire();
assert.strictEqual(facade.state,'error');assert.throws(()=>facade.requestFields());
release({ok:true,json:async()=>expectedPacket});await pending;
assert.strictEqual(facade.state,'error');assert.throws(()=>facade.requestFields());
""")


if __name__=='__main__':unittest.main()
