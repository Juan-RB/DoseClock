/**
 * DoseClock - Calendar Module
 * Handles calendar functionality and dose visualization
 */

// Calendar state
let calendar = null;
let currentView = 'dayGridMonth';

/**
 * Initialize calendar with FullCalendar
 * @param {string} elementId - Calendar container element ID
 * @param {string} eventsUrl - URL to fetch events from
 */
function initializeCalendar(elementId, eventsUrl) {
  const calendarEl = document.getElementById(elementId);
  
  if (!calendarEl) {
    console.error('Calendar element not found');
    return;
  }
  
  calendar = new FullCalendar.Calendar(calendarEl, {
    locale: 'es',
    initialView: currentView,
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek'
    },
    buttonText: {
      today: 'Hoy',
      month: 'Mes',
      week: 'Semana',
      day: 'Dia',
      list: 'Lista'
    },
    events: eventsUrl,
    eventClick: handleEventClick,
    eventDidMount: handleEventMount,
    eventTimeFormat: {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    },
    height: 'auto',
    aspectRatio: 1.5,
    nowIndicator: true,
    navLinks: true,
    editable: false,
    selectable: false,
    dayMaxEvents: true,
    moreLinkClick: 'popover'
  });
  
  calendar.render();
}

/**
 * Handle event click
 * @param {object} info - Event info from FullCalendar
 */
function handleEventClick(info) {
  const event = info.event;
  const props = event.extendedProps;
  
  // Build modal content
  const content = `
    <div class="dose-detail">
      <h5>${props.medication}</h5>
      <p><strong>Hora programada:</strong> ${formatEventTime(event.start)}</p>
      <p><strong>Estado:</strong> ${getStatusLabel(props.status)}</p>
      ${props.treatment_id ? `
        <div class="mt-3">
          <a href="/tratamientos/${props.treatment_id}/" class="btn btn-sm btn-outline-primary">
            <i class="bi bi-eye me-1"></i>Ver tratamiento
          </a>
          <a href="/tomas/${event.id}/historial/" class="btn btn-sm btn-outline-secondary">
            <i class="bi bi-clock-history me-1"></i>Historial
          </a>
        </div>
      ` : ''}
    </div>
  `;
  
  // Show in a modal or alert
  showEventModal(props.medication, content);
}

/**
 * Handle event mount (customize event appearance)
 * @param {object} info - Event mount info
 */
function handleEventMount(info) {
  const event = info.event;
  const props = event.extendedProps;
  
  // Add status icon
  const statusIcon = getStatusIcon(props.status);
  if (statusIcon) {
    const iconEl = document.createElement('i');
    iconEl.className = `bi ${statusIcon} me-1`;
    info.el.querySelector('.fc-event-title')?.prepend(iconEl);
  }
  
  // Add tooltip
  info.el.title = `${props.medication} - ${getStatusLabel(props.status)}`;
}

/**
 * Get status label in Spanish
 * @param {string} status - Status code
 * @returns {string} Status label
 */
function getStatusLabel(status) {
  const labels = {
    'confirmada': 'Confirmada a tiempo',
    'tarde': 'Confirmada tarde',
    'no_tomada': 'No tomada',
    'pendiente': 'Pendiente'
  };
  return labels[status] || status;
}

/**
 * Get status icon class
 * @param {string} status - Status code
 * @returns {string} Bootstrap icon class
 */
function getStatusIcon(status) {
  const icons = {
    'confirmada': 'bi-check-circle-fill',
    'tarde': 'bi-exclamation-circle-fill',
    'no_tomada': 'bi-x-circle-fill',
    'pendiente': 'bi-hourglass-split'
  };
  return icons[status] || '';
}

/**
 * Format event time for display
 * @param {Date} date - Date object
 * @returns {string} Formatted time
 */
function formatEventTime(date) {
  return date.toLocaleString('es-CL', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

/**
 * Show event details in a modal
 * @param {string} title - Modal title
 * @param {string} content - Modal body content
 */
function showEventModal(title, content) {
  // Check if Bootstrap modal exists
  let modal = document.getElementById('doseDetailModal');
  
  if (!modal) {
    // Create modal dynamically
    modal = document.createElement('div');
    modal.id = 'doseDetailModal';
    modal.className = 'modal fade';
    modal.setAttribute('tabindex', '-1');
    modal.innerHTML = `
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title"></h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
          </div>
          <div class="modal-body"></div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  }
  
  // Update content
  modal.querySelector('.modal-title').textContent = title;
  modal.querySelector('.modal-body').innerHTML = content;
  
  // Show modal
  const bsModal = new bootstrap.Modal(modal);
  bsModal.show();
}

/**
 * Refresh calendar events
 */
function refreshCalendar() {
  if (calendar) {
    calendar.refetchEvents();
  }
}

/**
 * Go to specific date
 * @param {Date|string} date - Date to navigate to
 */
function goToDate(date) {
  if (calendar) {
    calendar.gotoDate(date);
  }
}

/**
 * Change calendar view
 * @param {string} viewName - View name (dayGridMonth, timeGridWeek, etc.)
 */
function changeView(viewName) {
  if (calendar) {
    calendar.changeView(viewName);
    currentView = viewName;
  }
}

/**
 * Get events for a specific date range
 * @param {Date} start - Start date
 * @param {Date} end - End date
 * @returns {Array} Events in range
 */
function getEventsInRange(start, end) {
  if (!calendar) return [];
  
  return calendar.getEvents().filter(event => {
    return event.start >= start && event.start <= end;
  });
}

/**
 * Add custom event to calendar
 * @param {object} eventData - Event data
 */
function addEvent(eventData) {
  if (calendar) {
    calendar.addEvent(eventData);
  }
}

/**
 * Remove event from calendar
 * @param {string} eventId - Event ID to remove
 */
function removeEvent(eventId) {
  if (calendar) {
    const event = calendar.getEventById(eventId);
    if (event) {
      event.remove();
    }
  }
}

/**
 * Destroy calendar instance
 */
function destroyCalendar() {
  if (calendar) {
    calendar.destroy();
    calendar = null;
  }
}

// Export functions for global use
window.DoseClockCalendar = {
  initialize: initializeCalendar,
  refresh: refreshCalendar,
  goToDate: goToDate,
  changeView: changeView,
  getEventsInRange: getEventsInRange,
  addEvent: addEvent,
  removeEvent: removeEvent,
  destroy: destroyCalendar
};
