import json
import os
from urllib.parse import urlparse

HISTORY_FILE = ".suggested_urls.json"


class InputAgent:
    def __init__(self, client):
        self.client = client

    def resolve(self, url=None, username=None, password=None, max_pages=5):
        """
        Validate and normalize inputs.
        If no URL is provided, ask Gemini to suggest one it hasn't suggested before.
        """
        if not url:
            print("🤔 No URL provided — asking Gemini to suggest a website...")
            url = self._suggest_url()
            print(f"📌 Suggested: {url}")
        else:
            url = self._normalize(url)
            print(f"🎯 Target: {url}")

        parsed = urlparse(url)
        base_domain = f"{parsed.scheme}://{parsed.netloc}"

        config = {
            "start_url":   url,
            "base_domain": base_domain,
            "username":    username or None,
            "password":    password or None,
            "needs_auth":  bool(username and password),
            "max_pages":   max_pages,
        }

        if config["needs_auth"]:
            print(f"🔐 Auth credentials received for: {username}")

        return config

    def _normalize(self, url):
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url.rstrip("/")

    def _load_history(self):
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE) as f:
                return json.load(f)
        return []

    def _save_history(self, history):
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)

    def _suggest_url(self):
        history = self._load_history()
        exclusions = ""
        if history:
            exclusions = (
                f"\n\nDo NOT suggest any of these previously suggested URLs:\n"
                + "\n".join(f"- {u}" for u in history)
                + "\nPick something different."
            )

        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                "Suggest one well-known, publicly accessible website that is ideal for QA testing demos. "
                "It should have: forms, navigation menus, interactive elements, and multiple pages. "
                "Vary your suggestions — consider e-commerce, SaaS dashboards, news, forums, documentation sites, etc. "
                "Return ONLY the full URL with no explanation (e.g. https://example.com)."
                + exclusions
            ],
            config={"temperature": 1.0},
        )

        url = self._normalize(response.text.strip().strip("\"'"))

        # Save to history so it's not repeated next time
        history.append(url)
        self._save_history(history)

        return url
