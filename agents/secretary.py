import json
import os

class SecretaryAgent:
    def __init__(self, client):
        self.client = client

    def document_page(self, scan_data):
        if not scan_data:
            return {"intent": "Failed", "component_map": []}
        elements_context = json.dumps(scan_data['elements'][:60])
        prompt = f"Analyze UI for {scan_data['url']}. Return ONLY JSON: {{\"intent\": \"string\", \"component_map\": [ {{\"label\": \"string\", \"abs_coords\": [x, y], \"logic\": \"string\"}} ] }} DATA: {elements_context}"
        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt],
            config={"response_mime_type": "application/json"}
        )
        analysis = json.loads(response.text)
        self._save(scan_data, analysis)
        return analysis

    def _save(self, scan_data, analysis):
        safe_name = scan_data['url'].split("//")[-1].replace("/", "_").replace(".", "_")[:50]
        file_path = os.path.join(scan_data['run_folder'], f"{safe_name}_knowledge.json")
        with open(file_path, 'w') as f:
            json.dump(analysis, f, indent=4)
