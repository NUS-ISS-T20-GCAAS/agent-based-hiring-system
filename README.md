# Agentic Hiring System

An agent-based, explainable resume screening system built for scalable and auditable hiring decisions.

## Tech Stack
- Python 3.11
- FastAPI
- PostgreSQL
- OpenAI API
- Docker / Docker Compose

## Architecture Principles
- Custom agent framework (no LangChain / LangGraph)
- Stateless agents with shared memory
- Full decision traceability and audit logs
- Deterministic prompts and model configuration

## Supported Scope
- Text-based PDF resumes only
- Multiple predefined job roles
- Chat-style UI (future phase)
- Anonymized real-world resumes

## Local Development
### Build Services Individually
You can build each service separately:

```bash
# Build all services
make build-all

# Or build individual services
make build-frontend
make build-coordinator
make build-resume

# Using docker-compose
make compose-build-all
make compose-build-frontend
# etc.
```

### Run the System
```bash
docker-compose -f infra/docker-compose.yml up --build
```

Or using make:
```bash
make up
```

### GitHub Actions
- **Automatic Builds**: On push/PR, only builds services that have changed files.
- **Manual Builds**: Go to the Actions tab, select "Build Services" or "Build Frontend", click "Run workflow", and specify which services to build (for services workflow).


## To generate tree folder cmd
``` sh
tree -L 3 --gitignore # may need to install 
```