document.addEventListener('DOMContentLoaded', function() {
  const menuToggle = document.getElementById('side-menu-toggle');
  const sideMenu = document.getElementById('side-menu');
  const overlay = document.getElementById('side-menu-overlay');
  const offlineEnabled = document.getElementById('offline-enabled');
  const offlineStatusText = document.getElementById('offline-status-text');
  const offlineSyncNow = document.getElementById('offline-sync-now');
  const offlineProgress = document.getElementById('offline-progress');
  const progressBarFill = offlineProgress.querySelector('.progress-bar-fill');
  const progressBarText = offlineProgress.querySelector('.progress-bar-text');

  // Initialize offline toggle state
  offlineEnabled.checked = window.offlinePreferences.isEnabled();

  function toggleMenu() {
    sideMenu.classList.toggle('open');
    overlay.classList.toggle('visible');
    document.body.style.overflow = sideMenu.classList.contains('open') ? 'hidden' : '';
  }

  menuToggle.addEventListener('click', toggleMenu);
  overlay.addEventListener('click', toggleMenu);

  // Close menu when clicking a link
  const menuLinks = sideMenu.getElementsByClassName('side-menu-link');
  Array.from(menuLinks).forEach(link => {
    link.addEventListener('click', () => {
      if (sideMenu.classList.contains('open')) {
        toggleMenu();
      }
    });
  });

  // Handle offline toggle
  offlineEnabled.addEventListener('change', function() {
    const enabled = this.checked;
    window.offlinePreferences.setEnabled(enabled);
    
    if (enabled) {
      // Don't show the sync button immediately - it will be shown when we reach the "downloaded" state
      offlineSyncNow.style.display = 'none';
      syncWorker.postMessage({ type: 'START' });
    } else {
      offlineSyncNow.style.display = 'none';
      offlineProgress.style.display = 'none';
      syncWorker.postMessage({ type: 'STOP' });
    }
  });

  // Handle sync now button
  offlineSyncNow.addEventListener('click', function() {
    syncWorker.postMessage({ type: 'SYNC' });
  });

  // Handle worker messages
  syncWorker.onmessage = function(event) {
    const { type, status, data } = event.data;
    
    if (type === 'progress') {
      switch (status) {
        case 'checking':
          offlineStatusText.textContent = 'Checking for updates...';
          offlineProgress.style.display = 'none';
          offlineSyncNow.style.display = 'none';
          break;
          
        case 'downloading':
          offlineStatusText.textContent = data.message;
          offlineProgress.style.display = 'block';
          offlineSyncNow.style.display = 'none';
          const percent = (data.current / data.total) * 100;
          progressBarFill.style.width = `${percent}%`;
          progressBarText.textContent = `${data.current}/${data.total} files`;
          break;
          
        case 'cleaning':
          offlineStatusText.textContent = 'Cleaning up old files...';
          offlineProgress.style.display = 'none';
          offlineSyncNow.style.display = 'none';
          break;
          
        case 'downloaded':
          offlineStatusText.textContent = 'All files are up to date';
          offlineProgress.style.display = 'none';
          // Only show the sync button when in the downloaded state and offline is enabled
          if (offlineEnabled.checked) {
            offlineSyncNow.style.display = 'block';
          }
          break;
          
        case 'error':
          offlineStatusText.textContent = 'An error occurred during sync';
          offlineProgress.style.display = 'none';
          offlineSyncNow.style.display = 'none';
          break;
          
        case 'cleared':
          offlineStatusText.textContent = 'Offline storage cleared';
          offlineProgress.style.display = 'none';
          offlineSyncNow.style.display = 'none';
          break;
      }
    }
  };
}); 