// Constants for localStorage keys
var VIEWER_ENABLED_KEY = 'jamsite_viewer_enabled';

// Check if in-app PDF viewer is enabled
function isViewerEnabled() {
    try {
        return localStorage.getItem(VIEWER_ENABLED_KEY) === 'true';
    } catch (error) {
        return false;
    }
}

// Enable or disable in-app PDF viewer
function setViewerEnabled(enabled) {
    try {
        localStorage.setItem(VIEWER_ENABLED_KEY, enabled ? 'true' : 'false');
        return true;
    } catch (error) {
        console.error('Error saving viewer preferences:', error);
        return false;
    }
}

// Export the functions
window.viewerPreferences = {
    isEnabled: isViewerEnabled,
    setEnabled: setViewerEnabled
};
