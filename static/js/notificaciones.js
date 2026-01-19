/**
 * DoseClock - Notifications Module
 * Handles browser notifications and push notifications
 */

// Notification state
let notificationPermission = 'default';
let notificationCheckInterval = null;

/**
 * Initialize notifications system
 */
function initializeNotifications() {
  // Check if notifications are supported
  if (!('Notification' in window)) {
    console.log('Este navegador no soporta notificaciones');
    return;
  }
  
  // Get current permission status
  notificationPermission = Notification.permission;
  
  // Request permission if not granted
  if (notificationPermission === 'default') {
    requestNotificationPermission();
  }
  
  // Start checking for notifications
  startNotificationChecker();
  
  // Register service worker if supported
  registerServiceWorker();
}

/**
 * Request notification permission from user
 */
async function requestNotificationPermission() {
  try {
    const permission = await Notification.requestPermission();
    notificationPermission = permission;
    
    if (permission === 'granted') {
      console.log('Notificaciones activadas');
      showNotification('DoseClock', {
        body: '¡Notificaciones activadas! Te recordaremos tus medicamentos.',
        icon: '/static/icons/icon-192.png',
        tag: 'welcome'
      });
    }
  } catch (error) {
    console.error('Error requesting notification permission:', error);
  }
}

/**
 * Register Service Worker for background notifications
 */
async function registerServiceWorker() {
  if ('serviceWorker' in navigator) {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js');
      console.log('Service Worker registrado:', registration.scope);
    } catch (error) {
      console.error('Error registrando Service Worker:', error);
    }
  }
}

/**
 * Show a notification
 * @param {string} title - Notification title
 * @param {object} options - Notification options
 */
function showNotification(title, options = {}) {
  if (notificationPermission !== 'granted') {
    console.log('Notificaciones no permitidas');
    return;
  }
  
  const defaultOptions = {
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/icon-72.png',
    vibrate: [200, 100, 200],
    requireInteraction: true,
    silent: false
  };
  
  const notificationOptions = { ...defaultOptions, ...options };
  
  // Use Service Worker notification if available
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
    navigator.serviceWorker.ready.then(registration => {
      registration.showNotification(title, notificationOptions);
    });
  } else {
    // Fallback to regular notification
    const notification = new Notification(title, notificationOptions);
    
    notification.onclick = function(event) {
      event.preventDefault();
      window.focus();
      
      if (options.data && options.data.doseId) {
        // Navigate to confirm dose
        window.location.href = `/tomas/${options.data.doseId}/confirmar/`;
      }
      
      notification.close();
    };
  }
}

/**
 * Show dose reminder notification
 * @param {object} doseData - Dose information
 */
function showDoseReminder(doseData) {
  const title = `¡Es hora de tomar ${doseData.medicationName}!`;
  const options = {
    body: 'Toca para confirmar la toma de tu medicamento.',
    icon: '/static/icons/icon-192.png',
    tag: `dose-${doseData.doseId}`,
    data: {
      doseId: doseData.doseId,
      type: 'dose_reminder'
    },
    actions: [
      { action: 'confirm', title: 'Confirmar' },
      { action: 'snooze', title: 'Recordar en 5 min' }
    ]
  };
  
  showNotification(title, options);
}

/**
 * Show advance reminder notification
 * @param {object} doseData - Dose information
 */
function showAdvanceReminder(doseData) {
  const title = `Recordatorio: ${doseData.medicationName}`;
  const options = {
    body: `Tu medicamento esta programado en 5 minutos.`,
    icon: '/static/icons/icon-192.png',
    tag: `reminder-${doseData.doseId}`,
    data: {
      doseId: doseData.doseId,
      type: 'advance_reminder'
    }
  };
  
  showNotification(title, options);
}

/**
 * Start the notification checker interval
 */
function startNotificationChecker() {
  // Check every 30 seconds
  notificationCheckInterval = setInterval(checkPendingNotifications, 30000);
  
  // Also check immediately
  checkPendingNotifications();
}

/**
 * Stop the notification checker
 */
function stopNotificationChecker() {
  if (notificationCheckInterval) {
    clearInterval(notificationCheckInterval);
    notificationCheckInterval = null;
  }
}

/**
 * Check for pending notifications from API
 */
async function checkPendingNotifications() {
  // Check if notifications are enabled
  const notificationsEnabled = localStorage.getItem('doseclock_notifications') !== 'false';
  
  if (!notificationsEnabled || notificationPermission !== 'granted') {
    return;
  }
  
  try {
    const response = await fetch('/api/notificaciones-pendientes/');
    const data = await response.json();
    
    if (data.notifications && data.notifications.length > 0) {
      data.notifications.forEach(notification => {
        // Only show if within 1 minute of scheduled time
        if (notification.minutes_until <= 1 && notification.minutes_until >= 0) {
          if (notification.type === 'principal') {
            showDoseReminder({
              doseId: notification.id,
              medicationName: notification.medication
            });
          } else if (notification.type === 'recordatorio') {
            showAdvanceReminder({
              doseId: notification.id,
              medicationName: notification.medication
            });
          }
        }
      });
    }
  } catch (error) {
    console.error('Error checking notifications:', error);
  }
}

/**
 * Schedule a local notification
 * @param {string} title - Notification title
 * @param {object} options - Notification options
 * @param {Date} scheduledTime - When to show the notification
 */
function scheduleNotification(title, options, scheduledTime) {
  const now = new Date();
  const delay = scheduledTime - now;
  
  if (delay <= 0) {
    // Show immediately if time has passed
    showNotification(title, options);
  } else {
    // Schedule for later
    setTimeout(() => {
      showNotification(title, options);
    }, delay);
  }
}

/**
 * Cancel a scheduled notification by tag
 * @param {string} tag - Notification tag
 */
async function cancelNotification(tag) {
  if ('serviceWorker' in navigator) {
    const registration = await navigator.serviceWorker.ready;
    const notifications = await registration.getNotifications({ tag });
    
    notifications.forEach(notification => {
      notification.close();
    });
  }
}

/**
 * Get notification status
 * @returns {object} Notification status info
 */
function getNotificationStatus() {
  return {
    supported: 'Notification' in window,
    permission: notificationPermission,
    enabled: localStorage.getItem('doseclock_notifications') !== 'false',
    soundEnabled: localStorage.getItem('doseclock_sound') !== 'false'
  };
}

/**
 * Toggle notifications on/off
 * @param {boolean} enabled - Whether to enable notifications
 */
function toggleNotifications(enabled) {
  localStorage.setItem('doseclock_notifications', enabled.toString());
  
  if (enabled && notificationPermission === 'default') {
    requestNotificationPermission();
  }
}

/**
 * Toggle notification sound on/off
 * @param {boolean} enabled - Whether to enable sound
 */
function toggleNotificationSound(enabled) {
  localStorage.setItem('doseclock_sound', enabled.toString());
}

// Export functions for global use
window.DoseClockNotifications = {
  initialize: initializeNotifications,
  requestPermission: requestNotificationPermission,
  show: showNotification,
  showDoseReminder: showDoseReminder,
  showAdvanceReminder: showAdvanceReminder,
  schedule: scheduleNotification,
  cancel: cancelNotification,
  getStatus: getNotificationStatus,
  toggle: toggleNotifications,
  toggleSound: toggleNotificationSound,
  startChecker: startNotificationChecker,
  stopChecker: stopNotificationChecker
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initializeNotifications);

// Cleanup on page unload
window.addEventListener('beforeunload', stopNotificationChecker);
