import threading
import os
from dotenv import load_dotenv
from google import genai
from tools.browser_tool import BrowserTool
from agents.secretary import SecretaryAgent
from agents.inspector import InspectorAgent
from agents.test_generator import TestGeneratorAgent
from agents.report_writer import ReportWriter

load_dotenv()
PROJECT_ID = os.environ["GCP_PROJECT_ID"]


def process_page(scan_data, secretary, inspector, test_generator, all_results, lock):
    """Run the full agent pipeline for one page."""
    url = scan_data.get("url", "?")
    try:
        # 1. Map the UI — intent + component map
        sec_output = secretary.document_page(scan_data)

        # 2. Visual inspection — health score + bugs
        safe_name = scan_data['url'].split("//")[-1].replace("/", "_").replace(".", "_")[:30]
        screenshot_path = os.path.join(scan_data['run_folder'], f"{safe_name}.png")
        vis_output = inspector.scan_for_bugs(screenshot_path)

        # 3. Generate test cases (multimodal: screenshot + DOM)
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


def main():
    browser = BrowserTool()
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="us-central1")

    secretary     = SecretaryAgent(client)
    inspector     = InspectorAgent(client)
    test_generator = TestGeneratorAgent(client)

    start_url = "https://the-internet.herokuapp.com"
    queue     = [start_url]
    visited   = set()
    max_pages = 5

    all_results = []
    lock        = threading.Lock()
    threads     = []

    while queue and len(visited) < max_pages:
        url      = queue.pop(0)
        norm_url = url.split("?")[0].rstrip("/")

        if norm_url in visited or not norm_url.startswith(start_url) or "auth" in norm_url:
            continue

        visited.add(norm_url)
        print(f"\n🌐 PAGE {len(visited)}/{max_pages}  →  {norm_url}")

        try:
            scan_data = browser.navigate_scan_and_scroll(norm_url)
            if not scan_data:
                continue

            # Agent pipeline runs in background so crawl continues immediately
            t = threading.Thread(
                target=process_page,
                args=(scan_data, secretary, inspector, test_generator, all_results, lock),
                daemon=True,
            )
            t.start()
            threads.append(t)

            # Enqueue discovered links
            for el in scan_data.get("elements", []):
                h = el.get("href")
                if h:
                    ch = h.split("?")[0].rstrip("/")
                    if ch.startswith(start_url) and ch not in visited and ch not in queue:
                        queue.append(ch)

        except Exception as e:
            print(f"  ⚠️  Crawl error: {e}")
            continue

    print(f"\n⏳ Waiting for {len(threads)} agent pipelines to finish...")
    for t in threads:
        t.join()

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
