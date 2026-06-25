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

      // Use replaceState when already viewing a song so back goes to the index, not through every song
      var viewUrl = '/songs/' + encodeURIComponent(uuid) + '/' + encodeURIComponent(slug) + '.pdf';
      if (this.isOpen) {
        history.replaceState({ pdfViewer: true }, '', viewUrl);
      } else {
        history.pushState({ pdfViewer: true }, '', viewUrl);
      }

      this._show(pdfUrl, title);
    },

    openFromUrl: function() {
      // Try /songs/<uuid>/<slug>.pdf path format first
      var pdfMatch = window.location.pathname.match(/^\/songs\/([^/]+)\/([^/]+)\.pdf$/);
      var uuid, slug;
      if (pdfMatch) {
        uuid = decodeURIComponent(pdfMatch[1]);
        slug = decodeURIComponent(pdfMatch[2]);
      } else {
        // Fallback: old /song/<uuid>/<slug> path format
        var pathMatch = window.location.pathname.match(/^\/song\/([^/]+)\/([^/]+)$/);
        if (pathMatch) {
          uuid = decodeURIComponent(pathMatch[1]);
          slug = decodeURIComponent(pathMatch[2]);
        } else {
          // Fallback: old /?view=<uuid>&title=<slug> format
          var params = new URLSearchParams(window.location.search);
          uuid = params.get('view');
          if (!uuid) return;
          slug = params.get('title') || uuid;
        }
      }
      var pdfUrl = '/songs/' + uuid + '/' + slug + '.pdf';
      var title = this._titleFromUuid(uuid) || slug;
      this._show(pdfUrl, title);
    },

    close: function() {
      if (!this.isOpen) return;
      this._closeDom();
      // Fix URL if it still has viewer path or view param (e.g. PDF load error)
      if (window.location.pathname.match(/^\/songs\/[^/]+\/[^/]+\.pdf$/) || window.location.pathname.match(/^\/song\//) || new URLSearchParams(window.location.search).has('view')) {
        history.replaceState(null, '', '/');
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
        if (history.state && history.state.pdfViewer) {
          history.back();
        } else {
          window.location.href = '/';
        }
      });

      var titleEl = document.createElement('div');
      titleEl.className = 'pdf-viewer-title';
      titleEl.textContent = title || '';

      // Share menu
      var songParts = pdfUrl.match(/\/songs\/([^/]+)\/([^/]+)\.pdf$/);
      var shareWrap = document.createElement('div');
      shareWrap.className = 'pdf-viewer-share-wrap';

      var shareBtn = document.createElement('button');
      shareBtn.className = 'pdf-viewer-share';
      shareBtn.title = 'Share';
      shareBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12v7a2 2 0 002 2h12a2 2 0 002-2v-7"/><polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/></svg>';

      var sharePopover = document.createElement('div');
      sharePopover.className = 'pdf-viewer-share-popover';

      if (songParts) {
        var uuid = songParts[1];
        var slug = songParts[2];

        var shareRoom = document.createElement('a');
        shareRoom.href = '#';
        shareRoom.className = 'pdf-viewer-share-item share-with-room';
        shareRoom.setAttribute('data-uuid', uuid);
        shareRoom.setAttribute('data-slug', slug);
        shareRoom.textContent = 'Share with room';

        var shareQr = document.createElement('a');
        shareQr.href = '#';
        shareQr.className = 'pdf-viewer-share-item share-qr';
        shareQr.setAttribute('data-uuid', uuid);
        shareQr.setAttribute('data-slug', slug);
        shareQr.textContent = 'Share via QR code';

        var copyLink = document.createElement('a');
        copyLink.href = '#';
        copyLink.className = 'pdf-viewer-share-item';
        copyLink.textContent = 'Copy link to PDF';
        copyLink.addEventListener('click', function(e) {
          e.preventDefault();
          e.stopPropagation();
          var songUrl = window.location.origin + '/songs/' + uuid + '/' + slug + '.pdf';
          navigator.clipboard.writeText(songUrl).then(function() {
            copyLink.textContent = 'Copied!';
            setTimeout(function() { copyLink.textContent = 'Copy link to PDF'; }, 1500);
          });
          sharePopover.classList.remove('open');
        });

        var downloadPdf = document.createElement('a');
        downloadPdf.href = '/songs/' + uuid + '/' + slug + '.pdf';
        downloadPdf.download = slug + '.pdf';
        downloadPdf.className = 'pdf-viewer-share-item';
        downloadPdf.textContent = 'Download PDF';
        downloadPdf.addEventListener('click', function() {
          sharePopover.classList.remove('open');
        });

        sharePopover.appendChild(shareRoom);
        sharePopover.appendChild(shareQr);
        sharePopover.appendChild(copyLink);
        sharePopover.appendChild(downloadPdf);
      }

      shareBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        sharePopover.classList.toggle('open');
      });

      // Close popover when clicking outside
      this.overlay.addEventListener('click', function(e) {
        if (!e.target.closest('.pdf-viewer-share-wrap')) {
          sharePopover.classList.remove('open');
        }
      });

      shareWrap.appendChild(shareBtn);
      shareWrap.appendChild(sharePopover);

      header.appendChild(backBtn);
      header.appendChild(titleEl);
      header.appendChild(shareWrap);

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
      // Check /songs/<uuid>/<slug>.pdf path first, then old formats
      var pdfMatch = window.location.pathname.match(/^\/songs\/([^/]+)\/([^/]+)\.pdf$/);
      var uuid, slug;
      if (pdfMatch) {
        uuid = decodeURIComponent(pdfMatch[1]);
        slug = decodeURIComponent(pdfMatch[2]);
      } else {
        var pathMatch = window.location.pathname.match(/^\/song\/([^/]+)\/([^/]+)$/);
        if (pathMatch) {
          uuid = decodeURIComponent(pathMatch[1]);
          slug = decodeURIComponent(pathMatch[2]);
        } else {
          var params = new URLSearchParams(window.location.search);
          uuid = params.get('view');
          slug = params.get('title') || (uuid || '');
        }
      }
      if (uuid) {
        // Navigation to a viewer URL (open or switch song)
        var pdfUrl = '/songs/' + uuid + '/' + slug + '.pdf';
        var title = this._titleFromUuid(uuid) || slug;
        this._show(pdfUrl, title);
      } else if (this.isOpen) {
        // Back navigation to the index
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
      var timeoutId = setTimeout(function() {
        loadingTask.destroy();
      }, 15000);
      loadingTask.promise.then(function(pdf) {
        clearTimeout(timeoutId);
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
        clearTimeout(timeoutId);
        console.error('PDF.js failed to load document:', error);
        if (loadingEl && loadingEl.parentNode) {
          loadingEl.parentNode.removeChild(loadingEl);
        }
        if (!that.isOpen) return;
        var errorDiv = document.createElement('div');
        errorDiv.className = 'pdf-viewer-error';
        errorDiv.innerHTML = '<p>Could not load PDF.</p><a href="' + url + '" target="_blank">Open PDF directly \u2197</a>';
        container.appendChild(errorDiv);
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
