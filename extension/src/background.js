// 1. TOOLBAR ICON LISTENER (Mode Switcher)
chrome.action.onClicked.addListener(async (tab) => {
    const result = await chrome.storage.local.get(['appMode']);
    const mode = result.appMode || 'semi';

    if (mode === 'semi') {
        console.log("Executing Semi-Manual Auto-Fill...");
        chrome.tabs.sendMessage(tab.id, { action: "trigger_fill" });
    } else {
        chrome.runtime.openOptionsPage();
    }
});

// 2. THE API MIDDLEMAN (Bypasses CORS and Mixed Content restrictions)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    
    // Route A: Predict Data
    if (request.action === "api_predict") {
        fetch("http://127.0.0.1:8000/predict/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ fields: request.fields, context: request.context })
        })
        .then(res => res.json())
        .then(data => sendResponse({ success: true, data: data }))
        .catch(err => sendResponse({ success: false, error: err.message }));
        
        return true; // Tells Chrome to keep the channel open for the async response
    }

    // Route B: Learn Data
    if (request.action === "api_learn") {
        fetch("http://127.0.0.1:8000/agent/learn/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ field_mappings: request.mappings })
        })
        .then(res => res.json())
        .then(data => sendResponse({ success: true, data: data }))
        .catch(err => sendResponse({ success: false, error: err.message }));
        
        return true;
    }
});