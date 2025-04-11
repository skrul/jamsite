// Constants for localStorage keys
const OFFLINE_ENABLED_KEY = 'jamsite_offline_enabled';

// Default preferences
const DEFAULT_PREFERENCES = {
    enabled: false
};

// Get the current preferences
function getPreferences() {
    try {
        const stored = localStorage.getItem(OFFLINE_ENABLED_KEY);
        if (stored === null) {
            // If no preferences are stored, return defaults
            return DEFAULT_PREFERENCES;
        }
        return JSON.parse(stored);
    } catch (error) {
        console.error('Error reading offline preferences:', error);
        return DEFAULT_PREFERENCES;
    }
}

// Save preferences
function savePreferences(preferences) {
    try {
        localStorage.setItem(OFFLINE_ENABLED_KEY, JSON.stringify(preferences));
        return true;
    } catch (error) {
        console.error('Error saving offline preferences:', error);
        return false;
    }
}

// Enable or disable offline viewing
function setOfflineEnabled(enabled) {
    const preferences = getPreferences();
    preferences.enabled = enabled;
    return savePreferences(preferences);
}

// Check if offline viewing is enabled
function isOfflineEnabled() {
    return getPreferences().enabled;
}

// Export the functions
window.offlinePreferences = {
    setEnabled: setOfflineEnabled,
    isEnabled: isOfflineEnabled
}; 