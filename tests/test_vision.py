from google import genai
import PIL.Image
import os

def run_vision_test():
    # 1. Setup the Gemini Client
    # It uses your 'gcloud auth' credentials automatically
    client = genai.Client(vertexai=True, project="786551482100", location="us-central1")

    # 2. Load the screenshot you took earlier
    image_path = "screenshots/test_verify.png"
    
    if not os.path.exists(image_path):
        print(f"❌ Error: {image_path} not found. Run 'python3 test_browser.py' first!")
        return

    img = PIL.Image.open(image_path)

    # 3. Ask Gemini to "see" the image
    print("Sending screenshot to Gemini 2.0 Flash via Vertex AI...")
    
    # We ask for coordinates to test the 'UI Navigator' logic specifically
    prompt = "Look at this screenshot of Google. Tell me what you see and give me the approximate [x, y] coordinates of the search bar."
    
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt, img]
    )

    # 4. Print the result
    print("\n--- Gemini's Visual Analysis ---")
    print(response.text)
    print("--------------------------------")
    print("✅ Vision test complete!")

if __name__ == "__main__":
    run_vision_test()
