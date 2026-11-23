import test from 'node:test';
import assert from 'node:assert/strict';
import {createECDH, randomBytes} from 'node:crypto';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {publicKeyBytes, sameKey, registrationFile} from '../web/subscription.mjs';

const ec = createECDH('prime256v1');
const pub = ec.generateKeys();
const pubText = pub.toString('base64url');
const auth = randomBytes(16).toString('base64url');
const site = 'https://approval.example';
const endpoint = 'https://fcm.googleapis.com/fcm/send/test_token-example';
function sub(input = endpoint) {
  return {options:{applicationServerKey:pub}, toJSON:() => ({endpoint:input, expirationTime:null, keys:{p256dh:pubText, auth}, ignored:'extra'})};
}
function serviceWorker() {
  const handlers = {}; const opened = []; const shown = [];
  vm.runInNewContext(readFileSync(new URL('../web/sw.js',import.meta.url),'utf8'), {URL, self:{
    location:new URL(site + '/android/sw.js'), addEventListener:(key,fn)=>{handlers[key]=fn;},
    clients:{openWindow:async url=>{opened.push(url);}}, registration:{showNotification:async (...args)=>shown.push(args)}
  }});
  async function fire(name, input) {
    let pending;
    handlers[name]({...input,waitUntil:promise=>{pending=promise;}});
    assert.ok(pending); await pending;
  }
  return {opened,shown,fire};
}

test('issued P-256 VAPID public key round trips; wrong or missing key requires re-enrollment',()=>{
  assert.deepEqual([...publicKeyBytes(pubText)],[...pub]);
  assert.equal(sameKey(sub(),publicKeyBytes(pubText)),true);
  assert.equal(sameKey(sub(),createECDH('prime256v1').generateKeys()),false);
  assert.equal(sameKey({options:{}},publicKeyBytes(pubText)),false);
  for(const invalid of [undefined, pubText+'=', Buffer.alloc(65).toString('base64url')]) assert.throws(()=>publicKeyBytes(invalid));
});
test('exports exactly standard subscription fields without leaking other properties',()=>{
  assert.deepEqual(registrationFile(sub()),{endpoint,expirationTime:null,keys:{p256dh:pubText,auth}});
});
test('unknown notification providers and noncanonical endpoint targets are rejected',()=>{
  for (const url of [endpoint.replace('https:','http:'),endpoint.replace('.com/', '.com.test/'),endpoint.replace('/fcm/send/','/other/'),
    endpoint+'?parameter=x',endpoint+'#fragment',endpoint.replace('fcm.googleapis.com','user@fcm.googleapis.com'),
    endpoint+'/extra', endpoint+'%20', endpoint+'\n', endpoint.replace('fcm.googleapis.com','fcm.googleapis.com:443'),
    endpoint.replace('fcm.googleapis.com','fcm.googleapis.com:8443')]) assert.throws(()=>registrationFile(sub(url)));
  for (const expirationTime of [0,-1,'100']) {
    const invalid = {...sub().toJSON(), expirationTime};
    assert.throws(()=>registrationFile({toJSON:()=>invalid}));
  }
});
test('empty or untrusted push data always shows a generic notification and opens only the fixed inbox', async()=>{
  const sw=serviceWorker();
  await sw.fire('push',{});
  await sw.fire('push',{data:{json:()=>{throw Error('payload must never be consulted');}}});
  assert.equal(sw.shown.length,2); assert.equal(sw.shown[0][0],sw.shown[1][0]);
  let closed=false;
  await sw.fire('notificationclick',{notification:{close:()=>{closed=true;},data:{url:'https://attacker.example', action:'approve'}}});
  assert.equal(closed,true);assert.deepEqual(sw.opened,[site+'/approvals/']);
});
test('local display test opens the companion only',async()=>{
  const sw=serviceWorker();
  await sw.fire('notificationclick',{notification:{tag:'tradegen-local-test',close:()=>{}}});
  assert.deepEqual(sw.opened,[site+'/android/']);
});

test('registration, key rotation and removal use browser state without any live push service',async t=>{
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id,{textContent:'',hidden:false,disabled:false});
    return elements.get(id);
  };
  let subscription=null, serverKey=pubText;
  const calls=[];
  const registration={scope:site+'/android/', pushManager:{
    getSubscription:async()=>subscription,
    subscribe:async options=>{
      assert.deepEqual([...options.applicationServerKey],[...pub]);assert.equal(options.userVisibleOnly,true);
      subscription={...sub(),unsubscribe:async()=>{calls.push('unsubscribe');subscription=null;return true;}};
      calls.push('subscribe');return subscription;
    }
  },showNotification:async(_title,options)=>calls.push(options.tag)};
  const saved=new Map();
  function install(name,value) {
    saved.set(name,Object.getOwnPropertyDescriptor(globalThis,name));
    Object.defineProperty(globalThis,name,{value,configurable:true});
  }
  t.after(()=>{for(const [name,original] of saved) {
    if(original) Object.defineProperty(globalThis,name,original); else delete globalThis[name];
  }});
  const notifications={permission:'default',requestPermission:async()=>{calls.push('permission');notifications.permission='granted';return 'granted';}};
  install('Notification',notifications);
  install('document',{getElementById:element,createElement:()=>assert.fail('No file should be made when VAPID rotated')});
  install('window',{isSecureContext:true,PushManager:{},Notification:notifications});
  install('navigator',{serviceWorker:{register:async(url,options)=>{assert.equal(url,'/android/sw.js');assert.equal(options.scope,'/android/');},ready:Promise.resolve(registration)}});
  install('fetch',async(url,options)=>{assert.equal(url,'/android/push-config.json');assert.equal(options.credentials,'omit');return {ok:true,json:async()=>({applicationServerKey:serverKey})};});
  await import('../web/app.mjs?fixture=registration');
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(element('registered').hidden,true);
  await element('enable').onclick();
  assert.deepEqual(calls,['permission','subscribe']);
  assert.equal(element('registered').hidden,false);
  assert.equal(element('enable').disabled,true);
  await element('test').onclick();
  assert.equal(calls.at(-1),'tradegen-local-test');
  serverKey=createECDH('prime256v1').generateKeys().toString('base64url');
  await element('export').onclick();
  assert.match(element('feedback').textContent,/공개키가 달라졌습니다/);
  await element('disable').onclick();
  assert.equal(calls.at(-1),'unsubscribe');assert.equal(element('registered').hidden,true);
});
