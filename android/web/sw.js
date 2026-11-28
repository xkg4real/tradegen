/* Notifications carry no account or approval details. The browser fetches those
   at the independent, same-origin approval service after the user opens it. */
const INBOX = new URL('/approvals/', self.location.origin).href;

self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('push', event => {
  event.waitUntil(self.registration.showNotification('TRADEGEN 알림', {
    body: '운영 알림과 승인 요청을 확인하세요.',
    icon: '/android/icon-192.png', badge: '/android/icon-192.png'
  }));
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  if (event.notification.tag === 'tradegen-local-test') {
    event.waitUntil(self.clients.openWindow(new URL('/android/', self.location.origin).href));
    return;
  }
  event.waitUntil(self.clients.openWindow(INBOX));
});
