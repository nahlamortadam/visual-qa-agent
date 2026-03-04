import os
from playwright.sync_api import sync_playwright

def run_test():
    # Ensure the screenshots directory exists
    if not os.path.exists("screenshots"):
        os.makedirs("screenshots")
        print("Created 'screenshots' folder.")

    with sync_playwright() as p:
        print("Launching Chromium...")
        # device_scale_factor=1 ensures standard pixel sizes on Retina screens
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(device_scale_factor=1)
        page = context.new_page()

        url = "https://www.google.com"
        print(f"Navigating to {url}...")
        page.goto(url)

        path = "screenshots/test_verify.png"
        page.screenshot(path=path)
        print(f"✅ Success! Screenshot saved at: {path}")

        browser.close()

if __name__ == "__main__":
    run_test()
