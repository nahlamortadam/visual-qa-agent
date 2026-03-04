import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*OpenSSL.*")
warnings.filterwarnings("ignore", message=".*LibreSSL.*")
warnings.filterwarnings("ignore", module="urllib3")
warnings.filterwarnings("ignore", module="google")

import argparse
import json
import threading
import os
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
from dotenv import load_dotenv
from google import genai

from tools.browser_tool import BrowserTool
from agents.input_agent import InputAgent
from agents.auth_agent import AuthAgent
from agents.secretary import SecretaryAgent
from agents.inspector import InspectorAgent
from agents.test_generator import TestGeneratorAgent
from agents.report_writer import ReportWriter

load_dotenv()
PROJECT_ID = os.environ["GCP_PROJECT_ID"]

VISITED_HISTORY_FILE = ".visited_urls.json"


# ── Persistent visited URL tracking (per domain) ─────────────────────────────

def load_visited(domain):
    """Load previously visited URLs for a domain across all past runs."""
    if os.path.exists(VISITED_HISTORY_FILE):
        with open(VISITED_HISTORY_FILE) as f:
            history = json.load(f)
        return set(history.get(domain, []))
    return set()


def save_visited(domain, visited):
    """Persist the visited URL set so future runs skip already-tested pages."""
    history = {}
    if os.path.exists(VISITED_HISTORY_FILE):
        with open(VISITED_HISTORY_FILE) as f:
            history = json.load(f)
    history[domain] = sorted(visited)
    with open(VISITED_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


# ── Per-page agent pipeline ───────────────────────────────────────────────────

def process_page(scan_data, secretary, inspector, test_generator, all_results, lock):
    url = scan_data.get("url", "?")
    try:
        safe_name = scan_data["url"].split("//")[-1].replace("/", "_").replace(".", "_")[:30]
        screenshot_path = os.path.join(scan_data["run_folder"], f"{safe_name}.png")

        # Secretary and Inspector run in parallel (independent)
        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_sec = pool.submit(secretary.document_page, scan_data)
            fut_vis = pool.submit(inspector.scan_for_bugs, screenshot_path)
            sec_output = fut_sec.result()
            vis_output = fut_vis.result()

        tests = test_generator.generate_tests(scan_data, sec_output, vis_output)

        tc_count = sum(len(s.get("test_cases", [])) for s in tests.get("test_suites", []))
        print(
            f"  ✅ {len(sec_output.get('component_map', []))} components  |  "
            f"🔍 health {vis_output.get('visual_health_score', '?')}/10  |  "
            f"🧪 {tc_count} test cases"
        )

        with lock:
            all_results.append({
                "url": url,
                "secretary": sec_output,
                "inspector": vis_output,
                "tests": tests,
            })

    except Exception as e:
        print(f"  ⚠️  Pipeline error [{url}]: {e}")


# ── Auth ──────────────────────────────────────────────────────────────────────

def handle_auth(browser, auth_agent, config):
    print(f"\n🔐 Navigating to {config['start_url']} for authentication...")
    browser.page.goto(config["start_url"], wait_until="domcontentloaded", timeout=15000)
    tmp_path = os.path.join(browser.run_folder, "_auth_screenshot.png")
    browser.page.screenshot(path=tmp_path)
    fields = auth_agent.find_login_fields(tmp_path)
    if fields.get("found"):
        print("  🔍 Login form detected — filling credentials...")
        browser.login(fields, config["username"], config["password"])
    else:
        print("  ⚠️  No login form found on start page — proceeding without login")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Visual QA Agent — generate test suites for any website"
    )
    parser.add_argument("--url",      type=str, help="Website URL to test (omit to let the agent suggest one)")
    parser.add_argument("--username", type=str, help="Login username or email")
    parser.add_argument("--password", type=str, help="Login password")
    parser.add_argument("--pages",    type=int, default=0,
                        help="Max pages to crawl (default: 0 = full site, no limit)")
    args = parser.parse_args()

    client = genai.Client(vertexai=True, project=PROJECT_ID, location="us-central1")

    input_agent = InputAgent(client)
    config = input_agent.resolve(
        url=args.url,
        username=args.username,
        password=args.password,
        max_pages=args.pages,
    )

    domain = urlparse(config["start_url"]).netloc

    # Load previously visited URLs for this domain
    # Always allow the start_url itself — it's the entry point for this run
    visited = load_visited(domain)
    visited.discard(config["start_url"])
    if visited:
        print(f"📋 Skipping {len(visited)} already-tested pages from previous runs")

    browser        = BrowserTool()
    auth_agent     = AuthAgent(client)
    secretary      = SecretaryAgent(client)
    inspector      = InspectorAgent(client)
    test_generator = TestGeneratorAgent(client)

    if config["needs_auth"]:
        handle_auth(browser, auth_agent, config)
        post_login_url = browser.page.url.rstrip("/")
        # If the URL changed after login, start crawl from the post-auth page
        # If it didn't change, login likely failed — crawl from start_url anyway
        if post_login_url != config["start_url"]:
            queue = [post_login_url]
            print(f"  📍 Post-login start: {post_login_url}")
        else:
            print("  ⚠️  Login did not redirect — crawling start URL without auth")
            queue = [config["start_url"]]
    else:
        queue = [config["start_url"]]
    threads     = []
    lock        = threading.Lock()
    all_results = []
    pages_crawled = 0
    max_pages = config["max_pages"]  # 0 = unlimited

    while queue:
        if max_pages and pages_crawled >= max_pages:
            break

        url      = queue.pop(0)
        norm_url = url.split("?")[0].rstrip("/")

        if norm_url in visited or not norm_url.startswith(config["base_domain"]):
            continue

        visited.add(norm_url)
        pages_crawled += 1
        label = f"{pages_crawled}" + (f"/{max_pages}" if max_pages else "")
        print(f"\n🌐 PAGE {label}  →  {norm_url}")

        try:
            scan_data = browser.navigate_scan_and_scroll(norm_url)
            if not scan_data:
                continue

            # Mid-crawl auth wall detection — prevents agent from getting stuck
            # on pages that require login (e.g. session expired, protected routes)
            tmp_shot = os.path.join(browser.run_folder, f"_check_{pages_crawled}.png")
            browser.page.screenshot(path=tmp_shot)
            if auth_agent.is_auth_wall(tmp_shot):
                if config["needs_auth"]:
                    print("  🔒 Auth wall detected mid-crawl — re-authenticating...")
                    fields = auth_agent.find_login_fields(tmp_shot)
                    if fields.get("found"):
                        browser.login(fields, config["username"], config["password"])
                        # Re-scan the page we're now on after re-auth
                        scan_data = browser.navigate_scan_and_scroll(browser.page.url.rstrip("/"))
                        if not scan_data:
                            continue
                    else:
                        print("  ⚠️  Auth wall found but no login form detected — skipping page")
                        continue
                else:
                    print("  🔒 Auth wall detected — skipping (no credentials provided)")
                    continue
            os.remove(tmp_shot)  # clean up temp check screenshot

            t = threading.Thread(
                target=process_page,
                args=(scan_data, secretary, inspector, test_generator, all_results, lock),
                daemon=True,
            )
            t.start()
            threads.append(t)

            for el in scan_data.get("elements", []):
                h = el.get("href")
                if h:
                    ch = h.split("?")[0].rstrip("/")
                    if ch.startswith(config["base_domain"]) and ch not in visited and ch not in queue:
                        queue.append(ch)

        except Exception as e:
            print(f"  ⚠️  Crawl error: {e}")
            continue

    # Persist visited URLs so next run skips them
    save_visited(domain, visited)
    print(f"\n💾 Saved {len(visited)} visited URLs for {domain} — won't be re-tested next run")

    print(f"\n⏳ Waiting for {len(threads)} agent pipelines to finish...")
    for t in threads:
        t.join(timeout=120)  # 2-min max per page — never hangs the whole run
        if t.is_alive():
            print("  ⚠️  Pipeline timed out for a page — moving on")

    print(f"\n📊 Writing report...")
    report_writer = ReportWriter(browser.run_folder)
    report_writer.generate(all_results)

    print(f"\n🏁 Done!  Output folder: {browser.run_folder}/")
    print(f"   ├── {{page}}_knowledge.json   UI component maps")
    print(f"   ├── {{page}}_tests.json       per-page test cases")
    print(f"   ├── test_suite.json          all tests (machine-readable)")
    print(f"   └── report.md               full report (human-readable)")

    browser.close()


if __name__ == "__main__":
    main()
