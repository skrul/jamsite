(function() {
  function Random(randomButton, songTable, search, indexIdMap) {
    this.init(randomButton, songTable, search, indexIdMap);
  }
  Random.prototype = {
    init: function(randomButton, songTable, search, indexIdMap) {
      var that = this;
      that.randomButton = randomButton;
      that.songTable = songTable;
      that.search = search;
      that.indexIdMap = indexIdMap;

      randomButton.addEventListener(
        'click',
        function(e) {
          that.clickRandomButton();
        },
        false
      );
    },

    clickRandomButton: function() {
      this.search.search(''); // clear previous searches to show all rows
      this.showRandomSong();
    },

    showRandomSong: function() {
      var filteredSongIds = Array.from(this.search.filteredSongIdSet());
      var randomSongUuid = null;
      var songElements = null;

      if (filteredSongIds.length > 0) {
        randomSongUuid = this.indexIdMap[filteredSongIds[Math.floor(filteredSongIds.length * Math.random())]];
      } else {
        randomSongUuid = this.indexIdMap[Math.floor(this.indexIdMap.length * Math.random())];
      }

      songElements = document.getElementById(randomSongUuid).children;
      // put the song name in the search string so it can be cleared
      document.getElementById('search').value = songElements[0].textContent;
      this.songTable.showRows([randomSongUuid]);
    }
  }

  window.Random = Random;
})();
