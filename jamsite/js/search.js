(function() {
  function Search(searchInput, songTable, searchFilter, indexData, indexIdMap, decadesMap) {
    this.init(searchInput, songTable, searchFilter, indexData, indexIdMap, decadesMap);
  }
  Search.prototype = {
    init: function(searchInput, songTable, searchFilter, indexData, indexIdMap, decadesMap) {
      var that = this;
      that.searchInput = searchInput;
      that.searchFilter = searchFilter;
      that.songTable = songTable;
      that.indexData = indexData;
      that.indexIdMap = indexIdMap;
      that.decadesMap = decadesMap;
      
      // Get the clear button
      var clearButton = document.getElementById('clear-search');
      
      // Show/hide clear button based on input value
      searchInput.addEventListener(
        'input',
        function(e) {
          setTimeout(function() {
            that.search(e.target.value);
            // Show/hide clear button
            if (e.target.value) {
              clearButton.style.display = 'block';
            } else {
              clearButton.style.display = 'none';
            }
          }, 1);
        },
        false
      );
      
      // Clear search when clear button is clicked
      clearButton.addEventListener(
        'click',
        function() {
          searchInput.value = '';
          clearButton.style.display = 'none';
          that.search('');
        },
        false
      );
    },

    /* returns a set of all songids matching active filters */
    filteredSongIdSet: function() {
      var that = this;
      var res = new Set();
      this.searchFilter.active().forEach(function(decade) {
        if (that.decadesMap[decade] !== undefined) {
          that.decadesMap[decade].forEach(function(songid) {
             res.add(songid);
          });
        }
      });
      return res;
    },

    search: function(s) {
      var res = null;
      var filteredSongs = this.filteredSongIdSet();

      if (s == '') { // No search terms in searchbar
        if (this.searchFilter.active().size == 0) { // and no filters
          // just display everything
          this.songTable.showAllRows();
          return;
        } else { // show all the songs indexed under active filters
          res = filteredSongs;
        }
      } else { // searchbar has text in it
        var terms = s.toLowerCase().split(/,?\s+/);

        // use trie to find matches for all the search terms first
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
        // then apply filters if applicable
        if (filteredSongs.size > 0) {
          res = new Set([...res].filter(x => filteredSongs.has(x)));
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
