(function() {
  function SongTable(table, nav) {
    this.init(table, nav);
  }

  SongTable.prototype = {
    init: function(table, nav) {
      var that = this;
      that.table = table;
      that.nav = nav;
      this.currentMode = null;

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

    sort: function(type) {
      var toKey;
      if (type == 'title') {
        toKey = function(c) { return [c[0], c[1], c[2]]; }
      } else if (type == 'artist') {
        toKey = function(c) { return [c[1], c[0], c[2]]; }
      } else {
        toKey = function(c) { return [c[2], c[1], c[0]]; }
      }

      var rowData = [];
      for (var i = 0; i < this.table.tBodies[0].rows.length; i++) {
        var row = this.table.tBodies[0].rows[i];
        var cellsValues = [
          row.cells[0].textContent,
          row.cells[1].textContent,
          row.cells[2].textContent
        ];
        rowData.push({
          tr: row,
          key: toKey(cellsValues)
        });
      }

      rowData.sort(function(a, b) {
        return a['key'][0].localeCompare(b['key'][0]) ||
          a['key'][1].localeCompare(b['key'][1]) ||
          a['key'][2].localeCompare(b['key'][2]);
      });

      for (var i = 0; i < rowData.length; i++) {
        this.table.tBodies[0].appendChild(rowData[i]['tr']);
      }

      if (this.currentMode) {
        this._getNavItem(this.currentMode).classList.remove('selected');
      }
      this._getNavItem(type).classList.add('selected');
      this.currentMode = type;
    },

    _getNavItem: function(name) {
      return this.nav.getElementsByClassName(name)[0];
    }
  }

  window.SongTable = SongTable;
})();
