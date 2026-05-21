# Decision Memory Layer

Building persistent organizational memory systems for AI-native enterprise decision intelligence.

## Vision

Most enterprise systems track:
- transactions
- workflows
- approvals
- operational states

But organizations rarely preserve:
- why decisions were made
- historical context
- reasoning evolution
- tradeoffs
- operational intent

Decision Memory Layer explores persistent organizational cognition systems.

## Core Hypothesis

Future enterprise intelligence systems will require:
- memory persistence
- temporal reasoning
- decision lineage
- contextual continuity
- organizational cognition

AI systems without memory suffer from operational amnesia.

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (optional, for containerized deployment)

### Local Development

```bash
# Clone the repository
git clone https://github.com/decisiongraph-ai/decision-memory-layer.git
cd decision-memory-layer

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Run the API server
uvicorn decision_memory.api:app --reload

# Run tests
pytest

# Run linter
ruff check src/ tests/
```

### Docker

```bash
# Build and run with Docker Compose
docker compose up --build

# Or build and run directly
docker build -t decision-memory-layer .
docker run -p 8000:8000 decision-memory-layer
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Configuration

| Environment Variable | Default    | Description                  |
|---------------------|------------|------------------------------|
| `DML_DB_PATH`       | `:memory:` | SQLite database file path    |

## Architecture

```
Enterprise Systems -> Event Stream -> Memory Layer -> Knowledge Graph -> Retrieval + Reasoning Layer -> Decision Intelligence
```

### Repository Structure

```
decision-memory-layer/
├── src/
│   └── decision_memory/
│       ├── __init__.py          # Package init
│       ├── models.py            # Pydantic models for decisions, context, relationships
│       ├── memory_store.py      # In-memory + SQLite persistence for decisions
│       ├── temporal.py          # Temporal context tracking (decision evolution over time)
│       ├── knowledge_graph.py   # Lightweight knowledge graph using networkx
│       ├── retrieval.py         # Query interface for decision retrieval
│       └── api.py               # FastAPI REST API
├── tests/
│   ├── test_models.py
│   ├── test_memory_store.py
│   ├── test_temporal.py
│   ├── test_knowledge_graph.py
│   └── test_api.py
├── pyproject.toml               # Modern Python packaging with hatchling
├── Dockerfile
├── docker-compose.yml
└── README.md
```

### Tech Stack

- **Python 3.11+** — modern type hints and async support
- **FastAPI** — high-performance async REST API
- **Pydantic v2** — data validation and serialization
- **SQLite (aiosqlite)** — lightweight async persistence
- **networkx** — knowledge graph for decision relationships
- **pytest** — testing framework

## API Endpoints

### Decisions

| Method   | Endpoint                              | Description                     |
|----------|---------------------------------------|---------------------------------|
| `POST`   | `/decisions`                          | Create a new decision           |
| `GET`    | `/decisions`                          | List decisions (filter by status) |
| `GET`    | `/decisions/{id}`                     | Get a specific decision         |
| `PATCH`  | `/decisions/{id}`                     | Update a decision               |
| `DELETE` | `/decisions/{id}`                     | Delete a decision               |
| `POST`   | `/decisions/search`                   | Search decisions                |
| `GET`    | `/decisions/{id}/history`             | Get decision change history     |
| `GET`    | `/decisions/{id}/relationships`       | Get decision relationships      |
| `GET`    | `/decisions/{id}/related`             | Get related decisions (graph)   |
| `GET`    | `/decisions/{id}/dependencies`        | Get dependency chain            |
| `GET`    | `/decisions/{id}/impact`              | Get impact chain                |

### Relationships

| Method   | Endpoint                    | Description               |
|----------|-----------------------------|---------------------------|
| `POST`   | `/relationships`            | Create a relationship     |
| `GET`    | `/relationships`            | List relationships        |
| `GET`    | `/relationships/{id}`       | Get a specific relationship |
| `DELETE` | `/relationships/{id}`       | Delete a relationship     |

### Other

| Method | Endpoint    | Description   |
|--------|-------------|---------------|
| `GET`  | `/health`   | Health check  |

## MVP Goals

### Decision Persistence
Store:
- decisions
- rationale
- approval context
- operational assumptions
- supporting evidence

### Temporal Context Tracking
Track:
- changing decisions over time
- historical reasoning
- evolving operational states
- organizational learning

### Knowledge Relationships
Map relationships between:
- workflows
- decisions
- stakeholders
- operational outcomes
- enterprise events

### Organizational Intelligence
Enable systems that can:
- recall prior context
- explain historical reasoning
- identify repeated patterns
- support long-term operational cognition

## Enterprise Use Cases

### Executive Decision Intelligence
Persistent strategic decision memory.

### Operational Governance
Historical workflow and approval reasoning.

### AI Copilots
Context-aware enterprise assistants.

### Organizational Learning Systems
Long-term operational cognition.

## Future Roadmap

### Phase 1 — MVP
- Decision storage
- Context persistence
- Basic temporal querying
- Relationship mapping

### Phase 2 — Cognitive Layer
- Knowledge graph integration
- Temporal reasoning
- Cross-workflow context
- Historical decision replay

### Phase 3 — Organizational Cognition
- Autonomous reasoning systems
- Enterprise memory agents
- Long-term operational intelligence
- AI-native organizational memory

## Long-Term Vision

Future enterprises may operate through systems that:
- remember prior decisions
- understand organizational context
- preserve reasoning history
- evolve institutional intelligence
- reduce operational memory loss

## Contributors

- Akash Raj
- Prem Kumar

## Focus Areas

- Organizational memory
- Decision intelligence
- Temporal reasoning
- Enterprise cognition
- AI-native operational systems
