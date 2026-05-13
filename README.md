# Fabric Agents

AI agents for Microsoft Fabric that automate data cleaning, semantic model creation, synthetic data generation, metadata proposal creation, and optimization reviews. Built as [VS Code Agent Skills](https://agentskills.io/) for use with GitHub Copilot in Agent mode.

<img height="150" alt="image" src="https://github.com/user-attachments/assets/853f752b-2b20-487e-8136-03d8f95be967" /><img width="150" alt="image" src="https://github.com/user-attachments/assets/c02c67e2-bf47-401f-bfa1-4aaaadfb4cf0" />



## Agents

### Fabric Data Cleaner

Discovers tables in Fabric lakehouses, analyzes data quality, and generates self-contained PySpark notebooks that clean the data. Deploys notebooks to Fabric, runs them in sequence, and writes results to a `_cleaned` table.

**Cleaning algorithms**: profiling, duplicate detection, null analysis, type validation (Spanish comma decimals), statistical summary, IQR outlier detection, date format validation, Spanish DNI/NIE checksum validation, email/phone format checks.

**Prompt**: `/clean-table orders in my_lakehouse`

### Fabric Semantic Model Creator

Analyzes lakehouse table schemas and sample data to infer a star-schema Power BI semantic model. Classifies tables as fact/dimension, detects relationships via FK/PK matching, generates DAX measures, and produces TMDL files deployable to Fabric.

**Prompt**: `/create-semantic-model all tables in my_lakehouse, My Workspace`

### Fabric Synthetic Data Generator

Designs realistic data schemas from domain templates (retail, healthcare, airlines, citizen incidents, custom), generates synthetic data with referential integrity using `faker`, and uploads Parquet files to Fabric lakehouse tables.

It can also prepare schemas for real-time streaming from the start, deploy a templated Fabric notebook that emits live synthetic fact events to an Eventstream custom endpoint, and keep post-event fields nullable so streaming records match real event lifecycles.

**Prompt**: `/generate-synthetic-data retail data for my_lakehouse`

### Fabric Metadata Creation

Analyzes Fabric lakehouse tables or semantic models and generates reviewable metadata proposals for data stewards and catalog ingestion planning. Suggests descriptions, glossary terms, classifications, Purview-like sensitivity labels, CDE candidates, relationship and lineage hints, data quality rules, and data product groupings with explicit evidence, assumptions, open questions, and confidence levels.

**Prompt**: `/generate-metadata tables in my_lakehouse for steward review`

### Fabric Optimization Review

Reviews Fabric lakehouse tables, data models, semantic models, and full workspaces to find performance issues, modeling anti-patterns, Direct Lake readiness gaps, and AI/agentic readiness improvements. Produces actionable recommendations for Delta table maintenance, V-Order/Z-Order, compaction, partitioning, DAX, relationships, descriptions, synonyms, display folders, and natural-language/Copilot readiness.

**Prompt**: `/review-optimization my_lakehouse in My Workspace`

## Prerequisites

- [VS Code](https://code.visualstudio.com/) with [GitHub Copilot](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot) extension
- [Fabric MCP Server](https://marketplace.visualstudio.com/items?itemName=fabric.vscode-fabric-mcp-server) VS Code extension for workspace/table discovery
- Azure CLI logged in (`az login`) for Fabric REST API access
- Python 3.10+

## Setup

1. Clone this repository
2. Open in VS Code
3. Install the Fabric MCP Server extension
4. Log in to Azure CLI: `az login`
5. The agents create a `.venv` automatically on first run

## Repository Structure

```
.github/
├── agents/
│   ├── fabric-data-cleaner.agent.md        # Data cleaning agent
│   ├── fabric-semantic-model.agent.md      # Semantic model agent
│   ├── fabric-synthetic-data.agent.md      # Synthetic data agent
│   ├── fabric-metadata-creation.agent.md   # Metadata proposal agent
│   └── fabric-optimization-review.agent.md # Optimization review agent
├── prompts/
│   ├── clean-table.prompt.md               # /clean-table entry point
│   ├── create-semantic-model.prompt.md     # /create-semantic-model entry point
│   ├── generate-synthetic-data.prompt.md   # /generate-synthetic-data entry point
│   ├── generate-metadata.prompt.md         # /generate-metadata entry point
│   └── review-optimization.prompt.md       # /review-optimization entry point
└── skills/
    ├── fabric-data-cleaner/
    │   ├── SKILL.md                        # Algorithm reference + gotchas
    │   ├── notebooks/                      # 9 self-contained PySpark notebook templates
    │   ├── references/                     # DNI validation rules
    │   └── scripts/
    │       ├── fabric_notebook.py          # Deploy/run/delete notebooks via REST API
    │       └── validate_notebooks.py       # Validate generated notebooks before deploy
    ├── fabric-semantic-model/
    │   ├── SKILL.md                        # TMDL templates + classification rules
    │   └── scripts/
    │       └── fabric_semantic_model.py    # Deploy/list/delete models + SQL endpoint + table schemas
    ├── fabric-synthetic-data/
    │   ├── SKILL.md                        # Domain templates + generation/streaming rules
    │   ├── notebooks/
    │   │   └── realtime_stream.ipynb       # Eventstream real-time synthetic event template
    │   └── scripts/
    │       └── fabric_synthetic_data.py    # Upload Parquet, load Delta tables, deploy notebooks
    ├── fabric-metadata-creation/
    │   ├── SKILL.md                        # Metadata categories + inference rules
    │   └── scripts/
    │       └── fabric_metadata.py          # Discovery/export + PDF/validation helpers
    └── fabric-optimization-review/
        ├── SKILL.md                        # Optimization rules + recommendation format
        └── scripts/
            └── fabric_optimization_review.py # Discovery + optimization report helpers
```

## How It Works

Each agent follows a phased workflow with clear human-in-the-loop checkpoints where production changes are possible. The metadata creation and optimization review agents are local-only after target selection and produce review artifacts instead of deploying governance or optimization changes.

1. **Discover** — Uses the Fabric MCP Server to find workspaces, lakehouses, and tables
2. **Analyze** — Classifies data and presents findings for user confirmation
3. **Generate** — Creates artifacts locally (notebooks, TMDL files, or Parquet files)
4. **Deploy** — Uploads to Fabric via REST API scripts, deploys optional notebooks, or saves locally
5. **Verify** — Confirms deployment success
6. **Cleanup** — Removes temporary artifacts from Fabric and local workspace

All agents use Python scripts (not raw API calls) for Fabric operations. Scripts authenticate via `DefaultAzureCredential` which picks up your `az login` session.

## Generated Output Directories

These are created at runtime and gitignored:

| Directory | Agent | Contents |
|-----------|-------|----------|
| `cleaning_runs/` | Data Cleaner | Customized PySpark notebooks per table/run |
| `semantic_models/` | Semantic Model | TMDL definition files per model/run |
| `synthetic_data/` | Synthetic Data | Parquet files and optional real-time streaming notebooks per generation run |
| `metadata_proposals/` | Metadata Creation | Proposal JSON/PDF and standalone glossary Markdown/PDF per run |
| `optimization_reviews/` | Optimization Review | Optimization findings and recommendation reports per review run |

Generated files use timestamped folders so multiple runs can be compared without overwriting prior output.

## Spanish Locale Support

All agents are configured for Spanish data:
- Date format: `dd/MM/yyyy`
- Decimal separator: `,` (comma)
- DNI/NIE validation with mod-23 checksum
- Phone numbers: `+34 6XX XXX XXX`
- `faker` locale: `es_ES`
- Semantic model culture: `es-ES`
