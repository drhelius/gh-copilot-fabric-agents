---
name: fabric-metadata-creation
description: "Create reviewable metadata proposals for Microsoft Fabric lakehouse tables and semantic models. Covers schema analysis, concise technical and business descriptions, glossary terms, classifications, Purview-like sensitivity label proposals, PII and sensitive data detection, relationship and lineage hints, data quality rules, CDE candidates, data products, JSON/PDF output, and steward review questions. Use when: metadata creation, data catalog, Purview mapping, glossary inference, data classification, sensitivity labels, stewardship review, governance metadata."
compatibility: "Requires the Fabric MCP Server VS Code extension for interactive discovery when available. Uses Python helper scripts with azure-identity and requests for Fabric discovery/export and markdown plus weasyprint for styled local PDFs. Produces local proposal artifacts only."
---

# Fabric Metadata Creation - Reference

Generates non-destructive metadata proposals for Microsoft Fabric lakehouse tables, files, views, and semantic models. The result is a steward-review package that can later be mapped into a data catalog such as Microsoft Purview, but it must not apply catalog changes automatically.

The agent's core principle is traceability: every suggestion must distinguish metadata explicitly found in the source from metadata inferred by the agent, include a confidence level, and carry assumptions or open questions when evidence is incomplete.

## Global Rules

- **Proposal only.** Never modify Fabric assets, Purview assets, glossary terms, labels, classifications, owners, stewards, retention policies, or access controls.
- **Human review required.** Governance outcomes are suggestions, not decisions.
- **No invented accountability.** Do not invent real owners, stewards, contacts, responsible teams, legal requirements, or compliance decisions. Use `Unknown`, `TBD`, or an open question when not explicit.
- **Evidence labeling.** Every metadata object must include `metadata_source` with one of: `explicit`, `inferred`, or `mixed`.
- **Confidence required.** Every proposal must include `confidence`: `high`, `medium`, or `low`.
- **Assumptions required.** Every inferred proposal should include `assumptions`; use an empty list only when there are no assumptions.
- **Open questions required.** Every asset-level and column-level proposal must include review questions when evidence is incomplete.
- **Conservative language.** Use `candidate`, `suggested`, `likely`, `possible`, or `requires human review` for inferred classifications and sensitivity labels.
- **Structured output.** Generate only the four final artifacts documented below: proposal JSON/PDF and standalone glossary Markdown/PDF.
- **Spanish review documents.** Human-readable artifacts must be written in Spanish. Keep original workspace, lakehouse, table, column, measure, semantic model, and glossary candidate names exactly as they appear in the source; do not translate source identifiers.

## Helper Script

Use [./scripts/fabric_metadata.py](./scripts/fabric_metadata.py) for Fabric discovery/export, PDF rendering, and output validation. The agent must activate `.venv/` before running it.

Install dependencies:

```bash
test -d .venv || python3 -m venv .venv
source .venv/bin/activate
pip install azure-identity requests markdown weasyprint
```

WeasyPrint requires system-level Cairo/Pango libraries. They are pre-installed on many Linux environments; on macOS install Pango with `brew install pango`.

Commands:

```bash
python .github/skills/fabric-metadata-creation/scripts/fabric_metadata.py list-workspaces
python .github/skills/fabric-metadata-creation/scripts/fabric_metadata.py list-items <workspace_id> [<item_type>]
python .github/skills/fabric-metadata-creation/scripts/fabric_metadata.py list-lakehouse-tables <workspace_id> <lakehouse_id>
python .github/skills/fabric-metadata-creation/scripts/fabric_metadata.py get-lakehouse-table <workspace_id> <lakehouse_id> <table_name>
python .github/skills/fabric-metadata-creation/scripts/fabric_metadata.py list-semantic-models <workspace_id> [<model_name>]
python .github/skills/fabric-metadata-creation/scripts/fabric_metadata.py export-semantic-model <workspace_id> <semantic_model_id> <output_dir>
python .github/skills/fabric-metadata-creation/scripts/fabric_metadata.py render-pdf <metadata_proposal.json> <metadata_proposal.pdf>
python .github/skills/fabric-metadata-creation/scripts/fabric_metadata.py render-glossary-md <metadata_proposal.json> <glossary_terms.md>
python .github/skills/fabric-metadata-creation/scripts/fabric_metadata.py render-glossary-pdf <metadata_proposal.json> <glossary_terms.pdf>
python .github/skills/fabric-metadata-creation/scripts/fabric_metadata.py render-markdown-pdf <input.md> <output.pdf>
python .github/skills/fabric-metadata-creation/scripts/fabric_metadata.py validate <output_dir>
```

