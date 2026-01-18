/**
 * DoseClock - Pillbox Animation Module
 * 3D animated pillbox for advanced visual mode
 */

// Pillbox state
let pillboxData = [];
let animationEnabled = true;

/**
 * Initialize pillbox visualization
 */
function initializePillbox(containerId, doses) {
  const container = document.getElementById(containerId);
  if (!container) {
    console.warn('Pillbox container not found');
    return;
  }

  pillboxData = doses || [];
  renderPillbox(container);

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    animationEnabled = false;
  }
}

/**
 * Render the pillbox visualization
 */
function renderPillbox(container) {
  const today = new Date();
  const days = ['Dom', 'Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab'];

  let html = `
    <div class="pillbox-wrapper">
      <h3 class="pillbox-title mb-3">
        <i class="bi bi-grid-3x3-gap me-2"></i>
        Pastillero Semanal
      </h3>
      <div class="pillbox">
  `;

  for (let i = 0; i < 7; i++) {
    const date = new Date(today);
    date.setDate(today.getDate() + i);
    const dayName = days[date.getDay()];
    const dayNum = date.getDate();
    const isToday = i === 0;

    html += `
      <div class="pillbox-day ${isToday ? 'today' : ''}" data-date="${date.toISOString().split('T')[0]}">
        <div class="day-header">
          <span class="day-name">${dayName}</span>
          <span class="day-num">${dayNum}</span>
        </div>
        <div class="day-compartments">
          ${renderDayCompartments(date)}
        </div>
      </div>
    `;
  }

  html += '</div></div>';
  container.innerHTML = html;
  setupPillboxInteractions(container);
}

/**
 * Render compartments for a single day
 */
function renderDayCompartments(date) {
  const dateStr = date.toISOString().split('T')[0];
  const dayDoses = pillboxData.filter(dose => {
    if (!dose.scheduledTime) return false;
    const doseDate = new Date(dose.scheduledTime).toISOString().split('T')[0];
    return doseDate === dateStr;
  });

  const slots = [
    { name: 'Manana', icon: 'sunrise', hours: [6, 7, 8, 9, 10, 11] },
    { name: 'Tarde', icon: 'sun', hours: [12, 13, 14, 15, 16, 17] },
    { name: 'Noche', icon: 'sunset', hours: [18, 19, 20, 21, 22, 23] },
    { name: 'Madrugada', icon: 'moon-stars', hours: [0, 1, 2, 3, 4, 5] }
  ];

  let html = '';

  slots.forEach(slot => {
    const slotDoses = dayDoses.filter(dose => {
      const hour = new Date(dose.scheduledTime).getHours();
      return slot.hours.includes(hour);
    });

    const hasDoses = slotDoses.length > 0;
    const allTaken = hasDoses && slotDoses.every(d => d.status === 'confirmada' || d.status === 'tarde');

    html += `
      <div class="pill-compartment ${hasDoses ? 'has-doses' : ''} ${allTaken ? 'taken' : ''}"
           data-slot="${slot.name}"
           title="${slot.name}: ${slotDoses.length} dosis">
        <i class="bi bi-${slot.icon} slot-icon" aria-hidden="true"></i>
        <div class="pills-container">
          ${slotDoses.map(dose => renderPill(dose)).join('')}
        </div>
        ${hasDoses ? `<span class="dose-count">${slotDoses.length}</span>` : ''}
      </div>
    `;
  });

  return html;
}

/**
 * Render a single pill
 */
function renderPill(dose) {
  const colorClass = getPillColorClass(dose.medicationColor);
  const statusClass = getPillStatusClass(dose.status);

  return `
    <div class="pill-3d ${colorClass} ${statusClass}"
         data-dose-id="${dose.id}"
         data-medication="${dose.medicationName || 'Medicamento'}"
         title="${dose.medicationName || 'Medicamento'} - ${formatPillTime(dose.scheduledTime)}"
         role="button"
         tabindex="0">
    </div>
  `;
}

function getPillColorClass(color) {
  if (!color) return 'pill-color-1';
  const colorMap = {
    '#667eea': 'pill-color-1',
    '#4facfe': 'pill-color-2',
    '#fa709a': 'pill-color-3',
    '#28a745': 'pill-color-4',
    '#fd7e14': 'pill-color-5'
  };
  return colorMap[color?.toLowerCase()] || 'pill-color-1';
}

function getPillStatusClass(status) {
  const statusMap = {
    'confirmada': 'taken',
    'tarde': 'taken-late',
    'no_tomada': 'missed',
    'pendiente': 'pending'
  };
  return statusMap[status] || 'pending';
}

function formatPillTime(isoTime) {
  if (!isoTime) return '--:--';
  const date = new Date(isoTime);
  return date.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' });
}

function setupPillboxInteractions(container) {
  container.querySelectorAll('.pill-compartment').forEach(compartment => {
    compartment.addEventListener('click', handleCompartmentClick);
  });

  container.querySelectorAll('.pill-3d').forEach(pill => {
    pill.addEventListener('click', handlePillClick);
  });
}

function handleCompartmentClick(event) {
  event.currentTarget.classList.toggle('expanded');
}

function handlePillClick(event) {
  event.stopPropagation();
  const pill = event.currentTarget;
  const doseId = pill.dataset.doseId;

  if (!pill.classList.contains('taken') && !pill.classList.contains('missed')) {
    animatePillTaken(pill);
    if (window.confirmDoseFromPillbox) {
      window.confirmDoseFromPillbox(doseId);
    }
  }
}

function animatePillTaken(pill) {
  if (!animationEnabled) {
    pill.classList.add('taken');
    return;
  }
  pill.classList.add('pill-taken-animation');
  pill.addEventListener('animationend', () => {
    pill.classList.remove('pill-taken-animation');
    pill.classList.add('taken');
  }, { once: true });
}

function updatePillbox(doses) {
  pillboxData = doses || [];
  const container = document.getElementById('pillbox-container');
  if (container) renderPillbox(container);
}

function loadPillboxData() {
  fetch('/api/proximas-tomas/')
    .then(response => response.json())
    .then(data => {
      if (data.doses) {
        const formattedDoses = data.doses.map(d => ({
          id: d.dose_id,
          scheduledTime: d.scheduled_time,
          medicationName: d.medication_name,
          medicationColor: d.medication_color,
          status: d.status,
          canConfirm: d.can_confirm
        }));
        updatePillbox(formattedDoses);
      }
    })
    .catch(err => {
      console.warn('Could not load pillbox data:', err);
      // Show empty state
      const container = document.getElementById('pillbox-container');
      if (container) {
        updatePillbox([]);
      }
    });
}

document.addEventListener('DOMContentLoaded', function() {
  const container = document.getElementById('pillbox-container');
  if (container) loadPillboxData();
});

window.DoseClockPillbox = {
  initialize: initializePillbox,
  update: updatePillbox,
  load: loadPillboxData
};
