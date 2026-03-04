import json

class ScoutAgent:
    def __init__(self, client):
        self.client = client

    def get_next_move(self, image_path):
        import PIL.Image
        img = PIL.Image.open(image_path)

        prompt = """
        You are a Web Scout. Look at this English Google homepage.
        1. Find the long search input bar in the center.
        2. Give me the coordinates for the BLANK SPACE in the middle of the bar, 
           away from the colorful icons (mic/camera) on the right and the AI button.
        3. Use a 0-1000 coordinate scale.
        
        Return ONLY a JSON object: 
        {"action": "type", "text": "Gemini AI", "coords": [x, y]}
        """

        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt, img],
            config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