Use MCP tools first when they are available for interactive discovery. Use the script when MCP does not expose the needed metadata, when exporting semantic model definitions, or when rendering/validating local outputs.

## Output Directory

Save each run to:

```text
./metadata_proposals/{SOURCE_NAME}/{YYYY-MM-DD_HHmmss}/
```

Required files:

| File | Purpose |
|------|---------|
| `metadata_proposal.json` | Compact machine-readable metadata proposal |
| `metadata_proposal.pdf` | Styled A4 proposal PDF rendered from Markdown with WeasyPrint |
| `glossary_terms.md` | Standalone human-readable glossary proposal |
| `glossary_terms.pdf` | Styled A4 glossary PDF rendered from Markdown with WeasyPrint |

Do not generate `metadata_proposal.md`, `metadata_proposal.yaml`, `evidence.json`, or other final artifacts. Temporary discovery/export files may be used while working, but they must not remain in the final output directory.

## Default Proposal PDF Sections

The proposal PDF must present these simplified review sections in order. The JSON is the source of truth; the PDF is the human-readable rendering.

1. Resumen ejecutivo
2. Entrada interpretada
3. Activos y columnas
4. Glosario
5. Sugerencias de gobierno
6. Relaciones, linaje y calidad de datos
7. Supuestos y preguntas abiertas

Both PDFs must include an index/table of contents. Sections and subsections must be numbered. Asset sections must be visually isolated with page breaks, and the asset name must appear in the asset table header. Source names that contain Markdown-looking characters, such as `# Case Updates`, must be rendered as literal names rather than Markdown syntax.

## Metadata Categories

### Asset-Level Metadata

Use these compact fields for databases, schemas, tables, views, files, semantic models, measures, dimensions, and relationship assets when applicable:

```text
asset_name, asset_type, fully_qualified_name, platform, source_system,
database_name, schema_name, object_type, data_domain, data_product,
environment, lifecycle_status, business_description, technical_description,
data_owner, data_steward, glossary_terms, upstream_lineage,
downstream_lineage, source_of_truth, security_notes, quality_notes,
confidence
```

Additional required traceability fields: `metadata_source`, `assumptions`, `open_questions`.

### Column-Level Metadata

Use these compact fields for columns, semantic model columns, calculated columns, measures, and dimensional attributes when applicable:

```text
column_name, business_name, data_type, nullable, key_role,
measure_or_dimension, business_description, technical_description,
semantic_type, classification, sensitivity_label, pii_indicator,
critical_data_element_candidate, derivation_logic, allowed_values,
example_values, quality_rules, relationship_hints, lineage_hints,
masking_recommendation, confidence
```

Additional required traceability fields: `metadata_source`, `assumptions`, `open_questions`.

### Business Glossary Term Metadata

Use these compact fields for suggested business glossary terms:

```text
term_name, definition, synonyms, related_terms, domain, status,
owner_or_steward, associated_assets, associated_columns, confidence,
metadata_source, open_questions
```

Use `status: Proposed` unless an explicit existing glossary status is present.

The glossary must also be published as an independent human-readable output in `glossary_terms.md` and `glossary_terms.pdf`. This glossary is a steward-review artifact, not a Purview import file. It should be readable without opening the full metadata proposal.

Recommended glossary presentation:

1. Title and generation context
2. Summary by domain or subject area
3. Alphabetical term list grouped by domain or subject area
4. For each term: definition, synonyms, related terms, associated assets, associated columns, confidence, metadata source, and open questions
5. Review guidance explaining that terms are proposed and require steward approval

### Classification Metadata

Use these fields for classification proposals:

```text
classification_name, classification_reason, detection_basis, confidence
```

Allowed classification names include, when evidence supports them: `personal data`, `financial data`, `operational data`, `identifier`, `reference data`, `master data`, `transactional data`, `metric`, `dimension`, `audit field`, `system field`, `derived field`.

### Sensitivity Metadata

Use these fields for Purview-like sensitivity label proposals:

```text
suggested_label, label_reason, protection_recommendation, confidence
```

Allowed suggested labels: `Public`, `Internal`, `Confidential`, `Highly Confidential`, `Restricted`.

### Data Quality Metadata

Use these fields for quality rules and profiling recommendations:

