from playwright.sync_api import sync_playwright
import json

def save_x_session():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        print("🌐 Opening login page. Please login manually...")
        page.goto("https://x.com/login")
        input("🛑 After logging in fully and tweets are visible, press Enter here...")

        context.storage_state(path="x_session.json")
        print("✅ Session saved to x_session.json")
        browser.close()

if __name__ == "__main__":
    save_x_session()
