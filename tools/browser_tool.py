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
                    for (let j = 0; j < 6; j++) {
                        window.scrollBy(0, 800);
                        // FIX 1: 300ms gives lazy-loaded content time to render (was 10ms)
                        await new Promise(r => setTimeout(r, 300));
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
            return {"url": self.page.url, "elements": elements, "run_folder": self.run_folder}
        except:
            return None

    def close(self):
        self.browser.close()
        self.playwright.stop()