```text
quality_dimension, quality_rule, severity, confidence
```

Quality dimensions include: `completeness`, `uniqueness`, `validity`, `accuracy`, `consistency`, `timeliness`, `freshness`, `integrity`, `conformity`, `reasonableness`.

### Lineage and Relationship Metadata

Use these fields for relationship and lineage hints:

```text
upstream_source, downstream_consumer, relationship_or_join_hint, confidence
```

### Critical Data Element Metadata

Use these fields for CDE candidates:

```text
cde_name, business_reason, associated_columns, confidence
```

### Data Product Metadata

Use these fields for suggested data products or domain groupings:

```text
data_product_name, purpose, included_assets, target_consumers,
owner_or_steward, confidence
```

## Evidence and Confidence Rules

### Metadata Source

| Value | Meaning |
|-------|---------|
| `explicit` | Directly present in Fabric metadata, TMDL, schema, annotations, descriptions, names, or user-provided context |
| `inferred` | Deduced from names, data types, relationships, sample values, model structure, or common enterprise patterns |
| `mixed` | Combines explicit evidence with inferred enrichment |

### Confidence Levels

| Confidence | Use When |
|------------|----------|
| `high` | Strong explicit evidence exists, or multiple independent signals agree, such as name pattern plus data type plus sample pattern |
| `medium` | Reasonable inference from names, data types, or model context, but no validating sample or explicit business description |
| `low` | Weak evidence, ambiguous abbreviations, missing samples, unclear domain, or conflicting signals |

Never raise confidence only because a term sounds plausible. Lower confidence when samples, row counts, relationships, or business context are missing.

## Inference Rules

### Asset Type and Domain

Use table/model names, workspace names, lakehouse names, schemas, and measure names to infer candidate domains. Examples:

| Pattern | Suggested Domain or Context |
|---------|-----------------------------|
| `customer`, `client`, `account`, `contact` | Customer, sales, CRM, master data |
| `order`, `invoice`, `payment`, `booking`, `transaction` | Sales, finance, transactional process |
| `product`, `item`, `sku`, `catalog` | Product, inventory, reference/master data |
| `employee`, `staff`, `payroll`, `hr` | Workforce or HR; possible sensitive data |
| `patient`, `diagnosis`, `doctor`, `visit`, `hospital` | Healthcare; possible regulated data |
| `flight`, `passenger`, `airport`, `aircraft` | Airline operations |
| `incident`, `ticket`, `case`, `status`, `priority` | Operations or service management |
| `calendar`, `date`, `time` | Date/time dimension |
| `audit`, `log`, `event`, `telemetry` | Operational, audit, or observability data |

If domain is ambiguous, use `Unknown` or a broad proposed domain and add an open question.

### Descriptions

Generate two descriptions for each asset and column:

- **Technical description**: what the object stores structurally, based on schema and type evidence.
- **Business description**: what the object likely means to a business user, based on names, model context, relationships, and measures.

Descriptions must be concise, deterministic, and free of unsupported claims. For low-confidence descriptions, explicitly say `Candidate description` or `Likely represents`.

### Keys and Relationships

Infer key metadata with these signals:

| Signal | Suggested Metadata |
|--------|--------------------|
| Column named `id`, `{table}_id`, `{entity}_id`, `{entity}_key`, `uuid` | Candidate primary, foreign, natural, or surrogate key depending on context |
| Single non-null unique ID-like column in a dimension table | Candidate primary key |
| Fact table column matching a dimension PK name/type | Candidate foreign key |
| Columns named `code`, `number`, `reference`, `dni`, `nif`, `passport`, `iban` | Candidate natural key or business identifier |
| Integer sequential ID column | Candidate surrogate key |
| Composite repeated columns such as `order_id` + `line_number` | Candidate composite key |

Default cardinality to `many-to-one candidate` only when a transactional/fact-like table points to a reference/dimension-like table. Use `unknown` when there is insufficient evidence.

### Measure and Dimension Detection

| Pattern | Suggestion |
|---------|------------|
| Numeric additive columns: `amount`, `total`, `quantity`, `cost`, `revenue`, `sales`, `importe`, `cantidad` | Metric/measure candidate |
| Descriptive strings: `name`, `description`, `category`, `status`, `type`, `city`, `country` | Dimension attribute candidate |
| DAX measure expression exists | Explicit measure |
| Calculated expression exists | Derived field candidate, include derivation logic |

### Classification Detection

