"""Exercise the real audience renderer while retaining canonical routing IDs."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RecipientDisplayLabelTests(unittest.TestCase):
    def test_preview_announcement_and_receipt_use_labels_without_rewriting_ids(self):
        script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
global.window=global;
class Element {
 constructor(){this.children=[];this.textContent='';this.classList={add(){}};}
 appendChild(e){this.children.push(e);return e;}
 replaceChildren(...items){this.children=items;}
 setAttribute(){} dispatchEvent(){} addEventListener(){}
 querySelector(){return null;}
 insertBefore(e){this.children.push(e);}
 text(){return this.textContent+this.children.map(e=>e.text()).join(' ');}
}
global.document={createElement(){return new Element()}};
vm.runInThisContext(fs.readFileSync(process.argv[1]+'/static/core.js','utf8'));
vm.runInThisContext(fs.readFileSync(process.argv[1]+'/static/recipients.js','utf8'));
const id='cli-1234abcd-live';
window.agentDisplayLabels={[id]:'My Codex <safe>'};
const data={mode:'selected',tokens:[],ignored:[],recipients:[{name:id,identity_id:'identity'}],warnings:[],waiting:[]};
const before=JSON.stringify(data),sent=[];
global.fetch=async(url,opts)=>{sent.push(JSON.parse(opts.body));return {ok:true,json:async()=>data}};
(async()=>{
 const panel=new Element(),preview=RecipientPreview.attach(panel);
 const request={text:'Roll call',channel:'general',selected_recipients:[id]};
 await preview.prepare(request);
 assert(panel.children[0].text().includes('@My Codex <safe>'));
 assert(panel.children[1].text().includes('@My Codex <safe>'));
 assert(!panel.text().includes('@'+id));
 assert.deepStrictEqual(sent[0],request);
 assert.equal(JSON.stringify(data),before);
 const receipt=new Element();
 RecipientPreview.appendReceipt(receipt,{uid:'u',metadata:{recipient_routing:{version:1,message_uid:'u',recipients:data.recipients}}});
 assert(receipt.text().includes('@My Codex <safe>'));
 assert(!receipt.text().includes('@'+id));
 window.agentDisplayLabels[id]='Renamed reviewer';
 await preview.prepare(request);
 assert(panel.text().includes('@Renamed reviewer'));
 assert.equal(sent[1].selected_recipients[0],id);
 delete window.agentDisplayLabels[id];
 await preview.prepare(request);
 assert(panel.text().includes('@'+id));
})().catch(e=>{console.error(e);process.exitCode=1});
'''
        result = subprocess.run(['node', '-e', script, str(ROOT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
