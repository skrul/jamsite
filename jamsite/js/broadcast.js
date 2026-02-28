(function() {
  function Broadcast() {
    this.clientId = null;
    this.eventSource = null;
    this.toastContainer = null;
    this._createToastContainer();
    this._connect();
  }

  Broadcast.prototype = {
    _connect: function() {
      var that = this;
      this.eventSource = new EventSource('/api/events');

      this.eventSource.onmessage = function(event) {
        var data = JSON.parse(event.data);

        if (data.type === 'connected') {
          that.clientId = data.clientId;
          return;
        }

        if (data.type === 'song') {
          that._showToast(data);
        }
      };

      this.eventSource.onerror = function() {
        // EventSource auto-reconnects; clientId will be reassigned
        that.clientId = null;
      };
    },

    send: function(uuid, title, artist) {
      if (!this.clientId) return;

      fetch('/api/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          senderId: this.clientId,
          uuid: uuid,
          title: title,
          artist: artist
        })
      }).catch(function(err) {
        console.error('Failed to send broadcast:', err);
      });
    },

    _createToastContainer: function() {
      this.toastContainer = document.createElement('div');
      this.toastContainer.className = 'broadcast-toast-container';
      document.body.appendChild(this.toastContainer);
    },

    _showToast: function(data) {
      var that = this;
      var toast = document.createElement('div');
      toast.className = 'broadcast-toast';

      var content = document.createElement('div');
      content.className = 'broadcast-toast-content';

      var text = document.createElement('div');
      text.className = 'broadcast-toast-text';

      var titleEl = document.createElement('div');
      titleEl.className = 'broadcast-toast-title';
      titleEl.textContent = data.title;

      var artistEl = document.createElement('div');
      artistEl.className = 'broadcast-toast-artist';
      artistEl.textContent = data.artist;

      var dismiss = document.createElement('button');
      dismiss.className = 'broadcast-toast-dismiss';
      dismiss.textContent = '\u00D7';
      dismiss.addEventListener('click', function(e) {
        e.stopPropagation();
        that._dismissToast(toast);
      });

      text.appendChild(titleEl);
      text.appendChild(artistEl);
      content.appendChild(text);
      toast.appendChild(content);
      toast.appendChild(dismiss);

      toast.addEventListener('click', function() {
        that._dismissToast(toast);
        window.open('/songs/' + data.uuid + '.pdf#toolbar=0', '_blank');
      });

      this.toastContainer.appendChild(toast);

      requestAnimationFrame(function() {
        toast.classList.add('broadcast-toast-visible');
      });

      toast._dismissTimer = setTimeout(function() {
        that._dismissToast(toast);
      }, 10000);
    },

    _dismissToast: function(toast) {
      if (toast._dismissed) return;
      toast._dismissed = true;
      clearTimeout(toast._dismissTimer);
      toast.classList.remove('broadcast-toast-visible');
      toast.classList.add('broadcast-toast-hiding');
      setTimeout(function() {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast);
        }
      }, 300);
    }
  };

  window.Broadcast = Broadcast;
})();
