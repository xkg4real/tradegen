/* Configuration and browser subscription files are the only input contracts. */
function decodeKey(value, size, error) {
  if (typeof value !== 'string' || value.length !== Math.ceil(size * 4 / 3) || !/^[A-Za-z0-9_-]+$/.test(value)) {
    throw new Error(error);
  }
  const raw = atob(value.replace(/-/g, '+').replace(/_/g, '/'));
  const canonical = btoa(raw).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  if (raw.length !== size || canonical !== value) throw new Error(error);
  return Uint8Array.from(raw, c => c.charCodeAt(0));
}

export function publicKeyBytes(value) {
  const bytes = decodeKey(value, 65, 'INVALID_VAPID_KEY');
  if (bytes[0] !== 4) throw new Error('INVALID_VAPID_KEY');
  return bytes;
}

export function sameKey(subscription, expected) {
  const actual = subscription.options?.applicationServerKey;
  if (!actual) return false;
  const bytes = new Uint8Array(actual);
  return bytes.length === expected.length && bytes.every((v, i) => v === expected[i]);
}

export function registrationFile(subscription) {
  const {endpoint, keys, expirationTime = null} = subscription.toJSON();
  if (typeof endpoint !== 'string' || !/^https:\/\/fcm\.googleapis\.com\/(?:wp|fcm\/send)\/[A-Za-z0-9_:-]{1,4096}$/.test(endpoint)) {
    throw new Error('UNSUPPORTED_PROVIDER');
  }
  if (expirationTime !== null && (!Number.isSafeInteger(expirationTime) || expirationTime <= 0)) {
    throw new Error('INVALID_SUBSCRIPTION');
  }
  const pub = decodeKey(keys?.p256dh, 65, 'INVALID_SUBSCRIPTION');
  if (pub[0] !== 4) throw new Error('INVALID_SUBSCRIPTION');
  decodeKey(keys?.auth, 16, 'INVALID_SUBSCRIPTION');
  return {endpoint, expirationTime, keys: {p256dh: keys.p256dh, auth: keys.auth}};
}
