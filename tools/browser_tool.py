from playwright.sync_api import sync_playwright
import os
from datetime import datetime

class BrowserTool:
    def __init__(self):
        self.width = 1280
        self.height = 800
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_folder = f"output/run_{timestamp}"
        os.makedirs(self.run_folder, exist_ok=True)
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)
        self.context = self.browser.new_context(viewport={'width': self.width, 'height': self.height})
        self.page = self.context.new_page()

    def navigate_scan_and_scroll(self, url):
        print(f"🌐 [NODE] {url}")
        try:
            # FIX 1 & 2: "domcontentloaded" waits through redirects (no double load)
            # and ensures the DOM is ready before scrolling (scroll won't be reset by page loading)
            self.page.goto(url, wait_until="domcontentloaded", timeout=15000)
            # FIX: removed redundant wait_for_selector("body") — domcontentloaded guarantees body exists
            self.page.evaluate("""
                async () => {
                    for (let j = 0; j < 4; j++) {
                        window.scrollBy(0, 800);
                        await new Promise(r => setTimeout(r, 150));
                    }
                    window.scrollTo(0, 0);
                }
            """)
            elements = self.page.evaluate("""
                () => {
                    return Array.from(document.querySelectorAll('a, button, input')).map(el => {
                        const rect = el.getBoundingClientRect();
                        return {
                            tag: el.tagName,
                            text: (el.innerText || el.placeholder || "").trim(),
                            href: el.href || null,
                            coords: [
                                Math.round(rect.left + rect.width / 2),
                                Math.round(rect.top + rect.height / 2)
                            ],
                            isVisible: rect.width > 0 && rect.height > 0
                        };
                    }).filter(el => el.isVisible && el.text.length > 0);
                }
            """)
            safe_name = url.split("//")[-1].replace("/", "_").replace(".", "_")[:30]
            self.page.screenshot(path=os.path.join(self.run_folder, f"{safe_name}.png"))
            return {"url": self.page.url.rstrip("/"), "elements": elements, "run_folder": self.run_folder}
        except:
            return None

    def login(self, fields, username, password):
        """
        Fill and submit login form.
        Strategy 1: DOM selectors (reliable, works on most sites).
        Strategy 2: Coordinate-based from AuthAgent (fallback).
        Returns True if URL changed after submit (login succeeded).
        """
        url_before = self.page.url

        if not self._dom_login(username, password):
            self._coord_login(fields, username, password)

        self.page.wait_for_load_state("domcontentloaded", timeout=10000)
        success = self.page.url.rstrip("/") != url_before.rstrip("/")
        status = "✅ Success" if success else "⚠️  URL unchanged — credentials may be wrong"
        print(f"  🔐 Login submitted → {self.page.url}  {status}")
        return success

    def _dom_login(self, username, password):
        """Fill login form using DOM selectors — works on most standard login pages."""
        try:
            pwd = self.page.locator('input[type="password"]').first
            if not pwd.is_visible(timeout=2000):
                return False

            user = self.page.locator(
                'input[type="email"], '
                'input[type="text"][name*="user" i], '
                'input[type="text"][id*="user" i], '
                'input[placeholder*="user" i], '
                'input[placeholder*="email" i], '
                'input[type="text"]'
            ).first
            user.fill(username)
            pwd.fill(password)

            submit = self.page.locator(
                'button[type="submit"], '
                'input[type="submit"], '
                'button:text-matches("login|sign in|log in|submit", "i")'
            ).first
            submit.click()
            print("  📋 DOM-based fill succeeded")
            return True
        except Exception:
            return False

    def _coord_login(self, fields, username, password):
        """Coordinate-based fill using AuthAgent vision output."""
        try:
            uf = fields["username_field"]["coords"]
            pf = fields["password_field"]["coords"]
            sb = fields["submit_button"]["coords"]

            self.page.mouse.click(uf[0], uf[1], click_count=3)
            self.page.keyboard.type(username, delay=50)
            self.page.mouse.click(pf[0], pf[1], click_count=3)
            self.page.keyboard.type(password, delay=50)
            self.page.mouse.click(sb[0], sb[1])
            print("  🎯 Coordinate-based fill used")
        except Exception as e:
            print(f"  ⚠️  Coordinate fill error: {e}")

    def close(self):
        self.browser.close()
        self.playwright.stop()