| Pattern | Candidate Classification |
|---------|--------------------------|
| `id`, `_id`, `_key`, `uuid`, `guid`, `code`, `number` | Identifier |
| `email`, `phone`, `mobile`, `telefono`, `address`, `dni`, `nif`, `nie`, `passport`, `name`, `birth_date` | Personal data candidate |
| `iban`, `bank`, `card`, `salary`, `payroll`, `payment`, `invoice`, `amount`, `revenue`, `margin`, `cost`, `price` | Financial data candidate |
| `patient`, `diagnosis`, `medical`, `doctor`, `visit`, `treatment` | Regulated or sensitive data candidate |
| `status`, `category`, `type`, `priority`, `country`, `city`, `currency` | Reference data candidate |
| `created_at`, `updated_at`, `loaded_at`, `ingestion_time`, `batch_id`, `source_file`, `run_id` | Audit or system field |
| `score`, `ratio`, `total`, `average`, `margin`, `age`, `duration`, `days_since` | Derived field or metric candidate |

Do not use regex-only matches as definitive evidence. Describe uncertainty in `classification_reason` for sensitive classifications.

### Sensitivity Label Suggestions

| Suggested Label | Use When |
|-----------------|----------|
| `Public` | Asset appears intended for open/public use and no sensitive indicators are present. Rarely infer this without explicit context. |
| `Internal` | Default for ordinary enterprise metadata without sensitive indicators. |
| `Confidential` | Contains candidate business confidential data, identifiers, contact data, financial values, or internal operational data. |
| `Highly Confidential` | Contains likely PII, financial identifiers, health-related fields, security-relevant fields, or combinations of sensitive attributes. |
| `Restricted` | Contains secrets, credentials, tokens, private keys, strong regulated data indicators, or explicitly restricted labels in source metadata. |

Treat every inferred label above `Internal` as requiring human review.

### Privacy and Sensitive Data Signals

Potential PII and sensitive fields include:

```text
name, first_name, last_name, full_name, email, phone, mobile, address, city,
postal_code, latitude, longitude, dni, nif, nie, ssn, passport, national_id,
tax_id, birth_date, gender, patient_id, diagnosis, medical_record, iban,
bank_account, credit_card, salary, password, secret, token, api_key, private_key,
ip_address, device_id, user_agent
```

Mark these as candidates unless sample values or explicit metadata confirm the pattern.

### Data Quality Rules

Suggest quality rules from type and classification evidence:

| Evidence | Suggested Rule |
|----------|----------------|
| Candidate primary key | Completeness and uniqueness checks, expected threshold 100% |
| Candidate foreign key | Referential integrity check against referenced asset |
| Required business column | Completeness check with agreed null threshold |
| Email/phone/identifier pattern | Validity and conformity checks |
| Date/timestamp column | Freshness, timeliness, and valid range checks |
| Amount/quantity/metric | Reasonableness, non-negative, range, outlier, and aggregation checks |
| Status/category/code | Allowed values and reference set checks |
| Audit field | Presence, monotonicity, ingestion recency, and run consistency checks |

Severity guidance:

| Severity | Use When |
|----------|----------|
| `high` | Key integrity, sensitive fields, CDE candidates, business-critical metrics |
| `medium` | Important dimensions, common reporting filters, relationship fields |
| `low` | Descriptive fields or optional enrichment attributes |

### Critical Data Element Candidates

Suggest a CDE candidate when one or more conditions apply:

- Column is a key identifier used in relationships.
- Column is a financial, operational, compliance, or customer-impacting metric.
- Column appears in a semantic model measure or relationship.
- Column is likely used for regulatory, privacy, security, or executive reporting.
- Column is needed to join important assets or identify master/reference entities.

Always describe CDEs as candidates and avoid definitive CDE status.

### Glossary Term Generation

Create glossary terms by converting physical names to business names and grouping repeated concepts.

Rules:

- Convert snake_case and camelCase to title case business terms.
- Expand common abbreviations only when likely: `id` -> `Identifier`, `qty` -> `Quantity`, `amt` -> `Amount`, `dt` -> `Date`, `cd` -> `Code`, `desc` -> `Description`.
- Do not invent acronyms unless they are present in the source.
- Create related terms from relationship context, such as `Customer`, `Customer Identifier`, and `Customer Segment`.
- Set `owner_or_steward` to `Unknown` or `TBD`, and `status` to `Proposed`, unless explicit.

## Purview-Oriented Mapping

