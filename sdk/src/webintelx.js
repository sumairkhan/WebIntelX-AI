;(function (global) {
  'use strict';

  var DEFAULT_CONFIG = {
    enabled: true,
    autoTrack: true,
    batchSize: 10,
    flushInterval: 5000,
    maxRetries: 2,
    queueLimit: 100,
    credential: '',
    endpoint: ''
  };

  var state = {
    config: Object.assign({}, DEFAULT_CONFIG),
    initialized: false,
    enabled: true,
    status: 'uninitialized',
    queue: [],
    sessionId: '',
    flushTimer: null,
    retries: 0
  };

  function warn(message) {
    if (global.console && typeof global.console.warn === 'function') {
      global.console.warn(message);
    }
  }

  function isSafePlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
  }

  function sanitizeData(value) {
    if (value === null || typeof value === 'undefined') {
      return value;
    }

    if (Array.isArray(value)) {
      return value.map(function (item) { return sanitizeData(item); });
    }

    if (typeof value === 'object') {
      var safe = {};
      Object.keys(value).forEach(function (key) {
        var lowerKey = key.toLowerCase();
        if (lowerKey.indexOf('password') !== -1 || lowerKey.indexOf('token') !== -1 || lowerKey.indexOf('secret') !== -1 || lowerKey.indexOf('cookie') !== -1 || lowerKey.indexOf('authorization') !== -1) {
          return;
        }

        var sanitizedValue = sanitizeData(value[key]);
        if (typeof sanitizedValue !== 'undefined') {
          safe[key] = sanitizedValue;
        }
      });
      return safe;
    }

    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
      return value;
    }

    return undefined;
  }

  function createId() {
    if (global.crypto && typeof global.crypto.randomUUID === 'function') {
      return global.crypto.randomUUID();
    }

    return 'id_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
  }

  function getSessionStorage() {
    try {
      if (global.sessionStorage) {
        return global.sessionStorage;
      }
    } catch (error) {
      return null;
    }
    return null;
  }

  function getSessionId() {
    if (state.sessionId) {
      return state.sessionId;
    }

    var storage = getSessionStorage();
    if (storage) {
      var existing = storage.getItem('webintelx_session_id');
      if (existing) {
        state.sessionId = existing;
        return state.sessionId;
      }
    }

    state.sessionId = 'session_' + createId();
    if (storage) {
      try {
        storage.setItem('webintelx_session_id', state.sessionId);
      } catch (error) {
        // Ignore storage failures gracefully.
      }
    }

    return state.sessionId;
  }

  function getPageContext() {
    var location = global.location || {};
    var navigatorObject = global.navigator || {};
    var screenObject = global.screen || {};

    return {
      page_url: location.href || '',
      page_path: location.pathname || '',
      referrer: document && document.referrer ? document.referrer : '',
      user_agent: navigatorObject.userAgent || '',
      screen_width: screenObject.width || 0,
      screen_height: screenObject.height || 0,
      language: navigatorObject.language || ''
    };
  }

  function buildEvent(eventType, customData) {
    var payload = {
      event_id: createId(),
      timestamp: new Date().toISOString(),
      event_type: String(eventType || 'custom_event'),
      source: 'browser_sdk',
      session_id: getSessionId()
    };

    var pageContext = getPageContext();
    Object.keys(pageContext).forEach(function (key) {
      if (pageContext[key] !== '' && pageContext[key] !== 0) {
        payload[key] = pageContext[key];
      }
    });

    if (customData && isSafePlainObject(customData)) {
      payload.data = sanitizeData(customData);
    }

    return payload;
  }

  function addToQueue(event) {
    if (!event) {
      return;
    }

    state.queue.push(event);
    if (state.queue.length > state.config.queueLimit) {
      state.queue = state.queue.slice(state.queue.length - state.config.queueLimit);
    }
  }

  function flushQueue() {
    if (!state.initialized || !state.enabled || state.queue.length === 0) {
      return Promise.resolve(false);
    }

    var batch = state.queue.slice(0, state.config.batchSize);
    state.queue = state.queue.slice(batch.length);

    var body = {
      credential: state.config.credential,
      events: batch
    };

    var requestOptions = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    };

    return Promise.resolve()
      .then(function () {
        if (!global.fetch) {
          throw new Error('Fetch API not available.');
        }
        return global.fetch(state.config.endpoint, requestOptions);
      })
      .then(function (response) {
        if (!response || !response.ok) {
          throw new Error('Telemetry request failed.');
        }
        state.retries = 0;
        return true;
      })
      .catch(function () {
        state.queue = batch.concat(state.queue);
        if (state.queue.length > state.config.queueLimit) {
          state.queue = state.queue.slice(state.queue.length - state.config.queueLimit);
        }

        if (state.retries < state.config.maxRetries) {
          state.retries += 1;
          var delay = 250 * Math.pow(2, state.retries);
          if (global.setTimeout) {
            global.setTimeout(function () {
              flushQueue();
            }, delay);
          }
          return false;
        }

        state.retries = 0;
        return false;
      });
  }

  function startBatchTimer() {
    if (state.flushTimer) {
      clearTimeout(state.flushTimer);
    }

    state.flushTimer = global.setTimeout(function () {
      flushQueue();
      startBatchTimer();
    }, state.config.flushInterval);
  }

  function trackPageView() {
    if (!state.initialized || !state.enabled || state.status === 'disabled') {
      return null;
    }

    var event = buildEvent('page_view');
    addToQueue(event);
    if (state.queue.length >= state.config.batchSize) {
      flushQueue();
    }
    return event;
  }

  function attachNavigationTracking() {
    if (!global.window || !global.history || !global.addEventListener) {
      return;
    }

    var originalPushState = global.history.pushState;
    var originalReplaceState = global.history.replaceState;

    global.history.pushState = function () {
      var result = originalPushState.apply(this, arguments);
      global.setTimeout(function () { trackPageView(); }, 0);
      return result;
    };

    global.history.replaceState = function () {
      var result = originalReplaceState.apply(this, arguments);
      global.setTimeout(function () { trackPageView(); }, 0);
      return result;
    };

    global.addEventListener('popstate', function () {
      trackPageView();
    });
  }

  function attachUnloadFlush() {
    if (!global.addEventListener) {
      return;
    }

    global.addEventListener('pagehide', function () {
      if (state.queue.length > 0 && global.navigator && typeof global.navigator.sendBeacon === 'function' && state.config.endpoint) {
        var payload = {
          credential: state.config.credential,
          events: state.queue.slice(0, state.config.batchSize)
        };
        var data = new Blob([JSON.stringify(payload)], { type: 'application/json' });
        try {
          global.navigator.sendBeacon(state.config.endpoint, data);
        } catch (error) {
          // Best-effort flush only.
        }
      }
    });
  }

  var WebIntelX = {
    init: function (config) {
      state.config = Object.assign({}, DEFAULT_CONFIG, config || {});

      if (!state.config.credential || typeof state.config.credential !== 'string' || !state.config.credential.startsWith('wix_ing_')) {
        state.initialized = false;
        state.enabled = false;
        state.status = 'disabled';
        warn('WebIntelX init failed: missing or invalid ingestion credential.');
        return WebIntelX;
      }

      if (!state.config.endpoint || typeof state.config.endpoint !== 'string') {
        state.initialized = false;
        state.enabled = false;
        state.status = 'disabled';
        warn('WebIntelX init failed: missing endpoint.');
        return WebIntelX;
      }

      state.enabled = state.config.enabled !== false;
      state.initialized = state.enabled;
      state.status = state.enabled ? 'initialized' : 'disabled';
      getSessionId();

      if (state.enabled) {
        attachNavigationTracking();
        attachUnloadFlush();
        startBatchTimer();
        if (state.config.autoTrack !== false) {
          trackPageView();
        }
      }

      return WebIntelX;
    },

    track: function (eventType, data) {
      if (!state.initialized || !state.enabled) {
        return null;
      }

      var event = buildEvent(eventType, data);
      addToQueue(event);
      if (state.queue.length >= state.config.batchSize) {
        flushQueue();
      }
      return event;
    },

    flush: function () {
      return flushQueue();
    },

    getSessionId: function () {
      return getSessionId();
    },

    getStatus: function () {
      return {
        initialized: state.initialized,
        enabled: state.enabled,
        queueSize: state.queue.length,
        sessionId: state.sessionId || null
      };
    }
  };

  global.WebIntelX = WebIntelX;
})(typeof window !== 'undefined' ? window : globalThis);
