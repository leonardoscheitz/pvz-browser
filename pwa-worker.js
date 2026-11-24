// Generated build metadata is prepended by scripts/build.py.
const cacheName = "pvz-browser-offline-" + BUILD_ID;
const scope = new URL(self.registration.scope);
const index = new URL("index.html", scope).href;
self.addEventListener("install", event => {
  event.waitUntil((async () => {
    const cache = await caches.open(cacheName);
    try {
      // Small batches avoid overwhelming memory and the connection on mobile.
      for (let i = 0; i < OFFLINE_FILES.length; i += 4) {
        await cache.addAll(OFFLINE_FILES.slice(i, i + 4).map(path =>
          new Request(new URL(path, scope), {cache: path.startsWith("assets/") ? "force-cache" : "reload"})));
      }
    } catch (error) {
      await caches.delete(cacheName);
      throw error;
    }
  })());
});
self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    for (const name of await caches.keys()) {
      if (name.startsWith("pvz-browser-offline-") && name !== cacheName) await caches.delete(name);
    }
    await self.clients.claim();
  })());
});
self.addEventListener("fetch", event => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== scope.origin ||
      !url.pathname.startsWith(scope.pathname)) return;
  const relative = url.pathname.slice(scope.pathname.length);
  if (request.mode === "navigate" && (relative === "" || relative === "index.html")) {
    // One consistent release per active worker; a new release activates after
    // the old game tabs are closed. Do not mix a new HTML with an old cache.
    event.respondWith(caches.open(cacheName).then(async cache =>
      await cache.match(index) || fetch(request)));
  } else if (OFFLINE_FILES.includes(relative) && !url.search) {
    event.respondWith(caches.open(cacheName).then(async cache =>
      await cache.match(request) || fetch(request)));
  }
});
