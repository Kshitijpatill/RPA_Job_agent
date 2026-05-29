import time
import requests
from playwright.sync_api import sync_playwright

FASTAPI_URL = "http://127.0.0.1:8000"

def get_predictions(fields: list, context: str) -> dict:
    """Queries the running FastAPI backend for database, ML, or LLM choices."""
    try:
        response = requests.post(f"{FASTAPI_URL}/predict/", json={
            "fields": fields,
            "context": context
        })
        if response.status_code == 200:
            return response.json().get("predictions", {})
    except Exception as e:
        print(f"❌ Connection to FastAPI failed: {e}")
    return {}

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

def run_autonomous_agent():
    print("🤖 Attaching to active Chrome instance on port 9222...")
    
    with sync_playwright() as p:
        try:
            # Connect over Chrome DevTools Protocol (CDP)
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            default_context = browser.contexts[0]
            
            # Select the currently open, active tab view
            if default_context.pages:
                page = default_context.pages[0]
            else:
                page = default_context.new_page()
                
            print(f"🌐 Operating on active tab URL: {page.url}")
            
            # 1. Gather visible fillable fields on the page view
            inputs = page.query_selector_all('input:not([type="hidden"]):not([type="password"]), textarea, select')
            if not inputs:
                print("ℹ️ No standard input targets found on this view layer.")
                return

            fields_payload = []
            for idx, el in enumerate(inputs):
                name_attr = el.get_attribute("name") or ""
                id_attr = el.get_attribute("id") or ""
                placeholder_attr = el.get_attribute("placeholder") or ""
                
                # Check for label elements pointing to this field's ID
                label_text = placeholder_attr
                if id_attr:
                    label_el = page.query_selector(f'label[for="{id_attr}"]')
                    if label_el:
                        label_text = label_el.inner_text()
                
                field_id = name_attr or id_attr or f"field_{idx}"
                fields_payload.append({
                    "id": field_id,
                    "label": label_text or field_id
                })

            # 2. Extract structural page layout text for Ollama contextual answers
            page_text = page.evaluate("document.body.innerText")[:3000]

            # 3. Post to API to secure field assignments
            print("🧠 Parsing fields through local pipeline modules...")
            predictions = get_predictions(fields_payload, page_text)

            # 4. Human-emulated typing injection execution
            for el in inputs:
                name_attr = el.get_attribute("name") or ""
                id_attr = el.get_attribute("id") or ""
                field_id = name_attr or id_attr
                
                if field_id in predictions:
                    val = predictions[field_id]
                    print(f"✍️ Injecting field [{field_id}] -> '{str(val)[:30]}...'")
                    
                    el.scroll_into_view_if_needed()
                    el.focus()
                    
                    # Wipe existing values cleanly
                    el.fill("")
                    
                    # Type linearly with slight character pacing latency to mimic human presence
                    el.type(str(val), delay=45)
                    time.sleep(0.3)

            print("🏁 Entry pass complete. Check adjustments, then commit registration step.")
            
            # Example tracking automation handle:
            # In your main structural loop, parse the portal DOM elements to capture string values:
            # log_application("Example Company Name", "Software Development Intern", page.url)

        except Exception as e:
            print(f"❌ Automation engine encountered a block: {e}")

if __name__ == "__main__":
    run_autonomous_agent()