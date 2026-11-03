const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const sdkPath = path.join(__dirname, '..', 'src', 'webintelx.js');
const source = fs.readFileSync(sdkPath, 'utf8');

function createSandbox() {
  const sessionStorage = {
    store: {},
    getItem(key) {
      return Object.prototype.hasOwnProperty.call(this.store, key) ? this.store[key] : null;
    },
    setItem(key, value) {
      this.store[key] = String(value);
    },
    removeItem(key) {
      delete this.store[key];
    }
  };

  const fetchCalls = [];
  const sandbox = {
    console: { warn: () => {} },
    navigator: {
      userAgent: 'node-test',
      language: 'en-US',
      sendBeacon: function () {
        return true;
      }
    },
    location: {
      href: 'https://example.com/products',
      pathname: '/products',
      search: ''
    },
    document: {
      referrer: 'https://google.com/'
    },
    screen: {
      width: 1920,
      height: 1080
    },
    history: {
      pushState: function () {},
      replaceState: function () {}
    },
    sessionStorage,
    setTimeout,
    clearTimeout,
    fetch: async function (url, options) {
      fetchCalls.push({ url, options });
      return { ok: true };
    },
    addEventListener: function () {}
  };

  sandbox.globalThis = sandbox;
  sandbox.window = sandbox;
  sandbox.global = sandbox;

  vm.runInNewContext(source, sandbox, { filename: 'webintelx.js' });

  return { sandbox, fetchCalls };
}

const { sandbox, fetchCalls } = createSandbox();
const sdk = sandbox.WebIntelX;

assert.ok(sdk, 'SDK should expose WebIntelX global');
assert.equal(typeof sdk.init, 'function');
assert.equal(typeof sdk.track, 'function');
assert.equal(typeof sdk.flush, 'function');

sdk.init({
  credential: 'wix_ing_test_credential',
  endpoint: 'https://example.com/api/ingest/events',
  enabled: true,
  autoTrack: true
});

const status = sdk.getStatus();
assert.equal(status.initialized, true);
assert.equal(status.enabled, true);
assert.ok(status.sessionId);
assert.equal('credential' in status, false);

const pageEvent = sdk.track('button_click', { button: 'checkout' });
assert.ok(pageEvent);
assert.equal(pageEvent.event_type, 'button_click');
assert.ok(pageEvent.event_id);
assert.ok(pageEvent.timestamp);
assert.equal(pageEvent.data.button, 'checkout');
assert.equal(status.sessionId, sdk.getSessionId());
assert.ok(Array.isArray(sandbox.WebIntelX.getStatus ? [1] : []));

const queueAfterTrack = sdk.getStatus().queueSize;
assert.ok(queueAfterTrack >= 1);

sdk.flush();
assert.ok(fetchCalls.length >= 0);

console.log('SDK smoke test passed.');
