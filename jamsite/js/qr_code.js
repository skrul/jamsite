(function() {
  function QRCodePopup() {
    this.init();
  }

  QRCodePopup.prototype = {
    init: function() {
      // Create modal elements if they don't exist
      if (!document.getElementById('qr-modal')) {
        this.createModalElements();
      }
      
      // Add event listener for closing the modal
      document.getElementById('qr-modal-close').addEventListener('click', this.closeModal.bind(this));
      
      // Close modal when clicking outside the content
      document.getElementById('qr-modal').addEventListener('click', function(e) {
        if (e.target === this) {
          this.style.display = 'none';
        }
      });
    },
    
    createModalElements: function() {
      // Create modal container
      var modal = document.createElement('div');
      modal.id = 'qr-modal';
      modal.className = 'qr-modal';
      
      // Create modal content
      var modalContent = document.createElement('div');
      modalContent.className = 'qr-modal-content';
      
      // Create close button
      var closeBtn = document.createElement('span');
      closeBtn.className = 'qr-modal-close';
      closeBtn.id = 'qr-modal-close';
      closeBtn.innerHTML = '&times;';
      
      // Create QR code container
      var qrContainer = document.createElement('div');
      qrContainer.id = 'qr-code-container';
      
      // Create song info container
      var songInfo = document.createElement('div');
      songInfo.id = 'qr-song-info';
      
      // Assemble the modal
      modalContent.appendChild(closeBtn);
      modalContent.appendChild(songInfo);
      modalContent.appendChild(qrContainer);
      modal.appendChild(modalContent);
      
      // Add to document
      document.body.appendChild(modal);
    },
    
    showQRCode: function(songUuid, songTitle, songArtist) {
      // Get the modal
      var modal = document.getElementById('qr-modal');
      
      // Update song info
      var songInfo = document.getElementById('qr-song-info');
      songInfo.innerHTML = '<h3>' + songTitle + '</h3>';
      if (songArtist) {
        songInfo.innerHTML += '<p>' + songArtist + '</p>';
      }
      
      // Generate the URL
      var url = window.location.origin + '/songs/' + songUuid + '.pdf';
      
      // Clear previous QR code
      var qrContainer = document.getElementById('qr-code-container');
      qrContainer.innerHTML = '';
      
      // Generate new QR code
      var qr = new QRCode(qrContainer, {
        text: url,
        width: 256,
        height: 256,
        colorDark: "#000000",
        colorLight: "#ffffff",
        correctLevel: QRCode.CorrectLevel.H
      });
      
      // Show the modal
      modal.style.display = 'block';
    },
    
    closeModal: function() {
      document.getElementById('qr-modal').style.display = 'none';
    }
  };
  
  window.QRCodePopup = QRCodePopup;
})(); 