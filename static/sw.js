// DoseClock Service Worker
// Handles offline functionality and push notifications

const CACHE_NAME = 'doseclock-v2';
const STATIC_CACHE = 'doseclock-static-v2';
const DYNAMIC_CACHE = 'doseclock-dynamic-v2';

// Files to cache for offline use
const STATIC_FILES = [
  '/',
  '/static/css/main.css',
  '/static/css/modo_minimalista.css',
  '/static/css/modo_avanzado.css',
  '/static/css/accesibilidad.css',
  '/static/js/cronometro.js',
  '/static/js/notificaciones.js',
  '/static/js/calendario.js',
  '/static/js/pastillero.js',
  '/static/manifest.json',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js'
];

// Install event - cache static files
self.addEventListener('install', (event) => {
  console.log('[SW] Installing...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Caching static files');
        return cache.addAll(STATIC_FILES);
      })
      .then(() => {
        console.log('[SW] Skip waiting');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[SW] Cache failed:', error);
      })
  );
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating...');
  
  event.waitUntil(
    caches.keys()
      .then((keyList) => {
        return Promise.all(
          keyList.map((key) => {
            if (key !== STATIC_CACHE && key !== DYNAMIC_CACHE) {
              console.log('[SW] Removing old cache:', key);
              return caches.delete(key);
            }
          })
        );
      })
      .then(() => {
        console.log('[SW] Claiming clients');
        return self.clients.claim();
      })
  );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
  const request = event.request;
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Skip API requests (always fetch from network)
  if (request.url.includes('/api/')) {
    event.respondWith(
      fetch(request)
        .catch(() => {
          return new Response(
            JSON.stringify({ error: 'Offline', message: 'Sin conexion a internet' }),
            { headers: { 'Content-Type': 'application/json' } }
          );
        })
    );
    return;
  }
  
  // Cache-first strategy for static files
  event.respondWith(
    caches.match(request)
      .then((cachedResponse) => {
        if (cachedResponse) {
          return cachedResponse;
        }
        
        // Fetch from network
        return fetch(request)
          .then((networkResponse) => {
            // Clone the response
            const responseClone = networkResponse.clone();
            
            // Cache the new response
            caches.open(DYNAMIC_CACHE)
              .then((cache) => {
                cache.put(request, responseClone);
              });
            
            return networkResponse;
          })
          .catch(() => {
            // Return offline page for navigation requests
            if (request.mode === 'navigate') {
              return caches.match('/');
            }
          });
      })
  );
});

// Push notification event
self.addEventListener('push', (event) => {
  console.log('[SW] Push received');
  
  let data = {
    title: 'DoseClock',
    body: 'Es hora de tu medicamento',
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/icon-72.png'
  };
  
  if (event.data) {
    try {
      data = { ...data, ...event.data.json() };
    } catch (e) {
      data.body = event.data.text();
    }
  }
  
  const options = {
    body: data.body,
    icon: data.icon,
    badge: data.badge,
    vibrate: [200, 100, 200],
    tag: data.tag || 'dose-notification',
    requireInteraction: true,
    data: data.data || {},
    actions: data.actions || [
      { action: 'confirm', title: 'Confirmar toma' },
      { action: 'dismiss', title: 'Descartar' }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Notification click event
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event.action);
  
  event.notification.close();
  
  const notificationData = event.notification.data || {};
  
  if (event.action === 'confirm' && notificationData.doseId) {
    // Send confirmation to server
    event.waitUntil(
      fetch(`/api/confirmar-toma/${notificationData.doseId}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      .then(() => {
        // Show confirmation notification
        return self.registration.showNotification('DoseClock', {
          body: '¡Toma confirmada!',
          icon: '/static/icons/icon-192.png',
          tag: 'confirmation'
        });
      })
      .catch((error) => {
        console.error('[SW] Confirmation failed:', error);
      })
    );
  } else {
    // Open the app
    event.waitUntil(
      clients.matchAll({ type: 'window', includeUncontrolled: true })
        .then((clientList) => {
          // Focus existing window if available
          for (const client of clientList) {
            if (client.url.includes(self.registration.scope) && 'focus' in client) {
              return client.focus();
            }
          }
          // Open new window
          if (clients.openWindow) {
            return clients.openWindow('/');
          }
        })
    );
  }
});

// Notification close event
self.addEventListener('notificationclose', (event) => {
  console.log('[SW] Notification closed');
});

// Background sync (for offline confirmations)
self.addEventListener('sync', (event) => {
  console.log('[SW] Sync event:', event.tag);
  
  if (event.tag === 'sync-confirmations') {
    event.waitUntil(syncConfirmations());
  }
});

// Sync pending confirmations
async function syncConfirmations() {
  try {
    // Get pending confirmations from IndexedDB
    const db = await openDatabase();
    const pending = await getPendingConfirmations(db);
    
    for (const confirmation of pending) {
      try {
        await fetch(`/api/confirmar-toma/${confirmation.doseId}/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ timestamp: confirmation.timestamp })
        });
        
        // Remove from pending
        await removeConfirmation(db, confirmation.id);
      } catch (error) {
        console.error('[SW] Sync failed for dose:', confirmation.doseId);
      }
    }
  } catch (error) {
    console.error('[SW] Sync failed:', error);
  }
}

// IndexedDB helpers
function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('DoseClockDB', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains('pendingConfirmations')) {
        db.createObjectStore('pendingConfirmations', { keyPath: 'id', autoIncrement: true });
      }
    };
  });
}

function getPendingConfirmations(db) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction('pendingConfirmations', 'readonly');
    const store = transaction.objectStore('pendingConfirmations');
    const request = store.getAll();
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
  });
}

function removeConfirmation(db, id) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction('pendingConfirmations', 'readwrite');
    const store = transaction.objectStore('pendingConfirmations');
    const request = store.delete(id);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
}

console.log('[SW] Service Worker loaded');

