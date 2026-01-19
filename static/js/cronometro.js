/**
 * DoseClock - Countdown Timer Module
 * Handles countdown displays and updates using absolute time synchronization
 */

// Store countdown intervals
const countdownIntervals = new Map();

// Server time offset (difference between server and client time in ms)
let serverTimeOffset = 0;

/**
 * Calculate the offset between server time and client time
 * This corrects for timezone differences and clock drift
 */
function calculateServerOffset() {
  const serverTimeMeta = document.querySelector('meta[name="server-time"]');
  if (serverTimeMeta) {
    const serverTime = new Date(serverTimeMeta.content);
    const clientTime = new Date();
    serverTimeOffset = serverTime.getTime() - clientTime.getTime();
    console.log(`Server time offset: ${serverTimeOffset}ms (${Math.round(serverTimeOffset/1000)}s)`);
  }
}

/**
 * Get the current time adjusted for server offset
 * @returns {Date} Current time synchronized with server
 */
function getSyncedNow() {
  return new Date(Date.now() + serverTimeOffset);
}

/**
 * Initialize all countdowns on the page
 */
function initializeCountdowns() {
  // Calculate server time offset first
  calculateServerOffset();
  
  const countdownElements = document.querySelectorAll('[data-target-time]');
  
  countdownElements.forEach(element => {
    const targetTime = element.dataset.targetTime;
    if (targetTime) {
      startCountdownAbsolute(element, targetTime);
    }
  });
  
  // Fallback for elements with only data-seconds (legacy support)
  const legacyElements = document.querySelectorAll('[data-seconds]:not([data-target-time])');
  legacyElements.forEach(element => {
    const seconds = parseInt(element.dataset.seconds, 10);
    if (!isNaN(seconds)) {
      startCountdown(element, seconds);
    }
  });
}

/**
 * Start a countdown timer using absolute target time
 * @param {HTMLElement} element - The countdown display element
 * @param {string} targetTimeISO - ISO timestamp of the target time
 */
function startCountdownAbsolute(element, targetTimeISO) {
  const elementId = element.id || `countdown-${Date.now()}`;
  element.id = elementId;
  
  // Clear existing interval if any
  if (countdownIntervals.has(elementId)) {
    clearInterval(countdownIntervals.get(elementId));
  }
  
  const targetTime = new Date(targetTimeISO);
  
  // Update function that calculates remaining time from current moment
  function updateFromAbsoluteTime() {
    const now = getSyncedNow();
    const remainingMs = targetTime.getTime() - now.getTime();
    const remainingSeconds = Math.max(0, Math.floor(remainingMs / 1000));
    
    updateCountdownDisplay(element, remainingSeconds);
    
    if (remainingSeconds <= 0) {
      clearInterval(countdownIntervals.get(elementId));
      countdownIntervals.delete(elementId);
      handleCountdownComplete(element);
    }
  }
  
  // Update immediately
  updateFromAbsoluteTime();
  
  // Set interval for updates (every second)
  const intervalId = setInterval(updateFromAbsoluteTime, 1000);
  countdownIntervals.set(elementId, intervalId);
}

/**
 * Start a countdown timer for an element (legacy - uses relative seconds)
 * Prefer startCountdownAbsolute for accurate timing
 * @param {HTMLElement} element - The countdown display element
 * @param {number} initialSeconds - Starting seconds
 */
function startCountdown(element, initialSeconds) {
  // Convert to absolute time and use the accurate method
  const targetTime = new Date(getSyncedNow().getTime() + (initialSeconds * 1000));
  startCountdownAbsolute(element, targetTime.toISOString());
}

/**
 * Update all countdowns (called for manual refresh)
 * With absolute timing, this recalculates from current time
 */
function updateCountdowns() {
  const countdownElements = document.querySelectorAll('[data-target-time]');
  
  countdownElements.forEach(element => {
    const targetTime = element.dataset.targetTime;
    if (targetTime) {
      const target = new Date(targetTime);
      const now = getSyncedNow();
      const remainingMs = target.getTime() - now.getTime();
      const remainingSeconds = Math.max(0, Math.floor(remainingMs / 1000));
      
      updateCountdownDisplay(element, remainingSeconds);
    }
  });
}

/**
 * Update the display of a countdown element
 * @param {HTMLElement} element - The countdown display element
 * @param {number} seconds - Remaining seconds
 */
