(function() {
  function Search(searchInput, songTable, indexData, indexIdMap) {
    this.init(searchInput, songTable, indexData, indexIdMap);
  }
  Search.prototype = {
    init: function(searchInput, songTable, indexData, indexIdMap) {
      var that = this;
      that.searchInput = searchInput;
      that.songTable = songTable;
      that.indexData = indexData;
      that.indexIdMap = indexIdMap;

      searchInput.addEventListener(
        'input',
        function(e) {
          setTimeout(function() {
            that.search(e.target.value);
          }, 1);
        },
        false
      );
    },

    search: function(s) {
      if (s == '') {
        this.songTable.showAllRows();
        return;
      }
      var terms = s.toLowerCase().split(/,?\s+/);
      var res = null;
      for (var i = 0; i < terms.length; i++) {
        if (terms[i] == '') {
          continue;
        }
        var ids = new Set(this.searchTerm(terms[i]));
        if (res) {
          res = new Set([...res].filter(x => ids.has(x)))
        } else {
          res = ids;
        }
      }

      var uuids = [];
      if (res) {
        var a = Array.from(res);
        for (var i = 0; i < a.length; i++) {
          uuids.push(this.indexIdMap[a[i]]);
        }
      }
      this.songTable.showRows(uuids);
    },

    searchTerm: function(s) {
      var ids = null;
      var n = this.indexData;
      for (var i = 0; i < s.length; i++) {
        node = n[s[i]];
        if (node) {
          ids = node['i'];
          n = node['c'];
        } else {
          return [];
        }
      }
      return ids;
    }
  }

  window.Search = Search;
})();
