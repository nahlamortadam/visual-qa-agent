# Visual QA Agent

An AI-powered testing agent that crawls any website and automatically generates a complete, structured test suite — happy path, edge cases, negative tests, and security checks — using Gemini vision and DOM analysis.

Built for the [Gemini Live Agent Challenge](https://geminiliveagentchallenge.devpost.com/) · **UI Navigators** category.

---

## What it does

Give it a URL. It crawls every page, visually understands the UI using Gemini multimodal, and outputs a test suite that an automation engineer can run immediately.

```
URL input
    │
    ▼
BrowserTool — crawls all pages (Playwright)
    │             screenshot + DOM elements per page
    ▼
┌─────────────────────────────────────┐
│  Per-page agent pipeline            │
│                                     │
│  SecretaryAgent  →  UI map          │
│  InspectorAgent  →  visual bugs     │
│  TestGenerator   →  test cases      │
└─────────────────────────────────────┘
    │
    ▼
test_suite.json   — all tests (machine-readable)
report.md         — full report (human-readable)
```

---

## Agents

| Agent | Role |
|-------|------|
| `SecretaryAgent` | Maps UI intent and all interactive components with coordinates |
| `InspectorAgent` | Detects visual bugs — overlaps, broken images, layout issues |
| `TestGeneratorAgent` | Generates test cases from screenshot + DOM (multimodal) |
| `ReportWriter` | Aggregates all results into `test_suite.json` and `report.md` |

---

## Output

Every run creates a timestamped folder under `output/`:

```
output/run_YYYYMMDD_HHMMSS/
├── {page}.png                  screenshot
├── {page}_knowledge.json       UI component map
├── {page}_visual.json          visual bug report
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

---

## Setup

### Prerequisites
- Python 3.10+
- A Google Cloud project with Vertex AI enabled
- `gcloud` CLI authenticated (`gcloud auth application-default login`)

### Install

```bash
git clone https://github.com/YOUR_USERNAME/visual-qa-agent.git
cd visual-qa-agent

pip install -r requirements.txt
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
python main.py
```

To scan a different website, change `start_url` in `main.py`:
```python
start_url = "https://your-website.com"
```

---

## Tech stack

- **Gemini 2.0 Flash** — UI understanding, visual inspection, test generation
- **Google GenAI SDK** — Vertex AI integration
- **Playwright** — browser automation and screenshot capture
- **Pillow** — image handling for multimodal prompts
- **Python threading** — parallel agent pipelines per page
