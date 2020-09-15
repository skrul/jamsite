(function() {
  function Random(randomButton, search, indexIdMap) {
    this.init(randomButton, search, indexIdMap);
  }
  Random.prototype = {
    init: function(randomButton, search, indexIdMap) {
      var that = this;
      that.randomButton = randomButton;
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
      this.searchRandomSong();
    },

    searchRandomSong: function() {
      var randomSongUUID = this.indexIdMap[Math.floor(this.indexIdMap.length * Math.random())];
      var songElements = document.getElementById(randomSongUUID).children;
      // put the song name and artist name in the search string
      var searchString = `${songElements[0].textContent} ${songElements[1].textContent}`;

      document.getElementById('search').value = searchString;
      this.search.search(searchString);
    }
  }

  window.Random = Random;
})();
