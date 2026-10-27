"""Display-only labels must survive restarts without changing routing identities."""
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class AgentDisplayLabelTests(unittest.TestCase):
    def test_persisted_reclaimable_labels_are_public_without_tokens_or_presence(self):
        from registry import RuntimeRegistry
        with tempfile.TemporaryDirectory() as folder:
            registry = RuntimeRegistry(folder)
            registry.seed({'cli-abcd-old': {'label': 'Agy', 'color': '#123456'}})
            instance = registry.register('cli-abcd-old')
            registry.deregister(instance['name'], reclaimable=True)
            cold = RuntimeRegistry(folder)
            self.assertEqual(cold.display_labels()[instance['name']], 'Agy')
            self.assertEqual(cold.get_agent_config(), {})
            self.assertNotIn(instance.get('token'), cold.display_labels().values())

    def test_saved_package_family_labels_cover_previous_launches(self):
        import app
        from types import SimpleNamespace
        packages = [{'id': 'uat', 'seats': [{'id': 'agy', 'name': 'Agy', 'adapter': 'cli'}]}]
        with patch.object(app, 'registry', None), patch.object(app, 'api_seat_store', SimpleNamespace(list=lambda: packages)):
            labels = app.agent_display_labels()
        family = 'cli-' + hashlib.sha256(b'uat/agy').hexdigest()[:8] + '-'
        self.assertEqual(labels[family], 'Agy')
        self.assertEqual(set(labels), {family})

    def test_node_chat_join_session_and_roles_use_labels_but_keep_ids(self):
        script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const root=process.argv[1];global.window=global;
vm.runInThisContext(fs.readFileSync(root+'/static/core.js','utf8'));
window.agentDisplayLabels={'cli-dead-old':'Agy <safe>','cli-1234abcd-':'Codex Sol 6.1'};
assert.equal(agentDisplayName('cli-dead-old'),'Agy <safe>');
assert.equal(agentDisplayName('cli-1234abcd-new'),'Codex Sol 6.1');
assert.equal(agentDisplayName('unknown'),'unknown');
let chat=fs.readFileSync(root+'/static/chat.js','utf8');
if(process.env.AGENT_LABEL_TEST_MUTANT==='raw-render') chat=chat.replaceAll('escapeHtml(agentDisplayName(msg.sender))','escapeHtml(msg.sender)');
function extract(source,name,next){return source.slice(source.indexOf('function '+name+'('),source.indexOf('function '+next+'(',source.indexOf('function '+name+'(')));}
const made=[];
global.document={getElementById(){return null},createElement(){return {dataset:{},style:{},classList:{add(){}},innerHTML:'',querySelector(){return null}}}};
global.maybeInsertDateDivider=()=>{};global.getColor=()=> '#123';global.activeChannel='general';
global.RecipientPreview={appendReceipt(){}};global.escapeHtml=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
vm.runInThisContext(extract(chat,'appendMessage','getSenderClass'));
global.username='Seth';global.todos={};global.agentHats={};global._agentRoles={};
global.getSenderClass=()=> 'agent';global.styleHashtags=x=>x;global.renderMarkdown=x=>x;
global.resolveAgent=()=>null;global.getAvatarSvg=()=>'';global.todoStatusLabel=()=>'';global.addCodeCopyButtons=()=>{};
for(const type of ['join','leave','chat']){
 const msg={id:made.length+1,type,sender:'cli-dead-old',channel:'general',text:'hello'};
 appendMessage(msg,{history:true,container:{appendChild(el){made.push(el)}}});
 assert(made.at(-1).innerHTML.includes('Agy &lt;safe&gt;'));
 assert(!made.at(-1).innerHTML.includes('>cli-dead-old<'));
 assert.equal(msg.sender,'cli-dead-old');
 assert.equal(made.at(-1).dataset.sender,'cli-dead-old');
}
const sessions=fs.readFileSync(root+'/static/sessions.js','utf8');
vm.runInThisContext(extract(sessions,'buildSessionCastEditor','recoveryPolicyEditor'));
const html=buildSessionCastEditor({roles:['writer'],phases:[]},{writer:'cli-dead-old'},['cli-dead-old']);
assert(html.includes('value="cli-dead-old"'));
assert(html.includes('>Agy &lt;safe&gt;</option>'));
const roleSource=extract(chat,'_syncBubbleRolePills','_setRole');
const button={classList:{toggle(){}}};global._agentRoles={'cli-dead-old':'Reviewer'};
document.querySelectorAll=()=>[{dataset:{sender:'cli-dead-old'},querySelector(sel){return sel==='.bubble-role'?button:{textContent:'Agy <safe>'}}}];
vm.runInThisContext(roleSource);_syncBubbleRolePills('cli-dead-old');assert.equal(button.textContent,'Reviewer');
const artifacts=fs.readFileSync(root+'/static/artifacts.js','utf8');
assert(artifacts.includes('agentDisplayName(row.author_name)'));
'''
        result = subprocess.run(['node', '-e', script, str(ROOT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
