(function() {
  function SortPopover(popoverLink, popoverBody, songTable) {
    this.init(popoverLink, popoverBody, songTable);
  }
  SortPopover.prototype = {
    init: function(popoverLink, popoverBody, songTable) {
      var that = this;
      that.popoverLink = popoverLink;
      that.popoverBody = popoverBody;
      that.songTable = songTable;
      //this.opened = false;

      popoverLink.addEventListener(
        'click',
        function(e) {
          that.clickPopverLink();
        },
        false
      );

      this._getNavItem('title').addEventListener(
        'click',
        function(e) { that.sort('Title', 'title'); },
        false
      );
      this._getNavItem('artist').addEventListener(
        'click',
        function(e) { that.sort('Artist', 'artist'); },
        false
      );
      this._getNavItem('year').addEventListener(
        'click',
        function(e) { that.sort('Year', 'year'); },
        false
      );
    },

    clickPopverLink: function() {
      this.popoverBody.classList.toggle('open')
    },

    sort: function(text, column) {
      this.popoverLink.innerHTML = text + ' &blacktriangledown;';
      this.popoverBody.classList.remove('open');
      this.songTable.sort(column);
    },

    _getNavItem: function(name) {
      return this.popoverBody.getElementsByClassName(name)[0];
    }
  }
  window.SortPopover = SortPopover;
})();
