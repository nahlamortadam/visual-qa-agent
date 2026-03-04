import json

class LogicGuard:
    def __init__(self, client):
        self.client = client

    def verify_test_results(self, page_data, test_case):
        prompt = f"""
        Analyze this test case goal: "{test_case['goal']}"
        Against these available elements: {json.dumps(page_data['elements'][:30])}
        
        Determine if the test is logicially sound based on the UI.
        Return ONLY JSON: {{"status": "PASS/FAIL", "reason": "string"}}
        """
        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt],
            config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
