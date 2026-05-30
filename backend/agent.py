import time
import requests
from playwright.sync_api import sync_playwright

FASTAPI_URL = "http://127.0.0.1:8000"

def get_predictions(fields: list, context: str) -> dict:
    try:
        response = requests.post(f"{FASTAPI_URL}/predict/", json={"fields": fields, "context": context})
        if response.status_code == 200:
            return response.json().get("predictions", {})
    except Exception as e:
        print(f"❌ Connection to FastAPI failed: {e}")
    return {}

def submit_learned_data(mappings: dict):
    """Sends human-filled or corrected data back to the API learning engine."""
    if not mappings:
        return
    try:
        requests.post(f"{FASTAPI_URL}/agent/learn/", json={"field_mappings": mappings})
    except Exception as e:
        print(f"❌ Failed to submit learning payload: {e}")



def log_application(company: str, role: str, link: str):
    """Signals FastAPI to commit a successful run to SQLite and Excel."""
    try:
        response = requests.post(f"{FASTAPI_URL}/job/log/", json={
            "company": company,
            "role": role,
            "link": link,
            "status": "Applied"
        })
        if response.status_code == 200:
            print("✅ Log recorded in SQLite. Excel spreadsheet updated!")
    except Exception as e:
        print(f"❌ Failed to log job entry: {e}")

def prepare_browser(portal: str):
    """Connects to Chrome, opens a tab, and immediately disconnects."""
    portal_urls = {
        "linkedin": "https://www.linkedin.com/jobs/",
        "indeed": "https://www.indeed.com/"
    }
    target_url = portal_urls.get(portal.lower(), "https://www.linkedin.com/jobs/")
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            page = context.new_page() # Open a fresh tab
            page.goto(target_url)
            print(f"✅ Tab opened to {target_url}. Disconnecting to allow manual login.")
            # As soon as this function ends, Playwright disconnects, 
            # but the Chrome tab STAYS OPEN for the user!
        except Exception as e:
            print(f"❌ Could not prepare browser: {e}")
            
def run_autonomous_agent(portal: str = "linkedin"):
    print(f"🤖 Attaching to active Chrome instance for {portal.upper()}...")

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            page = browser.contexts[0].pages[0] if browser.contexts[0].pages else browser.contexts[0].new_page()
            
            for step in range(10):
                print(f"\n--- Scanning Form Page {step + 1} ---")
                time.sleep(2.5) # Allow dynamic frames/DOM segments to settle

                # Extract interactive elements including selects, checkboxes, and radios
                elements = page.query_selector_all('input:not([type="hidden"]):not([type="password"]), textarea, select')
                if not elements:
                    print("ℹ️ No fillable targets found on this view layer.")
                    
                fields_payload = []
                element_metadata = {}

                for idx, el in enumerate(elements):
                    tag_name = el.evaluate("el => el.tagName").upper()
                    input_type = el.get_attribute("type") or "text"
                    name_attr = el.get_attribute("name") or ""
                    id_attr = el.get_attribute("id") or ""
                    placeholder_attr = el.get_attribute("placeholder") or ""
                    
                    # Label resolution engine
                    label_text = placeholder_attr
                    if id_attr:
                        label_el = page.query_selector(f'label[for="{id_attr}"]')
                        if label_el:
                            label_text = label_el.inner_text()
                    
                    field_id = name_attr or id_attr or f"field_{idx}"
                    
                    # Package rich metadata for the LLM pipeline
                    fields_payload.append({
                        "id": field_id,
                        "label": label_text or field_id,
                        "tag": tag_name,
                        "type": input_type
                    })
                    
                    element_metadata[field_id] = {"el": el, "tag": tag_name, "type": input_type}

                page_text = page.evaluate("document.body.innerText")[:3000]
                predictions = get_predictions(fields_payload, page_text)

                # --- ADVANCED FIELD FILLING ENGINE ---
                for field_id, meta in element_metadata.items():
                    if field_id not in predictions:
                        continue
                    
                    val = str(predictions[field_id])
                    el = meta["el"]
                    tag = meta["tag"]
                    itype = meta["type"].lower()

                    try:
                        el.scroll_into_view_if_needed()
                        
                        if tag == "SELECT":
                            # Handle Dropdowns: match by value or visible label text
                            print(f"🔽 Selecting dropdown [{field_id}] -> '{val}'")
                            el.select_option(label=val)
                            
                        elif tag == "INPUT" and itype in ["checkbox", "radio"]:
                            # Handle Selection Flags
                            is_affirmative = val.lower() in ["true", "yes", "1", "male" if "gender" in field_id.lower() else ""]
                            if is_affirmative:
                                print(f"🔘 Checking flag element [{field_id}]")
                                el.check()
                                
                        else:
                            # Standard Linear Typist Emulation for text components
                            print(f"✍️ Injecting text field [{field_id}] -> '{val[:25]}...'")
                            el.focus()
                            el.fill("")
                            el.type(val, delay=40)
                            
                        time.sleep(0.2)
                    except Exception as fill_err:
                        print(f"⚠️ Error processing field {field_id}: {fill_err}")

                # --- INTERCEPT & SELF-LEARNING ENGINE ---
                # Detect structural navigation triggers
                next_button = page.locator("button:has-text('Next'), button:has-text('Review'), button:has-text('Continue')").first
                submit_button = page.locator("button:has-text('Submit application'), button:has-text('Submit')").first

                # Before navigating or submitting, scan what is ACTUALLY inside the form elements
                # This captures any modifications the user typed manually in real-time
                print("🧠 Intercepting values for localized learning model...")
                live_mappings = {}
                for field_id, meta in element_metadata.items():
                    try:
                        current_val = meta["el"].evaluate("el => el.value")
                        if current_val and len(str(current_val).strip()) > 0:
                            live_mappings[field_id] = current_val
                    except:
                        pass
                
                # Push the accurate snapshot back to your system database instance
                submit_learned_data(live_mappings)

                if submit_button.is_visible():
                    print("🚀 Final page reached! Pausing execution to prevent unintended submit...")
                    break 
                elif next_button.is_visible():
                    print("➡️ Advancing to next multi-page section...")
                    next_button.click()
                else:
                    break

        except Exception as e:
            print(f"❌ Automation engine encountered a block: {e}")

if __name__ == "__main__":
    run_autonomous_agent()