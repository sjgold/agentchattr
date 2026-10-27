"""Execute shipped init/render functions with the CDN global absent."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
BOOT=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(process.argv[2]+'/static/chat.js','utf8');
const a=source.indexOf('function init()'),b=source.indexOf('function linkifyUrls(',a);
assert(a>=0&&b>a);
const called=[];
const context={window:{},console,document:{addEventListener(){},createElement(){return {
  textContent:'',get innerHTML(){return this.textContent.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')}
}}}};
for(const name of ['detectPlatform','fetchRoles','connectWebSocket','setupInput','setupDragDrop','setupPaste','setupScroll','setupSettingsKeys','setupKeyboardShortcuts','watchChatEmptyState','checkForUpdate'])context[name]=()=>called.push(name);
for(const name of ['RulesPanel','Jobs','Sessions','Channels'])context[name]={init:()=>called.push(name)};
for(const name of ['colorMentions','linkifyUrls','linkifyPaths'])context[name]=x=>x;
vm.createContext(context);
const h=source.indexOf('function escapeHtml('),end=source.indexOf('window.escapeHtml',h);
vm.runInContext(source.slice(h,end),context);
vm.runInContext(source.slice(a,b),context);
'''


class OfflineMarkdownTests(unittest.TestCase):
    def run_js(self,body):
        result=subprocess.run([shutil.which('node'),'-',str(ROOT)],input=BOOT+'\n'+body,
                              capture_output=True,text=True,encoding='utf-8',timeout=15)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_init_completes_without_cdn_and_reaches_connection_and_panels(self):
        self.run_js("context.init();assert(called.includes('connectWebSocket'));for(const n of ['RulesPanel','Jobs','Sessions','Channels'])assert(called.includes(n));")

    def test_messages_escape_literal_html_and_preserve_lines_without_cdn(self):
        self.run_js(r'''
const raw='<img src=x onerror=alert(1)> & entity\r\n`<script>`\nC:\\new\\tests';
const result=context.renderMarkdown(raw);
assert.strictEqual(result,'&lt;img src=x onerror=alert(1)&gt; &amp; entity<br>`&lt;script&gt;`<br>C:\\new\\tests');
assert(!result.includes('<img'));assert(!result.includes('<script'));
''')

    def test_present_cdn_keeps_markdown_parser_path(self):
        self.run_js("let options=0,parses=0;context.marked={setOptions(){options++},parse(){parses++;return '<p>formatted</p>'}};context.init();assert.strictEqual(context.renderMarkdown('**x**'),'formatted');assert.strictEqual(options,1);assert.strictEqual(parses,1);")
