(function() {
  function Search(searchInput, songTable, searchFilter, indexData, indexIdMap, decadesMap, playlistsMap) {
    this.init(searchInput, songTable, searchFilter, indexData, indexIdMap, decadesMap, playlistsMap);
  }
  Search.prototype = {
    init: function(searchInput, songTable, searchFilter, indexData, indexIdMap, decadesMap, playlistsMap) {
      var that = this;
      that.searchInput = searchInput;
      that.searchFilter = searchFilter;
      that.songTable = songTable;
      that.indexData = indexData;
      that.indexIdMap = indexIdMap;
      that.decadesMap = decadesMap;
      that.playlistsMap = playlistsMap || {};
      that.activePlaylist = null;
      that.playlistClearBtn = document.getElementById('playlist-clear');
      if (that.playlistClearBtn) {
        that.playlistClearBtn.addEventListener('click', function() {
          that.clearPlaylist();
        });
      }

      searchInput.addEventListener(
        'input',
        function(e) {
          // X button was clicked while playlist was active — clear the playlist
          if (that.activePlaylist !== null && e.target.value === '') {
            that.clearPlaylist();
            return;
          }
          if (!that.activePlaylist) {
            setTimeout(function() {
              that.search(e.target.value);
            }, 150);
          }
        },
        false
      );

      // 'search' event fires on clear-button click in some browsers
      searchInput.addEventListener(
        'search',
        function(e) {
          if (that.activePlaylist !== null && e.target.value === '') {
            that.clearPlaylist();
          }
        },
        false
      );
    },

    setPlaylist: function(name) {
      this.activePlaylist = name;
      this.searchInput.value = 'Playlist: ' + name;
      this.searchInput.readOnly = true;
      this.searchInput.classList.add('playlist-active');
      if (this.playlistClearBtn) this.playlistClearBtn.style.display = 'block';
      document.querySelectorAll('#decade-filter .filter').forEach(function(btn) { btn.disabled = true; });
      var randomBtn = document.getElementById('random');
      if (randomBtn) randomBtn.disabled = true;
      this.search('');
    },

    clearPlaylist: function() {
      this.activePlaylist = null;
      this.searchInput.readOnly = false;
      this.searchInput.value = '';
      this.searchInput.classList.remove('playlist-active');
      if (this.playlistClearBtn) this.playlistClearBtn.style.display = 'none';
      document.querySelectorAll('#decade-filter .filter').forEach(function(btn) { btn.disabled = false; });
      var randomBtn = document.getElementById('random');
      if (randomBtn) randomBtn.disabled = false;
      document.dispatchEvent(new CustomEvent('playlistcleared'));
      this.search('');
    },

    /* returns a set of all songids matching active filters */
    filteredSongIdSet: function() {
      var that = this;
      var res = new Set();

      // Decade filter
      this.searchFilter.active().forEach(function(decade) {
        if (that.decadesMap[decade] !== undefined) {
          that.decadesMap[decade].forEach(function(songid) {
             res.add(songid);
          });
        }
      });

      // Playlist filter
      if (this.activePlaylist && this.playlistsMap[this.activePlaylist]) {
        var playlistSet = new Set(this.playlistsMap[this.activePlaylist]);
        if (res.size > 0) {
          res = new Set([...res].filter(function(x) { return playlistSet.has(x); }));
        } else {
          res = playlistSet;
        }
      }

      return res;
    },

    search: function(s) {
      var res = null;
      var filteredSongs = this.filteredSongIdSet();
      var hasActiveFilters = this.searchFilter.active().size > 0 || this.activePlaylist !== null;

      if (s == '') { // No search terms in searchbar
        if (!hasActiveFilters) { // and no filters
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
