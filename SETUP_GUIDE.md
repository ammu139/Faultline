# ⚡ FAULTLINE — Setup & Deployment Guide

> Works fully out of the box. No API keys, no external services, no GPU required.

---

## Quick Start (2 minutes)

### Prerequisites
- Python 3.11 or higher
- pip

### Step 1: Install

```bash
git clone <repository-url>
cd Faultline-1/faultline_agent
pip install -r requirements.txt
```

### Step 2: Run

```bash
streamlit run app.py
```

Opens at **http://localhost:8501**

Or explicitly:

```bash
python -m streamlit run app.py --server.headless true --server.port 8501
```

Opens at **http://localhost:8501**

That's it. No `.env` configuration needed for the default experience.

---

## What to Try

### 1. Load a Scenario
Click any scenario card on the landing page:
- **🏦 Banking System** — transaction cascades, fraud detection
- **🛒 E-Commerce** — checkout collapse, Redis failures
- **⚙️ CI/CD** — microservices, Kubernetes fragility

Or: select from sidebar dropdown → click **🚀 Analyze**

### 2. Incident Replay (Hero Feature)
- Go to **🎬 Incident Replay** tab
- Select a failure target (e.g., "Core Banking Engine")
- Click **▶ Play**
- Watch the cascade propagate — nodes change color, event log streams, KPIs update

### 3. Ask the Incident Copilot
In the **🧠 Incident Copilot** panel (right side), try:
- `What happens if Redis fails?`
- `Show me the single points of failure`
- `How to fix the vulnerabilities?`
- `Tell me about the payment gateway`
- `What's the risk score?`

The copilot runs real simulations and returns quantified results.

### 4. Inject a Failure
In the sidebar under **💥 Inject Failure**:
- Select a node (e.g., "Payment Gateway")
- Select stress type (e.g., "Load Spike")
- Set intensity (0.8 recommended)
- Click **💥 Inject**
- Check **🔬 Technical Logs** for detailed propagation data

### 5. Explore Tabs
- **📊 Risk & Insights** — SPOFs, criticality scores, recommendations
- **🔬 Technical Logs** — node state table, propagation timelines, failure chains
- **🕸️ System Map** — full dependency graph with metrics

---

## What Works Without LLM

Everything:
- ✅ All 3 scenarios (22-24 nodes each)
- ✅ Incident Replay with animated cascade
- ✅ Failure injection with probabilistic propagation
- ✅ Risk assessment with criticality scores
- ✅ Technical logs with causal failure chains
- ✅ Incident Copilot (rule-based, backed by real simulation data)
- ✅ Monte Carlo simulation (via CLI tools)
- ✅ MCP Server for agent-to-agent integration

---

## Docker (Alternative)

```bash
docker build -t faultline .
docker run -p 8501:8501 faultline
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| Port 8501 in use | `streamlit run app.py --server.port 8502` |
| Slow first load | Normal — graph builds in ~200ms on first run |
| Windows encoding error | Already fixed in codebase |

---

## System Requirements

- Python 3.11+
- ~200MB disk (dependencies)
- No GPU required
- No external API required
- Works on Windows, macOS, Linux

---

---

## Optional: Enable LLM-Powered Responses

To enable the full ADK agent with LLM reasoning (not required for demo):

### Step 1: Configure `.env`

```bash
cp .env.example .env
```

Edit `.env`:
```env
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=http://localhost:6655
LLM_MODEL=gpt-4o
SIMULATION_MODE=false
```

Works with any OpenAI-compatible endpoint (Hyperspace AI, Ollama, vLLM, OpenAI).

### Step 2: Run ADK Agent (CLI)

```bash
# Interactive autonomous agent
python cli.py adk interactive

# Single question
python cli.py adk chat "Analyze the banking system for vulnerabilities"

# Full pipeline workflow
python cli.py adk workflow "ecommerce worst_case"
```

### Step 3: Google Gemini (Alternative)

```env
GOOGLE_API_KEY=your-gemini-key
# Remove OPENAI_* variables
```

The ADK agent uses LiteLLM — any model provider works.