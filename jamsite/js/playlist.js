(function() {
  function Playlist(container, search, sideMenu) {
    if (!container) return;
    var that = this;
    this.search = search;
    this.sideMenu = sideMenu;
    this.activeBtn = null;

    document.addEventListener('playlistcleared', function() {
      if (that.activeBtn) {
        that.activeBtn.classList.remove('button-primary');
        that.activeBtn = null;
      }
    });

    container.addEventListener('click', function(e) {
      var btn = e.target.closest('.playlist-btn');
      if (!btn) return;

      var name = btn.getAttribute('data-playlist');
      if (that.activeBtn === btn) {
        // Clicking active playlist deactivates it
        btn.classList.remove('button-primary');
        that.activeBtn = null;
        that.search.clearPlaylist();
      } else {
        if (that.activeBtn) {
          that.activeBtn.classList.remove('button-primary');
        }
        btn.classList.add('button-primary');
        that.activeBtn = btn;
        that.search.setPlaylist(name);
      }

      // Close the side menu
      if (that.sideMenu) {
        that.sideMenu.classList.remove('open');
        var overlay = document.getElementById('side-menu-overlay');
        if (overlay) overlay.classList.remove('visible');
        document.body.style.overflow = '';
      }
    });
  }

  window.Playlist = Playlist;
})();
