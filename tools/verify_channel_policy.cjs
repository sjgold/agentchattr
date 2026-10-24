// Actual integration functions with explicit DOM/network seams, not browser proof.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = name => fs.readFileSync(path.join(__dirname, '..', 'static', name), 'utf8');
function extract(file, name) {
  const text = source(file);
  let begin = text.indexOf('async function ' + name + '(');
  if (begin < 0) begin = text.indexOf('function ' + name + '(');
  const end = text.indexOf('\n}', begin);
  assert.ok(begin >= 0 && end > begin, 'actual source ' + name);
  return text.slice(begin, end + 2);
}
function heldJobs() {
  const element = () => ({disabled:false,readOnly:false,textContent:'',hidden:false,
    classList:{toggle(name,value){this[name]=value;}}});
  const input=element(), send=element(), create=element(), badge=element(), status=element();
  const nodes={'jobs-conv-input-text':input,'jobs-conv-send':send,'jobs-badge':badge};
  const context=vm.createContext({console,jobsData:[{id:1,channel:'general',messages:[{text:'cached conversation'}]}],
    activeJobId:1,jobLoadError:'',jobUnread:{1:7},activeChannel:'general',
    ChannelLifecycle:{canWrite:()=>true,ownerAvailable:()=>true,guardWrite:()=>true},
    document:{getElementById:id=>nodes[id]||null,querySelector:selector=>selector==='.jobs-create-btn'?create:null,
      querySelectorAll:()=>[status]},
    syncJobUnreadCache(){},renderJobsList(){},_unhideResolvedBreadcrumbs(){}});
  context.window=context;
  for(const name of ['jobCanWrite','applyJobChannelState','updateJobsBadge','applyJobsSnapshot'])
    vm.runInContext(extract('jobs.js',name),context);
  context.applyJobsSnapshot({type:'jobs',error:'Saved jobs are held. Repair storage and restart.'});
  return {context,input,send,create,badge,status};
}
const cases=[];
const test=(name,run)=>cases.push({name,run});
test('held jobs close create status and composer controls while retaining cached records',()=>{
  const env=heldJobs();
  assert.equal(env.create.disabled,true);
  assert.equal(env.send.disabled,true);
  assert.equal(env.input.readOnly,true);
  assert.equal(env.status.disabled,true);
  assert.equal(env.context.jobsData[0].messages[0].text,'cached conversation');
});
test('held jobs badge shows held status rather than an authoritative numeric count',()=>{
  const env=heldJobs();
  assert.equal(env.badge.textContent,'held');
  assert.equal(env.badge.classList.hidden,false);
});
test('mixed message delete refuses before WS while id zero remains a real source',()=>{
  const sent=[],lookups=[];
  const context=vm.createContext({console,deleteSelected:new Set([0,1]),
    document:{querySelector:selector=>{lookups.push(selector);return {dataset:{channel:selector.includes('"0"')?'archived':'peer'}};}},
    ChannelLifecycle:{guardWrite:channel=>channel==='peer',renderPolicy(){}},
    ws:{send:value=>sent.push(value)},exitDeleteMode(){throw new Error('selection must be kept');}});
  context.window=context;
  vm.runInContext(extract('chat.js','channelMessageWritable')+extract('chat.js','confirmDelete'),context);
  context.confirmDelete();
  assert.equal(sent.length,0);assert.equal(context.deleteSelected.size,2);
  assert.ok(lookups.some(selector=>selector.includes('"0"')));
});
test('actual Stop remains available when ordinary channel writes are unavailable',async()=>{
  const calls=[],updates=[];
  const context=vm.createContext({console,activeSession:{id:42,channel:'archived'},SESSION_TOKEN:'fixture',
    ChannelLifecycle:{guardWrite:()=>false,canWrite:()=>false},
    fetch:async(url,options)=>{calls.push({url,options});return {ok:true,json:async()=>({id:42,state:'stopped'})};},
    handleSessionEvent:(action,value)=>updates.push({action,value}),refreshStopStatus:async()=>{},
    clearEndSessionConfirm(){},alert(message){throw new Error('Unexpected alert '+message);}});
  context.window=context;
  vm.runInContext(extract('sessions.js','endActiveSession'),context);
  await context.endActiveSession();
  assert.equal(calls.length,1);assert.equal(calls[0].url,'/api/sessions/42/stop');
  assert.equal(calls[0].options.method,'POST');assert.equal(updates[0].value.state,'stopped');
});
(async()=>{
  let failures=0;
  for(const item of cases){try{await item.run();console.log('PASS '+item.name);}catch(error){failures++;console.error('FAIL '+item.name+'\n'+error.stack);}}
  console.log(JSON.stringify({cases:cases.length,failures,scope:'actual_source_integration_vm_only'}));
  process.exitCode=failures?1:0;
})();