function updateCountdownDisplay(element, seconds) {
  element.dataset.currentSeconds = seconds;
  
  if (seconds <= 0) {
    element.textContent = '¡Ahora!';
    element.classList.add('urgent');
    element.classList.remove('soon');
    return;
  }
  
  const formatted = formatTime(seconds);
  element.textContent = formatted;
  
  // Update visual state
  if (seconds <= 300) { // 5 minutes or less
    element.classList.add('urgent');
    element.classList.remove('soon');
  } else if (seconds <= 900) { // 15 minutes or less
    element.classList.add('soon');
    element.classList.remove('urgent');
  } else {
    element.classList.remove('urgent', 'soon');
  }
  
  // Update ARIA label
  element.setAttribute('aria-label', `Tiempo restante: ${formatted}`);
}

/**
 * Format seconds into readable time string
 * @param {number} totalSeconds - Total seconds
 * @returns {string} Formatted time string
 */
function formatTime(totalSeconds) {
  if (totalSeconds <= 0) return '¡Ahora!';
  
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  
  const parts = [];
  
  if (hours > 0) {
    parts.push(`${hours}h`);
  }
  
  if (minutes > 0 || hours > 0) {
    parts.push(`${minutes}m`);
  }
  
  if (seconds > 0 || parts.length === 0) {
    parts.push(`${seconds}s`);
  }
  
  return parts.join(' ');
}

/**
 * Handle countdown completion
 * @param {HTMLElement} element - The countdown element that completed
 */
function handleCountdownComplete(element) {
  element.textContent = '¡Ahora!';
  element.classList.add('urgent');
  
  // Find the associated confirm button and enable it
  const card = element.closest('.medication-card');
  if (card) {
    const confirmBtn = card.querySelector('.btn-confirm-dose, button[disabled]');
    if (confirmBtn && confirmBtn.classList.contains('btn-secondary')) {
      confirmBtn.classList.remove('btn-secondary');
      confirmBtn.classList.add('btn-success', 'btn-confirm-dose');
      confirmBtn.disabled = false;
      confirmBtn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Confirmar Toma';
    }
  }
  
  // Play notification sound if enabled
  playNotificationSound();
  
  // Trigger visual notification
  triggerVisualNotification(element);
}

/**
 * Play notification sound
 */
function playNotificationSound() {
  // Check if sound is enabled in config
  const soundEnabled = localStorage.getItem('doseclock_sound') !== 'false';
  
  if (soundEnabled) {
    // Create audio context for notification sound
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      oscillator.frequency.value = 800;
      oscillator.type = 'sine';
      gainNode.gain.value = 0.3;
      
      oscillator.start();
      
      setTimeout(() => {
        oscillator.stop();
      }, 200);
    } catch (e) {
      console.log('Audio not available');
    }
  }
}

/**
 * Trigger visual notification
 * @param {HTMLElement} element - The countdown element
 */
function triggerVisualNotification(element) {
  const card = element.closest('.medication-card');
  if (card) {
    card.classList.add('notification-pulse');
    
    setTimeout(() => {
      card.classList.remove('notification-pulse');
    }, 2000);
  }
}

/**
 * Get time until a specific date
 * @param {string} isoDateString - ISO date string
 * @returns {object} Time breakdown
 */
function getTimeUntil(isoDateString) {
  const targetDate = new Date(isoDateString);
  const now = new Date();
  const diff = targetDate - now;
  
  if (diff <= 0) {
    return {
      totalSeconds: 0,
      hours: 0,
      minutes: 0,
      seconds: 0,
      isPast: true
    };
  }
  
  const totalSeconds = Math.floor(diff / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  
  return {
    totalSeconds,
    hours,
    minutes,
    seconds,
    isPast: false
  };
}

/**
 * Clean up all countdown intervals
 */
function cleanupCountdowns() {
  countdownIntervals.forEach((intervalId, elementId) => {
    clearInterval(intervalId);
  });
  countdownIntervals.clear();
}

// Export functions for global use
window.DoseClockCountdown = {
  initialize: initializeCountdowns,
  start: startCountdown,
  update: updateCountdowns,
  format: formatTime,
  getTimeUntil: getTimeUntil,
  cleanup: cleanupCountdowns
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initializeCountdowns);

// Cleanup on page unload
window.addEventListener('beforeunload', cleanupCountdowns);
