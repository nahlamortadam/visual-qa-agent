import json
import os
import PIL.Image


class AuthAgent:
    def __init__(self, client):
        self.client = client

    def find_login_fields(self, screenshot_path):
        """
        Use Gemini vision to locate username, password fields and submit button.
        Returns field coordinates, or {"found": false} if no login form exists.
        """
        if not os.path.exists(screenshot_path):
            return {"found": False}

        img = PIL.Image.open(screenshot_path)

        prompt = """Analyze this webpage screenshot and find the login/authentication form.

Identify the center pixel coordinates of:
1. The username or email input field
2. The password input field
3. The login/submit button

The viewport is 1280x800 pixels. Use exact pixel coordinates.

Return ONLY valid JSON in this format:
{
  "found": true,
  "username_field": {"coords": [x, y], "label": "Email"},
  "password_field": {"coords": [x, y], "label": "Password"},
  "submit_button":  {"coords": [x, y], "label": "Login"}
}

If no login form is visible on this page, return:
{"found": false}"""

        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt, img],
            config={"response_mime_type": "application/json"},
        )
        return json.loads(response.text)

    def is_auth_wall(self, screenshot_path):
        """
        Detect if the current page is a login/auth wall that is blocking crawl progress.
        Returns True if a login form is present and the page appears to require authentication.
        Used mid-crawl to prevent the agent from getting stuck.
        """
        if not os.path.exists(screenshot_path):
            return False

        img = PIL.Image.open(screenshot_path)

        prompt = """Look at this webpage screenshot and answer ONE question:

Is this page primarily a login, sign-in, or authentication page that blocks access to content?

Signs it IS an auth wall:
- Has a username/email + password form as the main content
- Shows "Please log in", "Sign in to continue", "Access denied", "Session expired"
- The main purpose of this page is authentication, not content

Signs it is NOT an auth wall:
- Has actual content (articles, products, dashboard, navigation)
- Login is just a small widget in the corner, not the main focus
- It's a 404 or error page

Return ONLY valid JSON:
{"is_auth_wall": true} or {"is_auth_wall": false}"""

        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt, img],
            config={"response_mime_type": "application/json"},
        )
        result = json.loads(response.text)
        return result.get("is_auth_wall", False)
