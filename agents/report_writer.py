import json
import os
from datetime import datetime


PRIORITY_EMOJI = {
    "critical": "🔴",
    "high":     "🟠",
    "medium":   "🟡",
    "low":      "🟢",
}

CATEGORY_LABEL = {
    "happy_path": "Happy Path",
    "edge_case":  "Edge Case",
    "negative":   "Negative",
    "security":   "Security",
    "visual":     "Visual",
}


class ReportWriter:
    def __init__(self, run_folder):
        self.run_folder = run_folder

    def generate(self, all_results):
        self._write_test_suite_json(all_results)
        self._write_markdown(all_results)

    # ── JSON ────────────────────────────────────────────────────────────────────

    def _write_test_suite_json(self, all_results):
        total_tc = self._count_tests(all_results)

        output = {
            "generated_at": datetime.now().isoformat(),
            "total_pages": len(all_results),
            "total_test_cases": total_tc,
            "pages": [
                {
                    "url": r["url"],
                    "intent": r.get("secretary", {}).get("intent", ""),
                    "visual_health_score": r.get("inspector", {}).get("visual_health_score"),
                    "visual_bugs": r.get("inspector", {}).get("bugs", []),
                    "test_suites": r.get("tests", {}).get("test_suites", []),
                }
                for r in all_results
            ],
        }

        path = os.path.join(self.run_folder, "test_suite.json")
        with open(path, "w") as f:
            json.dump(output, f, indent=4)
        print(f"  📋 test_suite.json  →  {total_tc} test cases across {len(all_results)} pages")

    # ── Markdown ─────────────────────────────────────────────────────────────────

    def _write_markdown(self, all_results):
        total_tc = self._count_tests(all_results)
        avg_score = self._avg_health(all_results)
        total_bugs = sum(len(r.get("inspector", {}).get("bugs", [])) for r in all_results)

        lines = [
            "# Visual QA — Automated Test Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**Pages scanned:** {len(all_results)}  ",
            f"**Total test cases:** {total_tc}  ",
            f"**Avg visual health:** {avg_score}/10  ",
            f"**Visual bugs found:** {total_bugs}  ",
            "",
            "---",
            "",
        ]

        # Summary table
        lines += [
            "## Summary",
            "",
            "| Page | Intent | Health | Tests |",
            "|------|--------|--------|-------|",
        ]
        for r in all_results:
            url = r["url"]
            intent = r.get("secretary", {}).get("intent", "—")[:60]
            score = r.get("inspector", {}).get("visual_health_score", "—")
            tc_count = sum(
                len(s.get("test_cases", []))
                for s in r.get("tests", {}).get("test_suites", [])
            )
            lines.append(f"| `{url}` | {intent} | {score}/10 | {tc_count} |")

        lines += ["", "---", ""]

        # Per-page detail
        for r in all_results:
            url = r["url"]
            secretary = r.get("secretary", {})
            inspector = r.get("inspector", {})
            tests = r.get("tests", {})

            lines += [f"## {url}", ""]
            lines.append(f"**Intent:** {secretary.get('intent', '—')}  ")
            lines.append(f"**Visual health:** {inspector.get('visual_health_score', '—')}/10  ")

            bugs = inspector.get("bugs", [])
            if bugs:
                lines += ["", "**Visual bugs:**"]
                for bug in bugs:
                    lines.append(f"- {bug}")

            component_map = secretary.get("component_map", [])
            if component_map:
                lines += ["", f"**UI components mapped:** {len(component_map)}"]

            for suite in tests.get("test_suites", []):
                lines += ["", f"### {suite['suite']}", ""]
                for tc in suite.get("test_cases", []):
                    priority = tc.get("priority", "medium")
                    emoji = PRIORITY_EMOJI.get(priority, "⚪")
                    category = CATEGORY_LABEL.get(tc.get("category", ""), tc.get("category", ""))
                    lines += [
                        f"#### {tc['id']} {emoji} {tc['name']}",
                        "",
                        f"- **Category:** `{category}`  ",
                        f"- **Priority:** `{priority}`  ",
                        f"- **Precondition:** {tc.get('precondition', '—')}  ",
                        "",
                        "**Steps:**",
                        "",
                    ]
                    for i, step in enumerate(tc.get("steps", []), 1):
                        action = step.get("action", "")
                        target = step.get("target", "")
                        coords = step.get("coords")
                        value = step.get("value")

                        coord_str = f" at `{coords}`" if coords else ""
                        value_str = f' → `"{value}"`' if value else ""
                        lines.append(f"{i}. **{action}** {target}{coord_str}{value_str}")

                    lines += [
                        "",
                        f"**Expected:** {tc.get('expected_result', '—')}",
                        "",
                    ]

            lines += ["---", ""]

        path = os.path.join(self.run_folder, "report.md")
        with open(path, "w") as f:
            f.write("\n".join(lines))
        print(f"  📝 report.md        →  full human-readable report")

    # ── Helpers ──────────────────────────────────────────────────────────────────

    def _count_tests(self, all_results):
        return sum(
            len(suite.get("test_cases", []))
            for r in all_results
            for suite in r.get("tests", {}).get("test_suites", [])
        )

    def _avg_health(self, all_results):
        scores = [
            r["inspector"]["visual_health_score"]
            for r in all_results
            if r.get("inspector", {}).get("visual_health_score") is not None
        ]
        if not scores:
            return "—"
        return round(sum(scores) / len(scores), 1)
