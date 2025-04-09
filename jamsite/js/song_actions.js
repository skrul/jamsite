(function() {
  function SongActions() {
    this.init();
    this.qrPopup = new QRCodePopup();
  }

  SongActions.prototype = {
    init: function() {
      var that = this;
      document.addEventListener('click', function(e) {
        // Close any open popovers when clicking outside
        if (!e.target.closest('.song-actions')) {
          that.closeAllPopovers();
        }
      });

      // Handle toggle clicks
      document.addEventListener('click', function(e) {
        if (e.target.classList.contains('song-actions-toggle')) {
          e.preventDefault();
          e.stopPropagation();
          that.togglePopover(e.target);
        }
      });

      // Handle share QR code clicks
      document.addEventListener('click', function(e) {
        if (e.target.classList.contains('share-qr')) {
          e.preventDefault();
          e.stopPropagation();
          that.handleShareQR(e.target);
        }
      });
    },

    togglePopover: function(toggle) {
      this.closeAllPopovers();
      var popover = toggle.nextElementSibling;
      popover.classList.add('open');
    },

    closeAllPopovers: function() {
      var popovers = document.querySelectorAll('.song-actions-popover');
      popovers.forEach(function(popover) {
        popover.classList.remove('open');
      });
    },

    handleShareQR: function(link) {
      var uuid = link.getAttribute('data-uuid');
      var row = document.getElementById(uuid);
      
      // Get song title and artist from the row
      var title = row.querySelector('.song-title-text').textContent.trim();
      var artist = row.cells[1].textContent.trim();
      
      // Close the popover
      this.closeAllPopovers();
      
      // Show the QR code popup
      this.qrPopup.showQRCode(uuid, title, artist);
    }
  }

  window.SongActions = SongActions;
})(); 