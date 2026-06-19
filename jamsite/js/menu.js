class Menu {
  constructor(document, syncWorker, diagnostics) {
    this.document = document;
    this.syncWorker = syncWorker;
    this.diagnostics = diagnostics;
    
    // Cache DOM elements
    this.menuToggle = document.getElementById('side-menu-toggle');
    this.sideMenu = document.getElementById('side-menu');
    this.overlay = document.getElementById('side-menu-overlay');
    this.offlineEnabled = document.getElementById('offline-enabled');
    this.offlineStatusText = document.getElementById('offline-status-text');
    this.offlineSyncNow = document.getElementById('offline-sync-now');
    this.offlineProgress = document.getElementById('offline-progress');
    this.progressBarFill = this.offlineProgress.querySelector('.progress-bar-fill');
    this.progressBarText = this.offlineProgress.querySelector('.progress-bar-text');
    
    // Theme toggle
    this.themeToggle = document.getElementById('theme-toggle');

    // Initialize toggle states
    this.offlineEnabled.checked = window.offlinePreferences.isEnabled();

    // Bind event handlers
    this.toggleMenu = this.toggleMenu.bind(this);
    this.handleOfflineToggle = this.handleOfflineToggle.bind(this);
    this.handleSyncNow = this.handleSyncNow.bind(this);
    this.handleWorkerMessage = this.handleWorkerMessage.bind(this);

    // Initialize theme
    this.initTheme();

    // Initialize event listeners
    this.initializeEventListeners();
  }
  
  toggleMenu() {
    this.sideMenu.classList.toggle('open');
    this.overlay.classList.toggle('visible');
    this.document.body.style.overflow = this.sideMenu.classList.contains('open') ? 'hidden' : '';
  }
  
  initTheme() {
    this.themePreference = localStorage.getItem('theme-preference') || 'system';
    this.applyTheme();
    this.highlightThemeButton();

    // Listen for OS color scheme changes
    this.darkMediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    this.darkMediaQuery.addEventListener('change', () => {
      if (this.themePreference === 'system') {
        this.applyTheme();
      }
    });

    // Click handler on toggle buttons
    this.themeToggle.addEventListener('click', (e) => {
      var btn = e.target.closest('button[data-theme]');
      if (!btn) return;
      this.themePreference = btn.getAttribute('data-theme');
      localStorage.setItem('theme-preference', this.themePreference);
      this.applyTheme();
      this.highlightThemeButton();
    });
  }

  applyTheme() {
    var isDark;
    if (this.themePreference === 'dark') {
      isDark = true;
    } else if (this.themePreference === 'light') {
      isDark = false;
    } else {
      isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
  }

  highlightThemeButton() {
    var buttons = this.themeToggle.querySelectorAll('button[data-theme]');
    for (var i = 0; i < buttons.length; i++) {
      if (buttons[i].getAttribute('data-theme') === this.themePreference) {
        buttons[i].classList.add('active');
      } else {
        buttons[i].classList.remove('active');
      }
    }
  }

  initializeEventListeners() {
    // Menu toggle events
    this.menuToggle.addEventListener('click', this.toggleMenu);
    this.overlay.addEventListener('click', this.toggleMenu);
    
    // Close menu when clicking a link
    const menuLinks = this.sideMenu.getElementsByClassName('side-menu-link');
    Array.from(menuLinks).forEach(link => {
      link.addEventListener('click', () => {
        if (this.sideMenu.classList.contains('open')) {
          this.toggleMenu();
        }
      });
    });
    
    // Offline toggle event
    this.offlineEnabled.addEventListener('change', this.handleOfflineToggle);

    // Sync now button event
    this.offlineSyncNow.addEventListener('click', this.handleSyncNow);

    // Reset app button
    document.getElementById('reset-app').addEventListener('click', this.handleReset.bind(this));
    
    // Worker message event
    this.syncWorker.onmessage = this.handleWorkerMessage;
  }
  
  handleOfflineToggle() {
    const enabled = this.offlineEnabled.checked;
    window.offlinePreferences.setEnabled(enabled);

    if (enabled) {
      // Don't show the sync button immediately - it will be shown when we reach the "downloaded" state
      this.offlineSyncNow.style.display = 'none';
      if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/service_worker.js').catch(err => {
          console.error('Service Worker registration failed:', err);
        });
      }
      this.syncWorker.postMessage({ type: 'START' });
    } else {
      this.offlineSyncNow.style.display = 'none';
      this.offlineProgress.style.display = 'none';
      this.syncWorker.postMessage({ type: 'STOP' });
    }
  }
  
  handleSyncNow() {
    this.syncWorker.postMessage({ type: 'SYNC' });
  }
  
  async handleReset() {
    if (!confirm('This will clear all cached files and reload the page. Continue?')) return;

    try {
      // Clear all caches (static app shell + PDFs)
      const keys = await caches.keys();
      await Promise.all(keys.map(k => caches.delete(k)));
    } catch(e) {}

    try {
      // Unregister service worker
      const registrations = await navigator.serviceWorker.getRegistrations();
      await Promise.all(registrations.map(r => r.unregister()));
    } catch(e) {}

    // Delete IndexedDB
    try {
      await new Promise((resolve, reject) => {
        const req = indexedDB.deleteDatabase('jamsite_offline');
        req.onsuccess = resolve;
        req.onerror = reject;
        req.onblocked = resolve;
      });
    } catch(e) {}

    // Clear local storage
    localStorage.clear();

    // Force fresh resource fetches on next load
    sessionStorage.setItem('cache-bust', Date.now());
    window.location.reload();
  }

  handleWorkerMessage(event) {
    const { type, status, data } = event.data;
    
    if (type === 'progress') {
      switch (status) {
        case 'checking':
          this.offlineStatusText.textContent = 'Checking for updates...';
          this.offlineProgress.style.display = 'none';
          this.offlineSyncNow.style.display = 'none';
          break;
          
        case 'downloading':
          this.offlineStatusText.textContent = data.message;
          this.offlineProgress.style.display = 'block';
          this.offlineSyncNow.style.display = 'none';
          const percent = (data.current / data.total) * 100;
          this.progressBarFill.style.width = `${percent}%`;
          this.progressBarText.textContent = `${data.current}/${data.total} files`;
          break;
          
        case 'cleaning':
          this.offlineStatusText.textContent = 'Cleaning up old files...';
          this.offlineProgress.style.display = 'none';
          this.offlineSyncNow.style.display = 'none';
          break;
          
        case 'downloaded':
          this.offlineStatusText.textContent = 'All files are up to date';
          this.offlineProgress.style.display = 'none';
          // Only show the sync button when in the downloaded state and offline is enabled
          if (this.offlineEnabled.checked) {
            this.offlineSyncNow.style.display = 'block';
          }
          this.diagnostics.refreshCachedCount();
          break;
          
        case 'error':
          this.offlineStatusText.textContent = 'An error occurred during sync';
          this.offlineProgress.style.display = 'none';
          this.offlineSyncNow.style.display = 'none';
          break;
          
        case 'cleared':
          this.offlineStatusText.textContent = 'Offline storage cleared';
          this.offlineProgress.style.display = 'none';
          this.offlineSyncNow.style.display = 'none';
          this.diagnostics.refreshCachedCount();
          break;
      }
    }
  }
}
