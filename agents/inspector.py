import json
import os
import PIL.Image


class InspectorAgent:
    def __init__(self, client):
        self.client = client

    def scan_for_bugs(self, image_path):
        if not os.path.exists(image_path):
            return {"visual_health_score": None, "bugs": [f"Screenshot not found: {image_path}"]}

        img = PIL.Image.open(image_path)

        prompt = """You are a Senior Visual QA Inspector.

Analyze this screenshot carefully for any of the following issues:
- Overlapping or truncated text
- Broken or missing images (blank boxes, broken image icons)
- Misaligned elements (buttons, inputs, labels out of place)
- Layout overflow (content spilling outside containers)
- Inconsistent spacing or padding
- Elements cut off at viewport edges
- Color contrast issues (unreadable text)
- Invisible or zero-opacity interactive elements

Assign a visual_health_score from 0 (completely broken) to 10 (pixel-perfect).
List each bug as a short, specific description (e.g. "Login button overlaps email field at y=340").

Return ONLY valid JSON:
{
  "visual_health_score": 9,
  "bugs": [
    "Description of bug 1",
    "Description of bug 2"
  ]
}

If no bugs are found, return an empty bugs array."""

        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt, img],
            config={"response_mime_type": "application/json"}
        )
        result = json.loads(response.text)
        self._save(image_path, result)
        return result

    def _save(self, image_path, result):
        base = os.path.splitext(image_path)[0]
        path = f"{base}_visual.json"
        with open(path, "w") as f:
            json.dump(result, f, indent=4)
