/**
 * OceanTrace Main Application Controller & Router
 */
const App = {
  currentView: 'monitor',

  init() {
    this.renderLayout();
    this.startClock();
    this.navigateTo('monitor');
    this.bindGlobalEvents();
    this.checkBackendHealth();
  },

  async checkBackendHealth() {
    const pill = document.getElementById('backend-status-pill');
    if (!pill) return;

    try {
      const health = await OceanTraceApi.checkHealth();
      if (health.status === 'healthy' && health.model_loaded) {
        pill.className = 'status-pill live';
        pill.innerHTML = `<span class="pulse-dot"></span> Online (${health.device.toUpperCase()})`;
      } else if (health.status === 'healthy') {
        pill.className = 'status-pill';
        pill.style.background = 'var(--ivory-400)';
        pill.style.color = 'var(--blue-900)';
        pill.innerHTML = `Model Offline`;
      } else {
        pill.className = 'status-pill coral';
        pill.innerHTML = `Backend Disconnected`;
      }
    } catch (e) {
      pill.className = 'status-pill coral';
      pill.innerHTML = `Offline`;
    }
  },

  renderLayout() {
    const mainEl = document.getElementById('view-viewport');
    mainEl.innerHTML = `
      <div id="view-monitor" class="view-container"></div>
      <div id="view-forensics" class="view-container"></div>
      <div id="view-attribution" class="view-container"></div>
      ${DossierModalComponent.render()}
    `;
    DossierModalComponent.bindEvents();
  },

  navigateTo(viewName) {
    this.currentView = viewName;

    // Update Tab Buttons
    document.querySelectorAll('.nav-tab-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.view === viewName);
    });

    // Hide all view containers
    document.querySelectorAll('.view-container').forEach(v => {
      v.classList.remove('active');
    });

    const activeContainer = document.getElementById(`view-${viewName}`);
    if (activeContainer) {
      activeContainer.classList.add('active');

      if (viewName === 'monitor') {
        activeContainer.innerHTML = MonitorComponent.render();
        MonitorComponent.initMap();
        MonitorComponent.bindEvents();
      } else if (viewName === 'forensics') {
        activeContainer.innerHTML = ForensicsComponent.render();
        ForensicsComponent.initMap();
        ForensicsComponent.bindEvents();
      } else if (viewName === 'attribution') {
        activeContainer.innerHTML = AttributionComponent.render();
        AttributionComponent.initMap();
        AttributionComponent.bindEvents();
      }
    }

    // Refresh Lucide Icons
    if (window.lucide) {
      lucide.createIcons();
    }
  },

  startClock() {
    const updateTime = () => {
      const now = new Date();
      const utcString = now.toUTCString().replace('GMT', 'UTC');
      const timeEl = document.getElementById('utc-clock');
      if (timeEl) {
        timeEl.textContent = utcString.substring(17, 25) + ' UTC';
      }
    };
    updateTime();
    setInterval(updateTime, 1000);
  },

  bindGlobalEvents() {
    document.querySelectorAll('.nav-tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const view = e.currentTarget.dataset.view;
        this.navigateTo(view);
      });
    });
  }
};

// Boot application on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  App.init();
});
