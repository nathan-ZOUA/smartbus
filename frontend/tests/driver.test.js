const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const driverScript = fs.readFileSync(
  path.join(__dirname, "../public/assets/driver.js"),
  "utf8",
);

function createDriverPage({ rejectReports = false } = {}) {
  let now = 1_800_000_000_000;
  let nextTimerId = 0;
  const elements = new Map();
  const timers = new Map();
  const listeners = new Map();
  const storage = new Map([["smartbus_driver_token", "test-token"]]);
  const requests = [];
  let onPosition;
  let clearedWatchId = null;
  let clearedTimerId = null;

  class FakeElement {
    constructor(id) {
      this.id = id;
      this.value = "";
      this.textContent = "";
      this.disabled = false;
      this.children = [];
      this.handlers = new Map();
      this.classList = {
        add: (name) => this.setClass(name, true),
        remove: (name) => this.setClass(name, false),
        toggle: (name, enabled) => this.setClass(name, enabled),
        contains: (name) => this.classes.has(name),
      };
      this.classes = new Set();
    }

    setClass(name, enabled) {
      if (enabled) this.classes.add(name);
      else this.classes.delete(name);
    }

    addEventListener(type, callback) {
      const callbacks = this.handlers.get(type) || [];
      callbacks.push(callback);
      this.handlers.set(type, callbacks);
    }

    dispatch(type, event = {}) {
      for (const callback of this.handlers.get(type) || []) callback(event);
    }

    replaceChildren(...children) {
      this.children = children;
      this.value = "";
    }

    add(option) {
      this.children.push(option);
      if (!this.value && option.value) this.value = option.value;
    }
  }

  for (const id of [
    "driver-message",
    "start-sharing",
    "stop-sharing",
    "gps-dot",
    "gps-state",
    "gps-detail",
    "driver-bus",
    "driver-login",
    "driver-controls",
    "driver-logout",
  ]) {
    elements.set(id, new FakeElement(id));
  }

  class ClockDate extends Date {
    static now() {
      return now;
    }
  }

  const documentListeners = new Map();
  const windowListeners = new Map();
  const context = {
    Date: ClockDate,
    Error,
    FormData,
    JSON,
    Math,
    Object,
    Option: function Option(label, value) {
      return { text: label, value };
    },
    Promise,
    Number,
    String,
    document: {
      visibilityState: "visible",
      getElementById: (id) => elements.get(id),
      addEventListener: (type, callback) => documentListeners.set(type, callback),
    },
    navigator: {
      geolocation: {
        watchPosition(success) {
          onPosition = success;
          return 42;
        },
        clearWatch(id) {
          clearedWatchId = id;
        },
      },
    },
    sessionStorage: {
      getItem: (key) => storage.get(key) ?? null,
      setItem: (key, value) => storage.set(key, value),
      removeItem: (key) => storage.delete(key),
    },
    window: {
      isSecureContext: true,
      setInterval(callback, delay) {
        const id = ++nextTimerId;
        timers.set(id, { callback, delay });
        return id;
      },
      clearInterval(id) {
        clearedTimerId = id;
        timers.delete(id);
      },
      addEventListener: (type, callback) => windowListeners.set(type, callback),
    },
    fetch: async (url, options) => {
      requests.push({ url, options });
      if (url.endsWith("/auth/me/")) return response(200, { role: "DRIVER" });
      if (url.endsWith("/my-buses/")) {
        return response(200, [{ id: 7, registration: "SB-007", status: "IN_SERVICE" }]);
      }
      if (url.endsWith("/positions/report/")) {
        return rejectReports
          ? response(401, { detail: "Session expirée." })
          : response(201, { id: requests.length });
      }
      if (url.endsWith("/auth/logout/")) return response(204, null);
      throw new Error(`Requête inattendue: ${url}`);
    },
  };
  vm.runInNewContext(driverScript, context);

  return {
    elements,
    requests,
    timers,
    documentListeners,
    get clearedWatchId() {
      return clearedWatchId;
    },
    get clearedTimerId() {
      return clearedTimerId;
    },
    advanceTime(milliseconds) {
      now += milliseconds;
    },
    emitPosition(latitude = 48.8566) {
      onPosition({
        timestamp: now,
        coords: {
          latitude,
          longitude: 2.3522,
          speed: 3,
          heading: 359.8,
          accuracy: 12,
        },
      });
    },
    get interval() {
      return [...timers.values()][0];
    },
  };
}

function response(status, body) {
  return {
    status,
    ok: status >= 200 && status < 300,
    json: async () => body,
  };
}

async function waitFor(assertion) {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    if (assertion()) return;
    await new Promise(setImmediate);
  }
  assert.fail("The expected browser action did not complete.");
}

test("shares fresh assigned-bus positions at a limited rate and stops on request", async () => {
  const page = createDriverPage();
  await waitFor(() => page.elements.get("driver-bus").value === "7");

  page.elements.get("start-sharing").dispatch("click");
  page.emitPosition();
  await waitFor(() => page.requests.some(({ url }) => url.endsWith("/positions/report/")));
  await waitFor(() => page.elements.get("gps-state").textContent === "Position partagée");

  const report = () => page.requests.filter(({ url }) => url.endsWith("/positions/report/"));
  const firstReport = JSON.parse(report()[0].options.body);
  assert.equal(firstReport.bus, 7);
  assert.equal(firstReport.heading, 0);

  page.advanceTime(5_000);
  page.emitPosition(48.8567);
  await new Promise(setImmediate);
  assert.equal(report().length, 1);

  page.advanceTime(5_000);
  assert.equal(page.interval.delay, 10_000);
  page.interval.callback();
  await waitFor(() => report().length === 2);

  page.advanceTime(10_000);
  page.interval.callback();
  await new Promise(setImmediate);
  assert.equal(report().length, 2);

  const stopButton = page.elements.get("stop-sharing");
  stopButton.dispatch("click");
  assert.equal(page.clearedWatchId, 42);
  assert.equal(page.timers.size, 0);
  assert.equal(page.elements.get("gps-state").textContent, "Partage désactivé");
});

test("stops GPS sharing when the API rejects the driver's session", async () => {
  const page = createDriverPage({ rejectReports: true });
  await waitFor(() => page.elements.get("driver-bus").value === "7");

  page.elements.get("start-sharing").dispatch("click");
  page.emitPosition();
  await waitFor(() => page.elements.get("driver-message").textContent.includes("Session invalide"));

  assert.equal(page.clearedWatchId, 42);
  assert.equal(page.timers.size, 0);
  assert.equal(page.elements.get("gps-state").textContent, "Partage désactivé");
});
