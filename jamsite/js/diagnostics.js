(function() {
  function Diagnostics(container, indexIdMap) {
    var songCount = Array.isArray(indexIdMap) ? indexIdMap.length : Object.keys(indexIdMap).length;
    var currentSiteVersion = '\u2014';
    var currentPageSource = '\u2014';
    var currentCachedCount = '\u2014';

    function render() {
      var rows = [
        ['Songs', songCount],
        ['Site version', currentSiteVersion],
        ['Page source', currentPageSource],
        ['Cached PDFs', currentCachedCount],
      ];
      var html = '<div class="diagnostics-label">Diagnostics</div><dl class="diagnostics-list">';
      for (var i = 0; i < rows.length; i++) {
        html += '<dt>' + rows[i][0] + '</dt><dd>' + rows[i][1] + '</dd>';
      }
      html += '</dl>';
      container.innerHTML = html;
    }

    render();

    // Page source from navigation timing (sync)
    try {
      var nav = performance.getEntriesByType('navigation')[0];
      if (nav) {
        currentPageSource = nav.transferSize === 0 ? 'Cache' : 'Network';
      }
    } catch(e) {}

    // Site version from SW cache name (async)
    var siteVersionPromise = typeof caches !== 'undefined'
      ? caches.keys().then(function(keys) {
          var staticKey = keys.find(function(k) { return k.startsWith('jamsite-static-'); });
          return staticKey ? staticKey.replace('jamsite-static-', '') : '\u2014';
        }).catch(function() { return '\u2014'; })
      : Promise.resolve('\u2014');

    function getCachedCount() {
      return new Promise(function(resolve) {
        var done = false;
        var timer = setTimeout(function() {
          if (!done) { done = true; resolve('\u2014'); }
        }, 3000);

        try {
          var req = indexedDB.open('jamsite_offline', 1);
          req.onupgradeneeded = function(e) {
            var upgradeDb = e.target.result;
            if (!upgradeDb.objectStoreNames.contains('songs')) {
              upgradeDb.createObjectStore('songs', { keyPath: 'uuid' });
            }
          };
          req.onsuccess = function() {
            var db = req.result;
            db.onversionchange = function() { db.close(); };
            if (done) { db.close(); return; }
            try {
              var tx = db.transaction('songs', 'readonly');
              var countReq = tx.objectStore('songs').count();
              countReq.onsuccess = function() {
                db.close();
                if (!done) { done = true; clearTimeout(timer); resolve(countReq.result + ' / ' + songCount); }
              };
              countReq.onerror = function() {
                db.close();
                if (!done) { done = true; clearTimeout(timer); resolve('\u2014'); }
              };
            } catch(e) {
              db.close();
              if (!done) { done = true; clearTimeout(timer); resolve('\u2014'); }
            }
          };
          req.onerror = function() {
            if (!done) { done = true; clearTimeout(timer); resolve('\u2014'); }
          };
        } catch(e) {
          if (!done) { done = true; clearTimeout(timer); resolve('\u2014'); }
        }
      });
    }

    Promise.all([siteVersionPromise, getCachedCount()]).then(function(results) {
      currentSiteVersion = results[0];
      currentCachedCount = results[1];
      render();
    });

    // Public method to refresh the cached PDF count
    this.refreshCachedCount = function() {
      getCachedCount().then(function(count) {
        currentCachedCount = count;
        render();
      });
    };
  }

  window.Diagnostics = Diagnostics;
})();
