(function() {
  function SongTable(table) {
    this.init(table);
  }

  SongTable.prototype = {
    init: function(table) {
      var that = this;
      that.table = table;
      this.touchTimer = null;
      this.touchTr = null;
      this.uuidToRow = null;
      this.searchResults = null;
      this.sortColumn = 'title';
      this.rows = []

      for (var i = 0; i < this.table.tBodies[0].rows.length; i++) {
        this.rows.push(this.table.tBodies[0].rows[i]);
      }
      
      // Clear any selected rows when the page is loaded
      // This fixes the issue with rows remaining highlighted after using the back button
      this.clearRowSelection();
      
      // Also clear selection when the page becomes visible again (e.g., when returning from PDF)
      document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') {
          that.clearRowSelection();
        }
      });

      table.addEventListener(
        'touchstart',
        function(e) {
          // Check if the touch is on the song action button or its popover
          if (e.target.closest('.song-actions')) {
            return; // Don't trigger the touch behavior
          }
          
          var tr = that._getTr(e);
          that.touchTr = tr;
          that.touchTimer = setTimeout(function() { that.touchTimerFired(); }, 200);
        },
        false
      );

      table.addEventListener(
        'touchend',
        function(e) {
          // Check if the touch is on the song action button or its popover
          if (e.target.closest('.song-actions')) {
            return; // Don't trigger the touch behavior
          }
          
          var tr = that.touchTr;
          if (tr) {
            tr.classList.add('selected');
            window.location = tr.getAttribute('data-download-link');
          }
          that.touchTr = null;
        },
        false
      );

      table.addEventListener(
        'touchmove',
        function(e) {
          that.cancelTouch();
        },
        false
      );

      table.addEventListener(
        'touchcancel',
        function(e) {
          that.cancelTouch();
        },
        false
      );

      table.addEventListener(
        'click',
        function(e) {
          // Check if the click is on the song action button or its popover
          if (e.target.closest('.song-actions')) {
            return; // Don't trigger the row click behavior
          }
          
          var tr = that._getTr(e);
          if (!mobileAndTabletcheck()) {
            window.open(tr.getAttribute('data-view-link'), '_blank');
          }
        },
        false
      );

    },

    touchTimerFired: function() {
      if (this.touchTr) {
        this.touchTr.classList.add('selected');
      }
    },

    cancelTouch: function() {
      this.touchTr = null;
      if (this.touchTimer) {
        clearTimeout(this.touchTimer);
        this.touchTimer = null;
      }
      this.clearRowSelection();
    },

    clearRowSelection: function() {
      for (var i = 0; i < this.table.tBodies[0].rows.length; i++) {
        var row = this.table.tBodies[0].rows[i];
        row.classList.remove('selected');
      }
    },

    sort: function(column) {
      //this._getNavItem(this.sortColumn).classList.remove('selected');
      this.sortColumn = column;
      //this._getNavItem(this.sortColumn).classList.add('selected');
      this.refreshTable();
    },

    refreshTable: function() {
      var toKey;
      if (this.sortColumn == 'title') {
        toKey = function(c) { return [c[0], c[1], c[2]]; }
      } else if (this.sortColumn == 'artist') {
        toKey = function(c) { return [c[1], c[0], c[2]]; }
      } else {
        toKey = function(c) { return [c[2], c[1], c[0]]; }
      }

      var get_keys_for_row = function(row) {
        var get_cell_value = function(idx) {
          return row.cells[idx].getAttribute('data-sort') || row.cells[idx].textContent;
        }
        return toKey([
          get_cell_value(0),
          get_cell_value(1),
          get_cell_value(2)
        ]);
      }

      this.rows.sort(function(a, b) {
        a_values = get_keys_for_row(a);
        b_values = get_keys_for_row(b);
        return a_values[0].localeCompare(b_values[0]) ||
          a_values[1].localeCompare(b_values[1]) ||
          a_values[2].localeCompare(b_values[2]);
      });

      var tableBody = this.table.tBodies[0];
      for (var i = 0; i < this.rows.length; i++) {
        var row = this.rows[i];
        var appendRow = false;
        if (this.searchResults) {
          appendRow = this.searchResults.has(row.id);
        } else {
          appendRow = true;
        }

        if (appendRow) {
          tableBody.appendChild(row);
        } else {
          if (row.parentNode == tableBody) {
            tableBody.removeChild(row);
          }
        }
      }

      window.scrollTo(0, 0);
    },

    showRows: function(uuids) {
      this.searchResults = new Set(uuids);
      this.refreshTable();
    },

    showAllRows: function() {
      this.searchResults = null;
      this.refreshTable();
    },

    _getTr: function(e) {
      var target = e.target;
      while (target.tagName != 'TR') {
        target = target.parentElement;
      }
      return target;
    },

    _getUuidToRow: function() {
      for (var i = 0; i < this.table.tBodies[0].rows.length; i++) {
      }
    }
  }

  window.SongTable = SongTable;
})();
