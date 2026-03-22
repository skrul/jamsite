(function() {
  function PdfViewer() {
    this.overlay = null;
    this.container = null;
    this.isOpen = false;
    this._savedScrollY = 0;
    var that = this;
    window.addEventListener('popstate', function() {
      that._handlePopState();
    });
  }

  PdfViewer.prototype = {
    open: function(url, title) {
      // Strip #toolbar=0 from URL before passing to PDF.js
      var pdfUrl = url.replace(/#.*$/, '');

      // Parse UUID and slug from /songs/<uuid>/<slug>.pdf
      var parts = pdfUrl.match(/\/songs\/([^/]+)\/([^/]+)\.pdf$/);
      var uuid = parts ? parts[1] : '';
      var slug = parts ? parts[2] : '';

      // Push state for back-button support, then show
      var viewUrl = '/?view=' + encodeURIComponent(uuid);
      if (slug) viewUrl += '&title=' + encodeURIComponent(slug);
      history.pushState({ pdfViewer: true }, '', viewUrl);

      this._show(pdfUrl, title);
    },

    openFromUrl: function() {
      var params = new URLSearchParams(window.location.search);
      var uuid = params.get('view');
      if (!uuid) return;
      var slug = params.get('title') || uuid;
      var pdfUrl = '/songs/' + uuid + '/' + slug + '.pdf';
      var title = this._titleFromUuid(uuid) || slug;
      this._show(pdfUrl, title);
    },

    close: function() {
      if (!this.isOpen) return;
      this._closeDom();
      // Fix URL if it still has view param (e.g. PDF load error)
      var params = new URLSearchParams(window.location.search);
      if (params.has('view')) {
        history.replaceState(null, '', window.location.pathname);
      }
    },

    _show: function(pdfUrl, title) {
      if (this.isOpen) {
        this._closeDom();
      }

      // Create overlay DOM
      this.overlay = document.createElement('div');
      this.overlay.className = 'pdf-viewer-overlay';

      // Header
      var header = document.createElement('div');
      header.className = 'pdf-viewer-header';

      var backBtn = document.createElement('button');
      backBtn.className = 'pdf-viewer-back';
      backBtn.textContent = '\u2190';
      backBtn.addEventListener('click', function() {
        history.back();
      });

      var titleEl = document.createElement('div');
      titleEl.className = 'pdf-viewer-title';
      titleEl.textContent = title || '';

      header.appendChild(backBtn);
      header.appendChild(titleEl);

      // Container for canvases
      this.container = document.createElement('div');
      this.container.className = 'pdf-viewer-container';

      // Loading indicator
      var loading = document.createElement('div');
      loading.className = 'pdf-viewer-loading';
      var spinner = document.createElement('div');
      spinner.className = 'loading-spinner';
      loading.appendChild(spinner);
      this.container.appendChild(loading);

      this.overlay.appendChild(header);
      this.overlay.appendChild(this.container);
      document.body.appendChild(this.overlay);

      // Lock body scroll (iOS needs position:fixed to truly prevent background scroll)
      this._savedScrollY = window.scrollY;
      document.body.style.position = 'fixed';
      document.body.style.top = '-' + this._savedScrollY + 'px';
      document.body.style.width = '100%';
      document.body.style.overflow = 'hidden';

      this.isOpen = true;

      // Render PDF
      this._render(pdfUrl, loading);
    },

    _titleFromUuid: function(uuid) {
      var row = document.getElementById(uuid);
      if (!row) return '';
      var el = row.querySelector('.song-title-text');
      return el ? el.textContent : '';
    },

    _handlePopState: function() {
      var params = new URLSearchParams(window.location.search);
      var uuid = params.get('view');
      if (uuid && !this.isOpen) {
        // Forward navigation to a viewer URL
        var slug = params.get('title') || uuid;
        var pdfUrl = '/songs/' + uuid + '/' + slug + '.pdf';
        var title = this._titleFromUuid(uuid) || slug;
        this._show(pdfUrl, title);
      } else if (!uuid && this.isOpen) {
        // Back navigation from a viewer URL
        this._closeDom();
      }
    },

    _closeDom: function() {
      this.isOpen = false;
      if (this.overlay && this.overlay.parentNode) {
        this.overlay.parentNode.removeChild(this.overlay);
      }
      this.overlay = null;
      this.container = null;
      // Restore body scroll
      document.body.style.position = '';
      document.body.style.top = '';
      document.body.style.width = '';
      document.body.style.overflow = '';
      window.scrollTo(0, this._savedScrollY || 0);
    },

    _render: function(url, loadingEl) {
      var that = this;
      var container = this.container;

      var loadingTask = pdfjsLib.getDocument(url);
      loadingTask.promise.then(function(pdf) {
        // Remove loading indicator
        if (loadingEl && loadingEl.parentNode) {
          loadingEl.parentNode.removeChild(loadingEl);
        }

        // Check if viewer was closed while loading
        if (!that.isOpen) return;

        var numPages = pdf.numPages;
        for (var i = 1; i <= numPages; i++) {
          that._renderPage(pdf, i, container);
        }
      }).catch(function(error) {
        console.error('PDF.js failed to load document:', error);
        // Fall back to native PDF navigation
        that.close();
        window.open(url, '_blank');
      });
    },

    _renderPage: function(pdf, pageNum, container) {
      var that = this;
      pdf.getPage(pageNum).then(function(page) {
        if (!that.isOpen) return;

        var dpr = window.devicePixelRatio || 1;
        var unscaledViewport = page.getViewport({ scale: 1 });
        var isLandscapePdf = unscaledViewport.width > unscaledViewport.height;
        // Landscape PDFs and narrow/portrait screens: use full width.
        // Portrait PDFs on desktop: cap at 818px to match native PDF viewer.
        var maxWidth = (isLandscapePdf || container.clientWidth <= 1024)
          ? container.clientWidth : 818;
        var containerWidth = Math.min(container.clientWidth, maxWidth);
        var scale = containerWidth / unscaledViewport.width;
        var viewport = page.getViewport({ scale: scale * dpr });

        var canvas = document.createElement('canvas');
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        canvas.style.width = (viewport.width / dpr) + 'px';
        canvas.style.height = (viewport.height / dpr) + 'px';
        container.appendChild(canvas);

        var context = canvas.getContext('2d');
        page.render({
          canvasContext: context,
          viewport: viewport
        });
      });
    }
  };

  window.PdfViewer = PdfViewer;
})();
