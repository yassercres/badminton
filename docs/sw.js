// Minimal service worker — its presence makes the wrapper installable as a PWA.
// It doesn't cache anything; requests pass straight through to the network.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});
