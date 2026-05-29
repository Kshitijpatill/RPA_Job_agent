// Listen for fill command from popup UI
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "trigger_fill") {
        fillFormWithIntelligence();
        sendResponse({ status: "success" });
    }
    return true;
});

async function fillFormWithIntelligence() {
    console.log("AI Agent: Scrutinizing the webpage structure...");

    // 1. Grab all fillable inputs
    const inputs = document.querySelectorAll('input:not([type="hidden"]):not([type="password"]), textarea, select');
    
    // 2. Map fields to include their technical ID/name along with visible text label clues
    const fieldsPayload = Array.from(inputs).map(input => {
        // Try to find an associated <label> text element or placeholder text
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
            label: labelText || input.name || input.id || ""
        };
    }).filter(f => f.id);

    // 3. Smart Scrape Job Description Context
    // Looks across common job layout frameworks or grabs main structural text bodies
    let jobDescriptionText = "";
    const contextSelectors = ['#job-description', '.job-description', '[class*="description"]', 'main', 'article'];
    for (const selector of contextSelectors) {
        const element = document.querySelector(selector);
        if (element && element.innerText.length > 200) {
            jobDescriptionText = element.innerText.substring(0, 4000); // Caps content size safely
            break;
        }
    }
    // Fallback if no clean structural containers match
    if (!jobDescriptionText) {
        jobDescriptionText = document.body.innerText.substring(0, 3000);
    }

    try {
        // 4. Send structured payload to unified FastAPI prediction route
        const response = await fetch("http://127.0.0.1:8000/predict/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                fields: fieldsPayload,
                context: jobDescriptionText
            })
        });
        
        const data = await response.json();
        const predictions = data.predictions || {};

        // 5. Smart Injection Loop
        inputs.forEach(input => {
            const targetId = input.name || input.id;
            if (predictions[targetId]) {
                input.value = predictions[targetId];
                // Dispatch input events so framework sites (React/Angular) handle bindings properly
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });
        
        console.log("AI Agent: Smart parsing and form fill execution complete.");
    } catch (error) {
        console.error("AI Agent: Connection breakdown to local prediction matrix.", error);
    }
}