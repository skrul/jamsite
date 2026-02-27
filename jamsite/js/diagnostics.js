(function() {
  async function Diagnostics(container, indexIdMap) {
    var songCount = Object.keys(indexIdMap).length;

    // Site version from SW cache name
    var siteVersion = '—';
    try {
      var keys = await caches.keys();
      var staticKey = keys.find(function(k) { return k.startsWith('jamsite-static-'); });
      if (staticKey) {
        siteVersion = staticKey.replace('jamsite-static-', '');
      }
    } catch(e) {}

    // Page source from navigation timing
    var pageSource = '—';
    try {
      var nav = performance.getEntriesByType('navigation')[0];
      if (nav) {
        pageSource = nav.transferSize === 0 ? 'Cache' : 'Network';
      }
    } catch(e) {}

    // Cached PDF count from IndexedDB
    var cachedCount = '—';
    try {
      var db = await new Promise(function(resolve) {
        var req = indexedDB.open('jamsite_offline', 1);
        req.onsuccess = function() { resolve(req.result); };
        req.onerror = function() { resolve(null); };
        req.onupgradeneeded = function(e) { e.target.transaction.abort(); resolve(null); };
      });
      if (db) {
        var count = await new Promise(function(resolve) {
          var tx = db.transaction('songs', 'readonly');
          var req = tx.objectStore('songs').count();
          req.onsuccess = function() { resolve(req.result); };
          req.onerror = function() { resolve(0); };
        });
        db.close();
        cachedCount = count + ' / ' + songCount;
      }
    } catch(e) {}

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

  window.Diagnostics = Diagnostics;
})();
