const VERSION = "v1";
const SHELL_CACHE = `planna-shell-${VERSION}`;
const META_CACHE = `planna-meta-${VERSION}`;
const USER_CACHE_PREFIX = `planna-user-${VERSION}-`;
const OWNER_KEY = "/__planna_cache_owner__";
const SHELL = [
  "/",
  "/privacidade",
  "/manifest.webmanifest",
  "/icon-192.png",
  "/icon-512.png",
  "/icon-maskable-512.png",
  "/apple-touch-icon.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((names) =>
        Promise.all(
          names
            .filter(
              (name) =>
                name.startsWith("planna-shell-") && name !== SHELL_CACHE,
            )
            .map((name) => caches.delete(name)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

async function owner() {
  const response = await (await caches.open(META_CACHE)).match(OWNER_KEY);
  return response?.text();
}

async function setOwner(id) {
  if (!/^[A-Za-z0-9-]{1,64}$/.test(id)) return null;
  const cacheName = `${USER_CACHE_PREFIX}${id}`;
  const names = await caches.keys();
  await Promise.all(
    names
      .filter((name) => name.startsWith("planna-user-") && name !== cacheName)
      .map((name) => caches.delete(name)),
  );
  await (await caches.open(META_CACHE)).put(OWNER_KEY, new Response(id));
  return cacheName;
}

async function clearPrivateData() {
  const names = await caches.keys();
  await Promise.all(
    names
      .filter((name) => name.startsWith("planna-user-") || name.startsWith("planna-meta-"))
      .map((name) => caches.delete(name)),
  );
}

async function privateCache() {
  const id = await owner();
  return id ? caches.open(`${USER_CACHE_PREFIX}${id}`) : null;
}

async function authenticatedGet(request) {
  let response;
  try {
    response = await fetch(request);
  } catch (error) {
    const cached = await (await privateCache())?.match(request);
    if (cached) return cached;
    throw error;
  }
  if (response.status === 401) await clearPrivateData().catch(() => undefined);
  if (!response.ok) return response;

  try {
    let cache;
    if (new URL(request.url).pathname === "/api/auth/me") {
      const data = await response.clone().json();
      const cacheName = await setOwner(String(data.id || ""));
      cache = cacheName ? await caches.open(cacheName) : null;
    } else {
      cache = await privateCache();
    }
    await cache?.put(request, response.clone());
  } catch {}
  return response;
}

async function shellGet(request) {
  const cache = await caches.open(SHELL_CACHE);
  if (request.mode === "navigate") {
    try {
      const response = await fetch(request);
      if (response.ok) await cache.put(request, response.clone()).catch(() => undefined);
      return response;
    } catch {
      return (await cache.match(request)) || cache.match("/");
    }
  }
  const cached = await cache.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok && new URL(request.url).origin === self.location.origin) {
    await cache.put(request, response.clone()).catch(() => undefined);
  }
  return response;
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (url.pathname === "/api/auth/logout" && request.method === "POST") {
    event.respondWith(
      fetch(request).then(async (response) => {
        if (response.ok) await clearPrivateData().catch(() => undefined);
        return response;
      }),
    );
    return;
  }
  if (url.pathname.startsWith("/api/") && request.method === "GET") {
    event.respondWith(authenticatedGet(request));
    return;
  }
  if (request.method === "GET") event.respondWith(shellGet(request));
});

self.addEventListener("message", (event) => {
  if (event.data?.type === "CLEAR_PRIVATE_DATA") {
    event.waitUntil(clearPrivateData());
  }
});
