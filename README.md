# Visual QA Agent

An AI-powered testing agent that crawls any website and automatically generates a complete, structured test suite — happy path, edge cases, negative tests, and security checks — using Gemini vision and DOM analysis.

Built for the [Gemini Live Agent Challenge](https://geminiliveagentchallenge.devpost.com/) · **UI Navigators** category.

---

## What it does

Give it a URL. It crawls every page, visually understands the UI using Gemini multimodal, and outputs a complete test suite that an automation engineer can run immediately.

```
CLI input (URL / credentials)
    │
    ▼
InputAgent — validates URL, suggests one if none provided
    │
    ▼
AuthAgent — detects login form, fills credentials (DOM-first, vision fallback)
    │
    ▼
BrowserTool — BFS crawls all pages (Playwright)
    │             screenshot + DOM elements per page
    ▼
┌─────────────────────────────────────────────┐
│  Per-page agent pipeline (parallel)         │
│                                             │
│  SecretaryAgent ──┐                         │
│                   ├──▶  TestGeneratorAgent  │
│  InspectorAgent ──┘                         │
└─────────────────────────────────────────────┘
    │
    ▼
ReportWriter
    │
    ├── test_suite.json   (machine-readable, all pages)
    └── report.md         (human-readable full report)
```

---

## Agents

| Agent | Role |
|-------|------|
| `InputAgent` | Validates and normalizes the target URL. If no URL is given, suggests a real website (never repeats the same suggestion). |
| `AuthAgent` | Detects login forms using Gemini vision, fills credentials via DOM selectors (falls back to coordinate-based clicks). Also detects mid-crawl auth walls and re-authenticates automatically. |
| `SecretaryAgent` | Maps all interactive UI components with coordinates, labels, and semantic intent. |
| `InspectorAgent` | Detects visual bugs — overlapping elements, broken images, layout issues — with a 1–10 health score. |
| `TestGeneratorAgent` | Generates structured test cases from screenshot + DOM elements (multimodal). Covers happy path, edge case, negative, security, and visual categories. |
| `ReportWriter` | Aggregates all per-page results into `test_suite.json` and `report.md`. |

---

## CLI Usage

```bash
# Scan any website (full site, no limit)
python3 main.py --url https://example.com

# Scan with authentication
python3 main.py --url https://app.example.com --username user@email.com --password yourpassword

# Limit to N pages
python3 main.py --url https://example.com --pages 5

# Let the agent suggest a website for you
python3 main.py
```

### Arguments

| Flag | Default | Description |
|------|---------|-------------|
| `--url` | _(none)_ | Website to test. Omit to let InputAgent suggest one. |
| `--username` | _(none)_ | Login username or email |
| `--password` | _(none)_ | Login password |
| `--pages` | `0` | Max pages to crawl. `0` = full site, no limit. |

---

## Authentication

The agent handles auth automatically when `--username` and `--password` are provided:

1. **Login detection** — AuthAgent uses Gemini vision to find the login form on the start URL
2. **DOM-first fill** — uses Playwright locators (`input[type="email"]`, `input[type="password"]`, etc.) for reliability
3. **Coordinate fallback** — if DOM fill fails, falls back to vision-detected pixel coordinates
4. **Mid-crawl re-auth** — if a login wall appears mid-crawl (session expired, protected route), the agent detects it and re-authenticates automatically before continuing

---

## Persistent URL tracking

The agent remembers which pages it has already tested, per domain, across runs:

- Tested URLs are saved to `.visited_urls.json` after each run
- Future runs on the same domain skip already-tested pages
- The start URL is always re-allowed as the crawl entry point
- Delete `.visited_urls.json` to reset and re-test all pages

---

## Output

Every run creates a timestamped folder under `output/`:

```
output/run_YYYYMMDD_HHMMSS/
├── {page}.png                  screenshot
├── {page}_knowledge.json       UI component map (SecretaryAgent)
├── {page}_visual.json          visual bug report (InspectorAgent)
├── {page}_tests.json           per-page test cases
├── test_suite.json             ALL pages — machine-readable
└── report.md                   full human-readable report
```

### Example test case
```json
{
  "id": "TC-004",
  "name": "Submit login form with empty email",
  "category": "edge_case",
  "priority": "high",
  "precondition": "User is on the login page",
  "steps": [
    { "action": "navigate", "target": "https://example.com/login", "coords": null, "value": null },
    { "action": "click",    "target": "Submit button", "coords": [320, 340], "value": null },
    { "action": "assert",   "target": "Error message", "coords": null, "value": "Email is required" }
  ],
  "expected_result": "Validation error is shown, form is not submitted"
}
```

Test categories: `happy_path` · `edge_case` · `negative` · `security` · `visual`

---

## Setup

### Prerequisites
- Python 3.10+
- A Google Cloud project with Vertex AI API enabled
- `gcloud` CLI authenticated:
  ```bash
  gcloud auth application-default login
  ```

### Install

```bash
git clone https://github.com/YOUR_USERNAME/visual-qa-agent.git
cd visual-qa-agent

pip3 install -r requirements.txt
playwright install chromium
```

### Configure

```bash
cp .env.example .env
```

Edit `.env`:
```
GCP_PROJECT_ID=your-gcp-project-id
```

### Run

```bash
python3 main.py --url https://www.saucedemo.com --username standard_user --password secret_sauce
```

---

## Tech stack

- **Gemini 2.0 Flash** — UI understanding, visual inspection, test generation (multimodal)
- **Google GenAI SDK** — Vertex AI integration
- **Playwright** — browser automation, screenshot capture, DOM evaluation
- **Pillow** — image handling for multimodal prompts
- **Python threading** — parallel per-page agent pipelines + parallel Secretary/Inspector calls
- **python-dotenv** — secrets management
