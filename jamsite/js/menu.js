class Menu {
  constructor(document, syncWorker) {
    this.document = document;
    this.syncWorker = syncWorker;
    
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
    
    // Initialize offline toggle state
    this.offlineEnabled.checked = window.offlinePreferences.isEnabled();
    
    // Bind event handlers
    this.toggleMenu = this.toggleMenu.bind(this);
    this.handleOfflineToggle = this.handleOfflineToggle.bind(this);
    this.handleSyncNow = this.handleSyncNow.bind(this);
    this.handleWorkerMessage = this.handleWorkerMessage.bind(this);
    
    // Initialize event listeners
    this.initializeEventListeners();
  }
  
  toggleMenu() {
    this.sideMenu.classList.toggle('open');
    this.overlay.classList.toggle('visible');
    this.document.body.style.overflow = this.sideMenu.classList.contains('open') ? 'hidden' : '';
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
    
    // Worker message event
    this.syncWorker.onmessage = this.handleWorkerMessage;
  }
  
  handleOfflineToggle() {
    const enabled = this.offlineEnabled.checked;
    window.offlinePreferences.setEnabled(enabled);
    
    if (enabled) {
      // Don't show the sync button immediately - it will be shown when we reach the "downloaded" state
      this.offlineSyncNow.style.display = 'none';
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
          break;
      }
    }
  }
}
