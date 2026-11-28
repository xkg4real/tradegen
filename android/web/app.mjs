import {publicKeyBytes, registrationFile, sameKey} from './subscription.mjs';

const el = id => document.getElementById(id);
let worker;
let working = true;
let hasSubscription = false;

function draw() {
  const permission = 'Notification' in window ? Notification.permission : 'denied';
  el('enable').disabled = !worker || working || permission === 'denied' || hasSubscription;
  el('test').disabled = !worker || working || permission === 'denied';
  el('registered').hidden = !hasSubscription;
  el('disable').disabled = !worker || working;
  el('export').disabled = !worker || working || permission !== 'granted';
  el('status').textContent = !worker ? '알림을 사용할 수 없습니다. Android Chrome에서 운영 HTTPS 주소를 여세요.'
    : permission === 'denied' ? '알림이 차단되었습니다. Android 또는 Chrome의 사이트 알림 설정을 확인하세요.'
    : hasSubscription ? '브라우저 푸시 등록 정보가 있습니다.'
    : permission === 'granted' ? '기기 알림 허용됨 · 푸시 미등록' : '기기 알림 사용 전';
}

const errors = {
  DENIED: '알림 권한을 허용해야 합니다.',
  CONFIG_MISSING: '운영자가 이 사이트에 푸시 공개키를 설정해야 합니다.',
  INVALID_VAPID_KEY: '푸시 공개키 형식을 확인하세요.',
  KEY_CHANGED: '운영 공개키가 달라졌습니다. 운영자와 확인한 뒤 이 기기 등록을 해제하고 다시 등록하세요.',
  UNSUPPORTED_PROVIDER: '현재 전송기는 Android Chrome의 FCM 등록을 지원합니다.',
  INVALID_SUBSCRIPTION: '기기 등록 정보가 올바르지 않습니다. 등록 상태를 확인하세요.'
};
function run(action) {
  return async () => {
    if (working || !worker) return;
    working = true;
    draw();
    el('feedback').textContent = '';
    try { await action(); }
    catch (err) { el('feedback').textContent = errors[err.message] || '처리하지 못했습니다. 브라우저 설정과 연결 상태를 확인하세요.'; }
    finally {
      try { hasSubscription = Boolean(await worker.pushManager.getSubscription()); }
      catch { worker = null; }
      working = false;
      draw();
    }
  };
}
async function permission() {
  if (Notification.permission !== 'granted' && await Notification.requestPermission() !== 'granted') throw new Error('DENIED');
}
async function key() {
  const response = await fetch('/android/push-config.json', {cache: 'no-store', credentials: 'omit', redirect: 'error', mode: 'same-origin'});
  if (!response.ok) throw new Error('CONFIG_MISSING');
  const config = await response.json();
  return publicKeyBytes(config.applicationServerKey);
}

el('enable').onclick = run(async () => {
  await permission();
  const expected = await key();
  const previous = await worker.pushManager.getSubscription();
  const subscription = previous || await worker.pushManager.subscribe({userVisibleOnly: true, applicationServerKey: expected});
  if (!sameKey(subscription, expected)) throw new Error('KEY_CHANGED');
  registrationFile(subscription);
  el('feedback').textContent = '등록 파일을 저장해 운영 PC에 비공개로 전달하세요.';
});
el('test').onclick = run(async () => {
  await permission();
  await worker.showNotification('TRADEGEN 기기 테스트', {
    body: '이 기기에서 만든 테스트 알림입니다.', tag: 'tradegen-local-test', icon: '/android/icon-192.png'
  });
  el('feedback').textContent = '기기에 테스트 알림을 요청했습니다.';
});
el('export').onclick = run(async () => {
  const subscription = await worker.pushManager.getSubscription();
  if (!subscription) throw new Error('INVALID_SUBSCRIPTION');
  if (!sameKey(subscription, await key())) throw new Error('KEY_CHANGED');
  const file = new Blob([JSON.stringify(registrationFile(subscription))], {type: 'application/json'});
  const url = URL.createObjectURL(file);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'tradegen-android-subscription.json';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
  el('feedback').textContent = '등록 파일 저장을 요청했습니다. 이 파일은 비공개로 보관하세요.';
});
el('disable').onclick = run(async () => {
  const subscription = await worker.pushManager.getSubscription();
  if (subscription && !await subscription.unsubscribe()) throw new Error('UNSUBSCRIBE_FAILED');
  el('feedback').textContent = '이 기기 등록을 해제했습니다. 운영 PC에서도 해당 등록 파일을 제거하세요.';
});

async function init() {
  let timer;
  if (window.isSecureContext && 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window) {
    try {
      await navigator.serviceWorker.register('/android/sw.js', {scope: '/android/'});
      worker = await Promise.race([navigator.serviceWorker.ready,
        new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('WORKER_UNAVAILABLE')), 10000); })]);
      hasSubscription = Boolean(await worker.pushManager.getSubscription());
    } catch { worker = null; }
    finally { clearTimeout(timer); }
  }
  working = false;
  draw();
}
init();