Use this mapping for catalog ingestion planning:

| Proposal Area | Purview-Oriented Target |
|---------------|-------------------------|
| Asset metadata | Data map asset attributes, custom attributes, contacts, collections |
| Business glossary terms | Glossary terms and term relationships |
| Classification proposals | Custom or built-in classifications for review |
| Sensitivity proposals | Microsoft Purview Information Protection label proposal, not applied label |
| Data quality rules | Data quality rule backlog or observability configuration |
| Relationships and lineage hints | Lineage relationships or process mappings for validation |
| CDE candidates | Governance critical data element candidate register |
| Data products | Data product/domain grouping proposal |

Never state that a Purview label or classification has been applied.

## Machine-Readable JSON Schema

The JSON file must follow this compact top-level structure:

```json
{
  "metadata_proposal": {
    "generated_at": "ISO-8601 timestamp",
    "generated_by": "fabric-metadata-creation agent",
    "proposal_version": "1.0",
    "input_interpreted": {},
    "executive_summary": "",
    "assets": [],
    "columns": [],
    "glossary_terms": [],
    "classifications": [],
    "sensitivity_labels": [],
    "critical_data_elements": [],
    "data_products": [],
    "relationships_lineage": [],
    "data_quality_rules": [],
    "assumptions": [],
    "open_questions": []
  }
}
```

Every asset and column object must include `metadata_source`, `confidence`, `assumptions`, and `open_questions`. Other proposal objects must include `metadata_source` and `confidence`. Use `review_required` only when it materially helps prioritize steward review.

## Output Authoring Rules

- Keep `metadata_proposal.json` compact and machine-readable; do not add legacy YAML, Markdown proposal, or evidence files.
- Render `metadata_proposal.pdf` from `metadata_proposal.json` using the helper script's Markdown-to-WeasyPrint renderer.
- Create `glossary_terms.md` as a standalone document that can be reviewed independently from the proposal PDF.
- Render `glossary_terms.pdf` from structured glossary terms using the helper script's Markdown-to-WeasyPrint renderer; do not manually export the PDF.
- Use A4 pages with 1.5cm margins, Segoe UI/Helvetica/Arial fonts, blue headings, zebra-striped tables, and VS Code-style code blocks.
- Write review prose, section titles, field labels, assumptions, questions, and generated descriptions in Spanish.
- Preserve original Fabric identifiers and source values exactly; do not translate table names, column names, measure names, workspace names, lakehouse names, semantic model names, or explicit glossary/source terms.
- Use concise enterprise language. Prefer brief explanations over long generated prose.
- Include confidence and metadata source in every proposal object.

## Validation Rules

Before finishing, validate:

1. `metadata_proposal.json` parses as JSON.
2. `metadata_proposal.pdf` exists and is non-empty.
3. `glossary_terms.md` exists and includes a standalone glossary title.
4. `glossary_terms.pdf` exists and is non-empty.
5. No legacy artifacts exist in the output folder: `metadata_proposal.md`, `metadata_proposal.yaml`, or `evidence.json`.
6. Every asset and column proposal includes `confidence`, `metadata_source`, `assumptions`, and `open_questions`.
7. No real owner, steward, contact, legal obligation, retention policy, access policy, or compliance decision was invented.

Use:

```bash
python .github/skills/fabric-metadata-creation/scripts/fabric_metadata.py validate <output_dir>
```

## Gotchas

- A physical column named `customer_id` is not proof that the field is PII. It is an identifier candidate and may become personal data only when it can identify or link to a person.
- A field named `name` can describe a person, product, department, status, or location. Use surrounding table context before proposing PII.
- Financial measures are often confidential business data even when they are not personal data.
- Health-related names such as `patient`, `diagnosis`, or `treatment` are strong sensitivity signals, but still require human review.
- Semantic model measures often carry business meaning. Use DAX expressions and format strings as explicit evidence for metric descriptions.
- Hidden key columns in semantic models are still governance-relevant and should be included in metadata proposals.
- Semantic model `getDefinition` calls may return `202 Accepted`. The helper must poll the operation and then fetch the operation result payload; the operation status itself does not contain the TMDL parts.
- Do not assign `Public` unless public availability is explicit or strongly implied by context.
- Do not assign legal categories such as GDPR, HIPAA, PCI, or SOX as definitive obligations. Use `possible regulatory review area` only when the source context suggests it.
- If no sample values are available, avoid sample-based claims and reduce confidence.
