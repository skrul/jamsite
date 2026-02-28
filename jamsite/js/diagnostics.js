(function() {
  function Diagnostics(container, indexIdMap) {
    var songCount = Array.isArray(indexIdMap) ? indexIdMap.length : Object.keys(indexIdMap).length;

    // Render synchronously with placeholders so something always shows
    function render(siteVersion, pageSource, cachedCount) {
      var rows = [
        ['Songs', songCount],
        ['Site version', siteVersion],
        ['Page source', pageSource],
        ['Cached PDFs', cachedCount],
      ];
      var html = '<div class="diagnostics-label">Diagnostics</div><dl class="diagnostics-list">';
      for (var i = 0; i < rows.length; i++) {
        html += '<dt>' + rows[i][0] + '</dt><dd>' + rows[i][1] + '</dd>';
      }
      html += '</dl>';
      container.innerHTML = html;
    }

    render('\u2014', '\u2014', '\u2014');

    // Page source from navigation timing (sync)
    var pageSource = '\u2014';
    try {
      var nav = performance.getEntriesByType('navigation')[0];
      if (nav) {
        pageSource = nav.transferSize === 0 ? 'Cache' : 'Network';
      }
    } catch(e) {}

    // Site version from SW cache name (async)
    var siteVersionPromise = caches.keys().then(function(keys) {
      var staticKey = keys.find(function(k) { return k.startsWith('jamsite-static-'); });
      return staticKey ? staticKey.replace('jamsite-static-', '') : '\u2014';
    }).catch(function() { return '\u2014'; });

    // Cached PDF count from IndexedDB (async, with timeout)
    var idbPromise = new Promise(function(resolve) {
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
          // If a deleteDatabase or version upgrade arrives, close immediately so it can proceed
          db.onversionchange = function() { db.close(); };
          if (done) { db.close(); return; }  // timeout already fired — close and bail
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

    Promise.all([siteVersionPromise, idbPromise]).then(function(results) {
      render(results[0], pageSource, results[1]);
    });
  }

  window.Diagnostics = Diagnostics;
})();
