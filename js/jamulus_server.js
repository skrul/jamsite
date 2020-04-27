(function() {
  function JamulusServer() {
    this.init();
  }
  JamulusServer.prototype = {
    init: function() {
      var that = this;
      that.serverStatus = document.getElementById('server-status');
      that.serverStartedAt = document.getElementById('server-started-at');
      that.serverControl = document.getElementById('server-control');
      that.last_status = null;
      that.state = null;
      that.pollTimer = null;
      this.refresh();

      that.serverControl.addEventListener(
        'click',
        function(e) {
          that.clickServerControl();
        },
        false
      );

    },

    refresh: function() {
      if (this.last_status == null) {
        this.serverStatus.innerHTML = '';
        this.serverStartedAt.innerHTML = '';
        this.serverControl.disabled = true;
        return;
      }

      this.serverStatus.innerHTML = this.state;
      if (this.state == 'running') {
        this.serverControl.innerHTML = 'Stop';
        this.serverControl.disabled = false;
        this.serverStartedAt.innerHTML = new Date(this.last_status.launch_time);
      }

      if (this.state == 'stopped') {
        this.serverControl.innerHTML = ' Start';
        this.serverControl.disabled = false;
        this.serverStartedAt.innerHTML = '';
      }

      if (this.state == 'stopping') {
        this.serverControl.innerHTML = 'Stopping...<i>\uD83C\uDFB8</i>';
        this.serverControl.disabled = true;
        this.serverStartedAt.innerHTML = '';
      }

      if (this.state == 'pending') {
        this.serverControl.innerHTML = 'Starting...<i>\uD83C\uDFB8</i>';
        this.serverControl.disabled = true;
        this.serverStartedAt.innerHTML = '';
      }
    },

    refresh_status: function() {
      var that = this;
      this._post('status', function(o) {
        that.last_status = o;
        that.state = o.state;
        that.refresh();
        if (o.state == 'running' || o.state == 'stopped') {
          that.stopRefreshPoll();
        }
        if (o.state == 'stopping' || o.state == 'pending') {
          that.startRefreshPoll();
        }
      });
    },

    clickServerControl: function() {
      var that = this;
      if (this.state == 'running') {
        this._post('stop', function(o) {
          that.refresh_status();
          that.startRefreshPoll();
        });
      }
      if (this.state == 'stopped') {
        this._post('start', function(o) {
          that.refresh_status();
          that.startRefreshPoll();
        });
      }
    },

    startRefreshPoll: function() {
      if (this.pollTimer != null) {
        return;
      }
      var that = this;
      that.pollTimer = setInterval(function() { that.refresh_status(); }, 5000);
    },

    stopRefreshPoll: function() {
      if (this.pollTimer == null) {
        return;
      }
      clearTimeout(this.pollTimer);
      this.pollTimer = null;
    },

    _post: function(action, f) {
      var xhr = new XMLHttpRequest();
      xhr.open(
        'POST',
        'https://43ljrpyu15.execute-api.us-west-1.amazonaws.com/default/jamulus-control',
        true
      );
      xhr.setRequestHeader('Content-Type', 'application/json;charset=UTF-8');
      xhr.onload = function () {
	var users = JSON.parse(xhr.responseText);
	if (xhr.readyState == 4 && xhr.status == '200') {
          f(JSON.parse(xhr.responseText));
	} else {
	  console.error(xhr);
	}
      }
      xhr.send('{"action":"' + action + '"}');
    }
  }

  window.JamulusServer = JamulusServer;
})();
