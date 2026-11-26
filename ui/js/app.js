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
