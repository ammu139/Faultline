# Faultline — Agent Architecture & Skills

## Multi-Agent Design

Faultline implements a **multi-agent architecture** using Google ADK 2.0:

### Agent 1: Resilience Engineer (`root_agent`)
- **Role**: Autonomous planner and investigator
- **Model**: Any OpenAI-compatible LLM via LiteLLM
- **Behavior**: Decomposes user goals into investigation plans, selects tools, executes multi-step analysis, synthesizes findings with evidence
- **Tools**: 15 composable function tools for graph exploration, simulation, and optimization

### Agent 2: Insight Generator (`insight_agent` in Workflow)
- **Role**: Specialist analyst that generates structured risk assessments
- **Model**: Same LLM with `output_schema` constraint
- **Behavior**: Receives propagation data, produces typed `InsightOutput` with risk scores, insights, and recommendations
- **Integration**: Final node in the ADK Workflow pipeline

### Agent 3: MCP Server (External Agent Interface)
- **Role**: Exposes Faultline's capabilities to external AI agents
- **Protocol**: Model Context Protocol (stdio-based)
- **Behavior**: Any MCP-compatible client (Claude, Cline, other ADK agents) can invoke Faultline tools
- **Security**: Input validation, rate limiting, sanitization

### Orchestration: ADK Workflow Pipeline
- **Type**: Graph-based workflow (`google.adk.workflow.Workflow`)
- **Flow**: `START → ingest → analyze → stress → propagate → insight_agent`
- **Design**: Deterministic execution with typed function nodes passing structured data

---

## ADK Skills Used

This project was developed using the Google ADK skills suite (`.agent/skills/`):

| Skill | How It Was Applied |
|-------|-------------------|
| `google-agents-cli-adk-code` | Agent definition patterns, FunctionTool design, LiteLLM model configuration, callback patterns |
| `google-agents-cli-workflow` | Development lifecycle, code preservation rules, project structure conventions |
| `google-agents-cli-scaffold` | Project layout (app/ directory, __init__.py exports, .env configuration) |

### Key ADK Patterns Applied

1. **Agent with Tools** — `root_agent` uses plain functions with typed args and docstrings as tools
2. **LiteLLM Integration** — Connects to any OpenAI-compatible endpoint (Hyperspace AI, Ollama, etc.)
3. **Workflow Graph** — Pipeline as a declarative graph with function nodes and LLM agent node
4. **Structured Output** — `insight_agent` uses `output_schema` for typed JSON responses
5. **InMemoryRunner** — Programmatic async execution with session management
6. **Composable Tools** — Small, focused tools that the LLM chains based on its plan

---

## Security Features

Implemented in `faultline_agent/security.py`:

| Feature | Implementation |
|---------|---------------|
| **Input Validation** | `InputValidator` — strips control chars, enforces length limits, blocks injection patterns |
| **Rate Limiting** | `RateLimiter` — token bucket algorithm, 60 req/min sliding window |
| **Audit Logging** | `AuditLogger` — records all actions with timestamps, severity, user context |
| **API Key Management** | `APIKeyManager` — SHA-256 hashed storage, key rotation, revocation |
| **Content Security** | Blocked patterns list (eval, exec, SQL injection, XSS) |

---

## Deployment

### Local Development
```bash
pip install -r requirements.txt
cp .env.example .env
python cli.py adk interactive
```

### Docker
```bash
docker build -t faultline .
docker run -p 8501:8501 --env-file .env faultline
```

### Google Cloud Run
```bash
gcloud run deploy faultline --source . --allow-unauthenticated
```

### ADK Playground (if agents-cli installed)
```bash
cd faultline_agent
agents-cli playground
```

---

## MCP Server Integration

External AI agents can invoke Faultline tools via the Model Context Protocol:

```bash
# Start MCP server
python cli.py mcp
```

Available MCP tools:
- `faultline_load_scenario` — Load a system topology
- `faultline_analyze` — Run structural analysis
- `faultline_inject_failure` — Simulate a failure
- `faultline_get_status` — System health status
- `faultline_list_nodes` — List all components
- `faultline_get_fragility_report` — Full vulnerability report

This enables **agent-to-agent collaboration** — other ADK agents or Claude can call Faultline as a specialist tool.