// Constants for worker states
const WORKER_STATES = {
    STOPPED: 'STOPPED',
    SYNCING: 'SYNCING',
    SYNCED: 'SYNCED',
    STOPPING: 'STOPPING'
};

// Constants for message types
const MESSAGE_TYPES = {
    START: 'START',
    STOP: 'STOP',
    SYNC: 'SYNC'
};

// Database configuration
const DB_NAME = 'jamsite_offline';
const DB_VERSION = 1;
const STORE_NAME = 'songs';

let currentState = WORKER_STATES.STOPPED;
let db = null;

// Initialize IndexedDB
async function initDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            db = request.result;
            resolve(db);
        };

        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains(STORE_NAME)) {
                db.createObjectStore(STORE_NAME, { keyPath: 'uuid' });
            }
        };
    });
}

// Send progress update to the main thread
function sendProgress(type, data) {
    self.postMessage({
        type: 'progress',
        status: type,
        data: data
    });
}

// Download a PDF file and store it in the cache
async function downloadPDF(uuid, hash) {
    try {
        const url = `/songs/${uuid}.pdf`;
        console.log('Downloading PDF:', uuid, url);
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        // Create a new response with the hash in headers
        const headers = new Headers(response.headers);
        headers.set('X-File-Hash', hash);
        
        const modifiedResponse = new Response(response.body, {
            status: response.status,
            statusText: response.statusText,
            headers: headers
        });
        
        const cache = await caches.open('pdf-cache');
        await cache.put(`/pdfs/${uuid}`, modifiedResponse);
        return true;
    } catch (error) {
        console.error('Error downloading PDF:', error);
        return false;
    }
}

// Check if a cached file matches the expected hash
async function checkCachedFile(uuid, expectedHash) {
    try {
        const cache = await caches.open('pdf-cache');
        const response = await cache.match(`/pdfs/${uuid}`);
        if (!response) return false;
        
        const cachedHash = response.headers.get('X-File-Hash');
        return cachedHash === expectedHash;
    } catch (error) {
        console.error('Error checking cached file:', error);
        return false;
    }
}

// Helper functions for IndexedDB operations
function getRecord(store, key) {
    return new Promise((resolve, reject) => {
        const request = store.get(key);
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

function putRecord(store, record) {
    return new Promise((resolve, reject) => {
        const request = store.put(record);
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
    });
}

function deleteRecord(store, key) {
    return new Promise((resolve, reject) => {
        const request = store.delete(key);
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
    });
}

function getAllRecords(store) {
    return new Promise((resolve, reject) => {
        const request = store.getAll();
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

// Main sync cycle implementation
async function syncCycle() {
    if (currentState !== WORKER_STATES.SYNCING) return;

    try {
        // Ensure database is initialized
        if (!db) {
            await initDB();
        }

        // Download song list from origin
        sendProgress('checking', { message: 'Checking for updates...' });
        const response = await fetch('/songs.json');
        const songs = await response.json();

        // Process each song
        let downloaded = 0;
        for (const song of songs) {
            if (currentState !== WORKER_STATES.SYNCING) return;

            const transaction = db.transaction([STORE_NAME], 'readonly');
            const store = transaction.objectStore(STORE_NAME);
            const existing = await getRecord(store, song.uuid);
            
            // Check both IndexedDB and Cache
            const isCached = await checkCachedFile(song.uuid, song.hash);

            if (!existing || existing.hash !== song.hash || !isCached) {
                sendProgress('downloading', {
                    current: downloaded,
                    total: songs.length,
                    message: `Downloading...`
                });

                const success = await downloadPDF(song.uuid, song.hash);
                if (success) {
                    const writeTransaction = db.transaction([STORE_NAME], 'readwrite');
                    const writeStore = writeTransaction.objectStore(STORE_NAME);
                    await putRecord(writeStore, { uuid: song.uuid, hash: song.hash });
                }
            }
            downloaded++;
        }

        // Clean up old files
        sendProgress('cleaning', { message: 'Cleaning up old files...' });
        
        const transaction = db.transaction([STORE_NAME], 'readonly');
        const store = transaction.objectStore(STORE_NAME);
        const allRecords = await getAllRecords(store);
        
        for (const record of allRecords) {
            if (!songs.find(s => s.uuid === record.uuid)) {
                const cache = await caches.open('pdf-cache');
                await cache.delete(`/pdfs/${record.uuid}`);
                
                const deleteTransaction = db.transaction([STORE_NAME], 'readwrite');
                const deleteStore = deleteTransaction.objectStore(STORE_NAME);
                await deleteRecord(deleteStore, record.uuid);
            }
        }

        currentState = WORKER_STATES.SYNCED;
        sendProgress('downloaded', { message: 'All files are up to date' });

    } catch (error) {
        console.error('Sync cycle error:', error);
        sendProgress('error', { message: 'An error occurred during sync' });
        currentState = WORKER_STATES.STOPPED;
    }
}

// Clean up function
async function cleanup() {
    try {
        const cache = await caches.open('pdf-cache');
        await cache.keys().then(keys => {
            keys.forEach(key => cache.delete(key));
        });
        
        if (db) {
            const transaction = db.transaction([STORE_NAME], 'readwrite');
            const store = transaction.objectStore(STORE_NAME);
            await store.clear();
        }
        
        sendProgress('cleared', { message: 'Offline storage cleared' });
    } catch (error) {
        console.error('Cleanup error:', error);
    }
    currentState = WORKER_STATES.STOPPED;
}

// Message handler
self.onmessage = async (event) => {
    const { type } = event.data;
    console.log('Sync worker type:', type);

    switch (type) {
        case MESSAGE_TYPES.START:
            if (currentState === WORKER_STATES.STOPPED) {
                currentState = WORKER_STATES.SYNCING;
                syncCycle();
            }
            break;

        case MESSAGE_TYPES.STOP:
            if (currentState === WORKER_STATES.SYNCING || currentState === WORKER_STATES.SYNCED) {
                currentState = WORKER_STATES.STOPPING;
                cleanup();
            }
            break;

        case MESSAGE_TYPES.SYNC:
            if (currentState === WORKER_STATES.SYNCED) {
                currentState = WORKER_STATES.SYNCING;
                syncCycle();
            }
            break;
    }
};
