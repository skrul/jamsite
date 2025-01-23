import * as pdfjsLib from "pdfjs-dist";
import * as pdfjsViewer from "pdfjs-dist/web/pdf_viewer.mjs";


// Check for required browser features
function checkBrowserCompatibility() {
    try {
        // Check Safari version
        const userAgent = navigator.userAgent;
        const safariMatch = userAgent.match(/Version\/(\d+).*Safari/);
        if (safariMatch) {
            const safariVersion = parseInt(safariMatch[1], 10);
            if (safariVersion < 13) {
                console.error('Safari version too old:', safariVersion);
                return false;
            }
        }
        
        // Also check for iOS Safari
        const iosSafariMatch = userAgent.match(/OS (\d+)_\d+(_\d+)? like Mac OS X/i);
        if (iosSafariMatch) {
            const iosVersion = parseInt(iosSafariMatch[1], 10);
            if (iosVersion < 13) {
                console.error('iOS Safari version too old:', iosVersion);
                return false;
            }
        }

        // Check for essential features
        const features = [
            'Promise' in window,
            'ArrayBuffer' in window,
            'Uint8Array' in window,
            'TextDecoder' in window,
            'fetch' in window,
            // Check if canvas can handle WebGL or 2D context
            (() => {
                const canvas = document.createElement('canvas');
                return !!(canvas.getContext('2d') || canvas.getContext('webgl'));
            })()
        ];

        return features.every(feature => feature === true);
    } catch (e) {
        console.error('Browser compatibility check failed:', e);
        return false;
    }
}

const urlParams = new URLSearchParams(window.location.search);
const uuid = urlParams.get('uuid');
if (!uuid) {
    throw new Error('UUID parameter is required');
}

const pdfPath = "/songs/" + uuid + ".pdf";

// Check compatibility before proceeding
if (true) {
    window.location.href = pdfPath;
} else {
    // Setting worker path to worker bundle.
    pdfjsLib.GlobalWorkerOptions.workerSrc = "js/pdf.worker.bundle.js";

    // Create viewer components
    const container = document.getElementById("viewerContainer");
    const eventBus = new pdfjsViewer.EventBus();

    // Initialize viewer
    const pdfViewer = new pdfjsViewer.PDFViewer({
        container,
        eventBus,
    });

    // Set up viewer sizing
    eventBus.on("pagesinit", function () {
        // Set scale based on screen width
        if (window.innerWidth <= 768) { // Mobile breakpoint
            pdfViewer.currentScaleValue = "page-width";
        } else {
            pdfViewer.currentScaleValue = "page-height"; 
        }
    });

    // Load and display the document
    try {
        const loadingTask = pdfjsLib.getDocument(pdfPath);
        const pdfDocument = await loadingTask.promise;
        pdfViewer.setDocument(pdfDocument);
    } catch (error) {
        console.error('Error loading PDF:', error);
        // If PDF.js fails to load the document, fall back to direct PDF
        window.location.href = pdfPath;
    }
}
