/**
 * DoseClock - Countdown Timer Module
 * Handles countdown displays and updates
 */

// Store countdown intervals
const countdownIntervals = new Map();

/**
 * Initialize all countdowns on the page
 */
function initializeCountdowns() {
  const countdownElements = document.querySelectorAll('[data-seconds]');
  
  countdownElements.forEach(element => {
    const seconds = parseInt(element.dataset.seconds, 10);
    if (!isNaN(seconds)) {
      startCountdown(element, seconds);
    }
  });
}

/**
 * Start a countdown timer for an element
 * @param {HTMLElement} element - The countdown display element
 * @param {number} initialSeconds - Starting seconds
 */
function startCountdown(element, initialSeconds) {
  const elementId = element.id;
  
  // Clear existing interval if any
  if (countdownIntervals.has(elementId)) {
    clearInterval(countdownIntervals.get(elementId));
  }
  
  let remainingSeconds = initialSeconds;
  
  // Update display immediately
  updateCountdownDisplay(element, remainingSeconds);
  
  // Set interval for updates
  const intervalId = setInterval(() => {
    remainingSeconds--;
    
    if (remainingSeconds <= 0) {
      clearInterval(intervalId);
      countdownIntervals.delete(elementId);
      handleCountdownComplete(element);
    } else {
      updateCountdownDisplay(element, remainingSeconds);
    }
  }, 1000);
  
  countdownIntervals.set(elementId, intervalId);
}

/**
 * Update all countdowns (called every second from dashboard)
 */
function updateCountdowns() {
  const countdownElements = document.querySelectorAll('.countdown-display');
  
  countdownElements.forEach(element => {
    const currentSeconds = parseInt(element.dataset.currentSeconds, 10) || 0;
    
    if (currentSeconds > 0) {
      const newSeconds = currentSeconds - 1;
      element.dataset.currentSeconds = newSeconds;
      updateCountdownDisplay(element, newSeconds);
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
