chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "trigger_fill") {
        fillFormWithIntelligence();
        sendResponse({ status: "success" });
    }
    return true;
});

async function fillFormWithIntelligence() {
    console.log("AI Agent: Scrutinizing the webpage structure...");

    const inputs = document.querySelectorAll('input:not([type="hidden"]):not([type="password"]), textarea, select');
    
    const fieldsPayload = Array.from(inputs).map(input => {
        let labelText = "";
        if (input.id) {
            const labelEl = document.querySelector(`label[for="${input.id}"]`);
            if (labelEl) labelText = labelEl.innerText;
        }
        if (!labelText && input.placeholder) {
            labelText = input.placeholder;
        }
        return {
            id: input.name || input.id || "",
            label: labelText || input.name || input.id || "",
            tag: input.tagName,
            type: input.type
        };
    }).filter(f => f.id);

    let jobDescriptionText = document.body.innerText.substring(0, 3000);

    try {
        // Ask the background script to fetch the predictions securely
        const response = await new Promise((resolve, reject) => {
            chrome.runtime.sendMessage({
                action: "api_predict",
                fields: fieldsPayload,
                context: jobDescriptionText
            }, (res) => {
                // Safely catch dead connections (Orphaned scripts)
                if (chrome.runtime.lastError) {
                    return reject(new Error(chrome.runtime.lastError.message));
                }
                resolve(res);
            });
        });

        if (!response || !response.success) {
            console.error("AI Agent: Backend connection failed via middleman.", response?.error);
            return;
        }

        const predictions = response.data.predictions || {};

        inputs.forEach(input => {
            const targetId = input.name || input.id;
            if (predictions[targetId]) {
                const predictedValue = String(predictions[targetId]);
                
                if (input.tagName === "INPUT") {
                    if (input.type === "radio" || input.type === "checkbox") {
                        const inputValue = (input.value || "").toLowerCase();
                        const predLower = predictedValue.toLowerCase();
                        if (inputValue === predLower || (predLower === "male" && inputValue === "m") || (predLower === "female" && inputValue === "f")) {
                            input.checked = true;
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    } else {
                        input.value = predictedValue;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                } else if (input.tagName === "SELECT") {
                    for (let i = 0; i < input.options.length; i++) {
                        if (input.options[i].text.toLowerCase().includes(predictedValue.toLowerCase()) || 
                            input.options[i].value.toLowerCase() === predictedValue.toLowerCase()) {
                            input.selectedIndex = i;
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                            break;
                        }
                    }
                } else if (input.tagName === "TEXTAREA") {
                    input.value = predictedValue;
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        });
        
        console.log("AI Agent: Smart parsing and form fill execution complete.");
    } catch (error) {
        console.error("AI Agent: Internal messaging breakdown.", error);
    }
}

// --- THE OBSERVER (Capture Phase) ---
// Using "true" at the end forces Chrome to catch the submit BEFORE the website intercepts it
document.addEventListener('submit', (event) => {
    const form = event.target;
    const inputs = form.querySelectorAll('input:not([type="password"]):not([type="hidden"]), textarea, select');
    const liveMappings = {};

    inputs.forEach(input => {
        const fieldName = input.name || input.id;
        let value = "";

        if (input.type === "radio" || input.type === "checkbox") {
            if (input.checked) value = input.value;
        } else {
            value = input.value;
        }
        
        if (fieldName && value && value.trim() !== "") {
            liveMappings[fieldName] = value;
        }
    });

    if (Object.keys(liveMappings).length > 0) {
        console.log("AI Agent: Intercepted manual data. Sending to background script...");
        // Use fire-and-forget message passing so the page can reload without breaking the request
        chrome.runtime.sendMessage({
            action: "api_learn",
            mappings: liveMappings
        });
    }
}, true);