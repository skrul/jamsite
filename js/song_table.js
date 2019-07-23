(function() {
  function SongTable(table, nav) {
    this.init(table, nav);
  }

  SongTable.prototype = {
    init: function(table, nav) {
      var that = this;
      that.table = table;
      that.nav = nav;
      this.touchTimer = null;
      this.touchTr = null;
      this.uuidToRow = null;
      this.searchResults = null;
      this.sortColumn = 'title';
      this.rows = []

      for (var i = 0; i < this.table.tBodies[0].rows.length; i++) {
        this.rows.push(this.table.tBodies[0].rows[i]);
      }

      table.addEventListener(
        'touchstart',
        function(e) {
          var tr = that._getTr(e);
          that.touchTr = tr;
          that.touchTimer = setTimeout(function() { that.touchTimerFired(); }, 200);
        },
        false
      );

      table.addEventListener(
        'touchend',
        function(e) {
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
          var tr = that._getTr(e);
          if (!mobileAndTabletcheck()) {
            window.location = tr.getAttribute('data-view-link');
          }
        },
        false
      );

      this._getNavItem('title').addEventListener(
        'click',
        function(e) { that.sort('title'); },
        false
      );
      this._getNavItem('artist').addEventListener(
        'click',
        function(e) { that.sort('artist'); },
        false
      );
      this._getNavItem('year').addEventListener(
        'click',
        function(e) { that.sort('year'); },
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
      this._getNavItem(this.sortColumn).classList.remove('selected');
      this.sortColumn = column;
      this._getNavItem(this.sortColumn).classList.add('selected');
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

      var rest = [];
      for (var i = 0; i < this.rows.length; i++) {
        var row = this.rows[i];
        var appendRow = false;
        if (this.searchResults) {
          appendRow = this.searchResults.has(row.id);
        } else {
          appendRow = true;
        }

        if (appendRow) {
          row.style.visibility = "visible";
          this.table.tBodies[0].appendChild(row);
        } else {
          rest.push(row);
        }
      }

      for (var i = 0; i < rest.length; i++) {
        rest[i].style.visibility = "hidden";
        this.table.tBodies[0].appendChild(rest[i]);
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

    _getNavItem: function(name) {
      return this.nav.getElementsByClassName(name)[0];
    },

    _getTr: function(e) {
      return e.target.parentElement;
    },

    _getUuidToRow: function() {
      for (var i = 0; i < this.table.tBodies[0].rows.length; i++) {
      }
    }
  }

  window.SongTable = SongTable;
})();
