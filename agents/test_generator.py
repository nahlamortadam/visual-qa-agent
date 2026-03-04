import json
import os
import PIL.Image


class TestGeneratorAgent:
    def __init__(self, client):
        self.client = client

    def generate_tests(self, scan_data, secretary_output, inspector_output):
        safe_name = scan_data['url'].split("//")[-1].replace("/", "_").replace(".", "_")[:30]
        screenshot_path = os.path.join(scan_data['run_folder'], f"{safe_name}.png")

        if not os.path.exists(screenshot_path):
            print(f"  ⚠️ Screenshot not found: {screenshot_path}")
            return {"page_url": scan_data['url'], "test_suites": []}

        img = PIL.Image.open(screenshot_path)

        intent = secretary_output.get('intent', '')
        component_map = json.dumps(secretary_output.get('component_map', []))
        bugs = json.dumps(inspector_output.get('bugs', []))
        elements = json.dumps(scan_data.get('elements', [])[:60])

        prompt = f"""You are a Senior QA Engineer. Analyze this web page screenshot and generate a COMPLETE test suite.

Page URL: {scan_data['url']}
Page Intent: {intent}
Interactive Elements (with coordinates): {elements}
Component Map: {component_map}
Visual Bugs Already Found: {bugs}

Generate test cases covering ALL of the following categories:

1. HAPPY PATH — normal user flows that should succeed
2. EDGE CASES — empty inputs, max-length strings, special characters, boundary values
3. NEGATIVE — invalid data, wrong formats, unauthorized actions
4. SECURITY — XSS attempts, SQL injection, script injection in input fields
5. VISUAL — layout checks, responsiveness, element visibility

Rules:
- Use the exact coordinates from the component map for every element interaction
- Every test case must have clear, specific steps an automation engineer can execute
- Steps must use only these actions: navigate, click, fill, assert, hover, scroll
- "assert" steps have no coords — just target and expected_value fields
- Each test case ID must be unique and sequential (TC-001, TC-002, ...)
- Be thorough — a login page should have at least 8-10 test cases

Return ONLY valid JSON in this exact format:
{{
  "page_url": "{scan_data['url']}",
  "intent": "{intent}",
  "test_suites": [
    {{
      "suite": "Suite name (e.g. Login Form — Happy Path)",
      "test_cases": [
        {{
          "id": "TC-001",
          "name": "Short descriptive name",
          "category": "happy_path",
          "priority": "critical",
          "precondition": "User is on the login page",
          "steps": [
            {{"action": "navigate", "target": "{scan_data['url']}", "coords": null, "value": null}},
            {{"action": "fill", "target": "Email input", "coords": [320, 240], "value": "user@example.com"}},
            {{"action": "click", "target": "Submit button", "coords": [320, 340], "value": null}},
            {{"action": "assert", "target": "Dashboard heading", "coords": null, "value": "Welcome"}}
          ],
          "expected_result": "User is redirected to dashboard and sees welcome message"
        }}
      ]
    }}
  ]
}}"""

        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt, img],
            config={"response_mime_type": "application/json"}
        )

        result = json.loads(response.text)
        self._save(scan_data, result)
        return result

    def _save(self, scan_data, tests):
        safe_name = scan_data['url'].split("//")[-1].replace("/", "_").replace(".", "_")[:50]
        path = os.path.join(scan_data['run_folder'], f"{safe_name}_tests.json")
        with open(path, 'w') as f:
            json.dump(tests, f, indent=4)
