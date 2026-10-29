/* Execute the actual inline viewer logic in an inert DOM. No sockets or APIs. */
'use strict';
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const html=fs.readFileSync(path.join(__dirname,'../patchcourt/web/live.html'),'utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const elements=new Map();
class Element {
  constructor(){this._text='';this.disabled=false;this.hidden=false;this.className='';this.children=[];this.classList={toggle(){}};}
  get textContent(){return this._text;}
  set textContent(value){this._text=String(value);}
  replaceChildren(...children){this.children=children;}
  append(...children){this.children.push(...children);}
  setAttribute(){}
}
function element(id){if(!elements.has(id))elements.set(id,new Element());return elements.get(id);}
let state={status:'INCONCLUSIVE',events:[],runs:1,provider:'glm',model:'synthetic-model',report:{
  status:'INCONCLUSIVE',reason:'Synthetic network failure',requests:[],total_reported_tokens:null,
  request_accounting:{reservations_by_kind:{model:0,search:1,discovery:0}}}};
const requests=[];
const context=vm.createContext({
  document:{getElementById:id=>id==='recorded-data'?null:element(id),querySelectorAll:()=>[],createElement:()=>new Element()},
  console,AbortController,setTimeout,clearTimeout,setInterval:()=>0,location:{protocol:'http:'},
  fetch:async(url,options={})=>{
    requests.push({url,method:options.method||'GET'});
    let body;
    if(url==='/session')body={session:'synthetic-local-session',provider:'glm',model:'synthetic-model'};
    else if(url==='/state')body=state;
    else if(url==='/run'){
      assert.equal(options.method,'POST');
      state={...state,runs:state.runs+1};
      body={status:'RUNNING'};
    }else throw Error('Unexpected local endpoint '+url);
    return {ok:true,status:200,json:async()=>JSON.parse(JSON.stringify(body))};
  },
});
(async()=>{
  vm.runInContext(script,context);
  await vm.runInContext('(async()=>{for(let i=0;i<50&&connecting;i++)await Promise.resolve();})()',context);
  assert.equal(element('state').textContent,'INCONCLUSIVE');
  assert.equal(element('after-status').textContent,'INCONCLUSIVE');
  assert.equal(element('after-value').textContent,'—');
  assert.equal(element('after-detail').textContent,'Synthetic network failure');
  assert.equal(element('run').disabled,false);
  assert.equal(element('run').textContent,'Start another run →');
  assert.equal(element('connection').hidden,true);
  assert.equal(element('calls-label').textContent,'Model requests');
  assert.equal(JSON.parse(element('summary').textContent).request_accounting.reservations_by_kind.search,1);
  for(let i=0;i<3;i++)await vm.runInContext('poll()',context);
  await vm.runInContext('reconnect()',context);
  assert.equal(requests.filter(request=>request.method==='POST').length,0,'Polling and reconnecting must never start a paid run');
  await vm.runInContext("$('run').onclick()",context);
  assert.equal(requests.filter(request=>request.method==='POST').length,1,'An explicit click sends exactly one fixed run request');
  assert.equal(element('state').textContent,'INCONCLUSIVE');
  assert.equal(element('run').disabled,false);
  state={...state,runs:3,limits:{max_runs:3},report:null,error:'Synthetic worker failure'};
  await vm.runInContext('poll()',context);
  assert.equal(element('after-detail').textContent,'Synthetic worker failure');
  assert.equal(element('elapsed').textContent,'Run ended · inspect details');
  assert.equal(element('run').disabled,true,'Three-run server budget stays enforced for inconclusive attempts');
  assert.equal(requests.filter(request=>request.method==='POST').length,1);
  state={...state,runs:3,limits:{max_runs:5,max_model_requests:200,max_tool_turns:12}};
  await vm.runInContext('poll()',context);
  assert.equal(element('run').disabled,false,'An explicit server run limit replaces the old hardcoded three');
  assert.equal(JSON.parse(element('run-settings').textContent).max_model_requests,200);
  state={...state,runs:5};
  await vm.runInContext('poll()',context);
  assert.equal(element('run').disabled,true,'The configured server limit remains enforced');
  assert.equal(requests.filter(request=>request.method==='POST').length,1);
  state={...state,runs:500,limits:{max_runs:0}};
  await vm.runInContext('poll()',context);
  assert.equal(element('run').disabled,false,'Zero means unlimited user-started sessions');
  console.log('Actual live viewer state transitions PASS; no network or provider calls.');
})().catch(error=>{console.error(error);process.exitCode=1;});
