from playwright.sync_api import sync_playwright
from google import genai
import json
import os

PROJECT_ID = "786551482100"

def run_integration_loop():
    with sync_playwright() as p:
        # 1. MUSCLES: Open Browser
        print("🚀 Step 1: Launching Browser...")
        browser = p.chromium.launch(headless=False) # We set to False so you can WATCH it work!
        page = browser.new_page(device_scale_factor=1)
        page.goto("https://www.google.com")
        
        if not os.path.exists("screenshots"): os.makedirs("screenshots")
        screenshot_path = "screenshots/loop_step_1.png"
        page.screenshot(path=screenshot_path)

        # 2. EYES: Ask Gemini for coordinates
        print("👀 Step 2: Gemini is looking at the page...")
        client = genai.Client(vertexai=True, project=PROJECT_ID, location="us-central1")
        
        # We specifically ask to click the Search Bar
        prompt = "Find the search bar and return the [x, y] coordinates in JSON format: {'coords': [x, y]}"
        
        import PIL.Image
        img = PIL.Image.open(screenshot_path)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt, img],
            config={"response_mime_type": "application/json"}
        )
        
        data = json.loads(response.text)
        x, y = data['coords']
        print(f"🎯 Step 3: Gemini decided to click at: {x}, {y}")

        # 3. ACTION: Click the coordinates
        page.mouse.click(x, y)
        print("🖱️ Step 4: Click executed!")
        
        # 4. VERIFY: Take a second screenshot to see if it worked
        page.wait_for_timeout(2000)
        page.screenshot(path="screenshots/loop_step_2.png")
        print("📸 Step 5: Final screenshot saved. Check if the search bar is focused!")

        browser.close()

if __name__ == "__main__":
    run_integration_loop()
