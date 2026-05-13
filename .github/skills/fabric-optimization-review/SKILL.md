---
name: fabric-optimization-review
description: "Review and optimize data storage, data models, and semantic models in Microsoft Fabric lakehouses. Covers Delta table optimization (V-Order, Z-Order, compaction, partitioning), data model anti-pattern detection, semantic model DAX review, relationship optimization, AI/agentic readiness (descriptions, synonyms, linguistic schema, display folders), workspace audit (Fabric best practices, dimensional modeling, Direct Lake), and actionable recommendation reports. Use when: optimization, performance, review, tuning, best practices, V-Order, Z-Order, partitioning, compaction, DAX optimization, data model review, AI readiness, agentic, NLQ, Copilot, natural language, workspace audit, Direct Lake, dimensional modeling, audit."
compatibility: "Requires the Fabric MCP Server VS Code extension for workspace and table discovery. Uses Fabric REST API for metadata retrieval. Python 3.10+."
---

# Fabric Optimization Review — Reference

Analyzes Microsoft Fabric lakehouse tables, data models, and semantic models to detect performance issues, anti-patterns, and optimization opportunities. Produces actionable recommendations with severity, effort, and expected impact.

## Review Categories

The agent performs three independent review tracks. The user can request one, several, or all:

| Track | Target | What It Checks |
|-------|--------|----------------|
| **Data Storage** | Lakehouse Delta tables | File sizes, compaction, partitioning, V-Order, Z-Order, small files, schema evolution |
| **Data Model** | Lakehouse table relationships | Normalization, star-schema compliance, redundant columns, key integrity, naming conventions |
| **Semantic Model** | Power BI semantic models (TMDL) | DAX measure quality, relationship cardinality, hidden columns, implicit measures, format strings, role-playing dimensions |
| **AI & Agentic Readiness** | Semantic models + lakehouse tables | Descriptions, synonyms, linguistic schema, display folders, naming conventions, pre-computed measures, column visibility for AI/NLQ/Copilot |
| **Workspace Audit** | Full workspace | Fabric best practices, dimensional modeling compliance, Direct Lake readiness, item organization, capacity usage, pipeline health |

## Data Storage Optimization Rules

### Small File Detection

Delta tables with many small files degrade read performance. Fabric uses V-Order by default but files still fragment from frequent small appends.

| Metric | Threshold | Severity | Recommendation |
|--------|-----------|----------|----------------|
| Avg file size < 32 MB | < 32 MB | High | Run `OPTIMIZE` to compact files |
| File count > 1000 per partition | > 1000 | High | Run `OPTIMIZE` with bin-packing |
| Avg file size < 8 MB | < 8 MB | Critical | Immediate compaction required; rethink ingestion batch size |

### Partitioning Assessment

| Pattern | Severity | Recommendation |
|---------|----------|----------------|
| Table > 1 GB with no partitioning | Medium | Consider partitioning by date or high-cardinality filter column |
| Partition column with > 10,000 distinct values | High | Over-partitioned — creates too many small folders. Choose a coarser grain (year-month vs date) |
| Partition column with < 5 distinct values | Low | Under-partitioned — minimal benefit. Consider removing partitioning |
| Partition column not used in common filters | Medium | Partitioning on non-filter columns wastes metadata. Change to a commonly filtered column |

### V-Order and Z-Order

| Check | Detection | Recommendation |
|-------|-----------|----------------|
| V-Order not enabled | Table properties lack `delta.parquet.vorder.enabled = true` | Enable V-Order: `ALTER TABLE {table} SET TBLPROPERTIES ('delta.parquet.vorder.enabled' = 'true')` |
| Z-Order not configured on query-heavy columns | No `ZORDER BY` in OPTIMIZE history | Apply `OPTIMIZE {table} ZORDER BY ({columns})` for frequently filtered/joined columns |
| Z-Order on > 4 columns | OPTIMIZE with > 4 ZORDER columns | Z-Order effectiveness degrades beyond 3-4 columns. Prioritize the most selective ones |

### Table Maintenance

| Check | Detection | Recommendation |
|-------|-----------|----------------|
| No OPTIMIZE in last 7 days | Delta log has no OPTIMIZE commits recently | Schedule regular `OPTIMIZE` runs |
| Vacuum not run / retention > 7 days | `delta.deletedFileRetentionDuration` > 7 days | Run `VACUUM {table} RETAIN 168 HOURS` to reclaim storage |
| Stats collection stale | Column-level stats absent or outdated | Run `ANALYZE TABLE {table} COMPUTE STATISTICS FOR ALL COLUMNS` |
| Too many Delta log entries | > 1000 log files without checkpoint | Force checkpoint: table properties `delta.checkpointInterval` |

### Schema & Data Type Optimization

| Pattern | Severity | Recommendation |
|---------|----------|----------------|
| String columns storing only integers | Medium | Cast to `INT`/`LONG` — smaller footprint, faster scans |
| String columns storing only dates | Medium | Cast to `DATE`/`TIMESTAMP` — enables predicate pushdown |
| `DOUBLE` for currency/money values | Low | Use `DECIMAL(18,2)` for exact arithmetic |
| Wide tables with > 50 columns | Low | Consider vertical partitioning (split into related tables) |
| Unused columns (null > 95%) | Medium | Consider dropping or archiving — reduces scan I/O |

## Data Model Review Rules

### Star Schema Compliance

| Anti-Pattern | Detection | Severity | Recommendation |
|-------------|-----------|----------|----------------|
| Snowflake dimensions | Dimension table has FK to another dimension | Medium | Flatten into single dimension for better query performance |
| Flat/denormalized mega-table | Single table with > 30 columns mixing measures and attributes | High | Normalize into fact + dimension tables |
| Missing date dimension | Fact table has date columns but no dedicated date/calendar table | High | Create a date dimension for time intelligence |
| Fact-to-fact relationships | Two fact tables joined directly | High | Introduce shared dimensions (conformed dimensions) |
| Bridge tables without clear purpose | Many-to-many junction tables | Medium | Verify necessity; simplify if possible |

### Key & Relationship Integrity

| Check | Detection | Recommendation |
|-------|-----------|----------------|
| No defined primary key | Dimension table has no unique column identified | Define a PK to enable relationship validation |
| Composite keys | Joins require multiple columns | Consider surrogate integer keys for simpler joins |
| Orphan foreign keys | FK values not found in dimension PK | Data quality issue — clean orphans or add "Unknown" dimension member |
| Circular relationships | A → B → C → A | Redesign to eliminate cycles; causes ambiguous query paths |
| Bidirectional relationships | Cross-filter in both directions | Use single direction unless absolutely required (performance + ambiguity risk) |

### Naming Convention Review

| Pattern | Severity | Recommendation |
|---------|----------|----------------|
| Inconsistent casing (mix of camelCase, snake_case, PascalCase) | Low | Standardize to one convention (prefer `snake_case` for Spark/lakehouse) |
| Table names without prefix (`fact_`, `dim_`) | Low | Add prefixes for clarity in large models |
| Ambiguous column names (`id`, `name`, `value`) | Medium | Qualify with table context (`customer_id`, `product_name`) |
| Reserved word column names (`date`, `order`, `table`) | Low | Rename to avoid query issues (`order_date`, `order_number`) |

## Semantic Model Review Rules

### DAX Measures

| Anti-Pattern | Detection | Severity | Recommendation |
|-------------|-----------|----------|----------------|
| Implicit measures | `discourageImplicitMeasures` is false or missing | High | Set `discourageImplicitMeasures` in model.tmdl and create explicit DAX measures |
| SUM on non-additive columns | `SUM()` on ratio, percentage, or average columns | High | Use `AVERAGE()`, `DIVIDE()`, or weighted calculations |
| Duplicate measures | Two measures with identical DAX expressions | Medium | Consolidate to a single measure |
| Missing COUNTROWS | Fact table without a row-count measure | Low | Add `COUNTROWS('{table}')` as base metric |
| Unformatted measures | Measures without `formatString` | Medium | Add format strings (`#,##0`, `#,##0.00`, `0.0%`) |
| Time intelligence without DATEADD/SAMEPERIODLASTYEAR | Manual date calculations instead of DAX time functions | Medium | Use `DATEADD`, `SAMEPERIODLASTYEAR`, `TOTALYTD` for correct time intelligence |
| CALCULATE without explicit filter removal | Nested CALCULATE without REMOVEFILTERS | Low | Review filter context — may produce unexpected results |

### Relationship Configuration

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| Missing relationships | Matching key columns with no defined relationship | High | Add the relationship (many-to-one, single direction) |
| Wrong cardinality | Many-to-many where many-to-one is correct | High | Fix cardinality — many-to-many bypasses engine optimizations |
| Both-direction cross-filter | `crossFilteringBehavior: bothDirections` without a bridge table | Medium | Use single direction; both-direction causes ambiguity and performance issues |
| Role-playing dimensions | Same dimension used for multiple relationships (e.g., date table for order_date and ship_date) | Medium | Use `USERELATIONSHIP()` in measures for inactive relationships; document clearly |
| Inactive relationships not used | Inactive relationship exists but no measure uses `USERELATIONSHIP` | Low | Either activate or remove the unused relationship |

### Column Configuration

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| ID/key columns visible | `isHidden: false` on FK/PK columns | Medium | Hide technical columns from report view |
| `summarizeBy` not set to `none` | Non-measure columns with default aggregation | Medium | Set `summarizeBy: none` to prevent implicit measures |
| Missing `isKey: true` | Dimension PK not marked as key | Low | Mark PK columns as `isKey: true` for VertiPaq optimization |
| Data type mismatch | Relationship columns with different TMDL types | High | Align types — mismatches cause conversion overhead |

### Locale & Formatting

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| Missing culture | No `culture` in model.tmdl | Medium | Add `culture: es-ES` (or target locale) |
| Wrong format strings for locale | Using `.` as decimal in Spanish locale | Low | Use `#.##0,00` for es-ES (dot = thousands, comma = decimals) |
| Missing `sourceQueryCulture` | Not set in model.tmdl | Low | Add `sourceQueryCulture: es-ES` to match data source locale |

## AI & Agentic Readiness Rules

These rules evaluate how well a semantic model (and its underlying data) is prepared for consumption by AI agents, Copilot, natural language queries (NLQ), and other agentic interfaces. A model optimized for human report builders is NOT automatically optimized for AI — AI needs richer metadata, unambiguous naming, and pre-computed measures to generate correct answers.

### 1. Table Descriptions

Every table must have a `description` in TMDL that explains its purpose, grain (what one row represents), and key relationships.

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| Table without description | `description` property missing or empty in table TMDL | High | Add description explaining purpose, grain, and relationships. Example: `"Fact table of individual customer support calls. One row = one call. Joins to dim_agent, dim_customer, dim_date via FK columns."` |
| Description too short (< 20 chars) | Description exists but is trivially short | Medium | Expand with grain, relationships, and business context |
| Description is technical jargon | Description uses only internal/database terms | Medium | Rewrite in business language that an AI can interpret for end users |

TMDL example:
```tmdl
table 'fact_calls'
	description: "Fact table recording individual customer support calls. One row represents a single call. Grain: call_id. Joins to dim_agent (agent handling the call), dim_customer (caller), dim_date (call date), dim_product (product discussed)."
```

### 2. Measure Descriptions

Every DAX measure must have a `description` explaining what it calculates, its units, when to use it, and any caveats.

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| Measure without description | `description` missing on measure | High | Add description with calculation logic, units, and usage guidance |
| Description missing units | Description doesn't mention currency, %, seconds, count, etc. | Medium | Specify units explicitly: "in euros (€)", "as percentage (0-100)", "in seconds" |
| Complex measure without usage guidance | CALCULATE/FILTER/time-intelligence measure with no context | Medium | Explain when to use vs. similar measures. Example: "Use for YTD comparison. For month-only, use [Revenue Monthly]." |

TMDL example:
```tmdl
measure 'Average Handle Time' =
	AVERAGE('fact_calls'[duration_seconds])
	description: "Average duration of customer calls in seconds. Includes hold time. Use for operational efficiency analysis. For calls without hold time, use [Avg Talk Time]."
	formatString: #,##0.0
```

### 3. Column Descriptions

At minimum, describe all foreign key columns, amount/currency columns, coded/enumerated columns, and any column whose name is ambiguous.

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| FK column without description | Column ending in `_id`/`_key` with no description | High | Describe what it references: "Foreign key to dim_agent. Join on agent_id to get agent name and team." |
| Amount/currency column without description | Numeric column with `amount`, `total`, `price`, `importe`, `precio` in name, no description | Medium | Specify currency, tax inclusion, sign convention: "Net revenue in EUR, excluding VAT. Positive = income, negative = refund." |
| Coded/enum column without description | Column with low cardinality (< 20 distinct values) and no description | Medium | List possible values and meanings: "Call outcome code: 'R' = Resolved, 'E' = Escalated, 'A' = Abandoned, 'C' = Callback scheduled." |
| Date column without description | Date/timestamp column with no description | Low | Specify timezone, business meaning: "Date and time the call was answered by an agent (UTC). NULL if call was abandoned before pickup." |

### 4. Synonyms & Annotations

Add synonyms so AI can map natural language terms (in any language) to the correct tables, columns, and measures. Critical for multilingual environments.

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| No synonyms on any table | No `annotation` with synonym content in TMDL | High | Add synonyms for each table in all relevant languages. Example: fact_calls → "llamadas", "calls", "phone calls", "tickets telefónicos" |
| Measures without synonyms | Measures have no alternative names | Medium | Add natural-language aliases: "Average Handle Time" → "AHT", "duración media", "tiempo medio de gestión" |
| Columns without synonyms | Key business columns lack aliases | Medium | Add synonyms for columns users ask about: "agent_name" → "nombre del agente", "rep", "representative" |
| Acronyms not expanded | Measures/columns use acronyms without synonyms | Medium | Map acronyms: "AHT" → "Average Handle Time", "FCR" → "First Call Resolution" |

TMDL synonym example (via extended properties or annotations):
```tmdl
table 'fact_calls'
	annotation Synonyms = ["llamadas", "calls", "phone calls", "registros de llamadas"]

	column agent_name
		annotation Synonyms = ["agente", "representante", "rep", "agent"]

	measure 'Total Calls' = COUNTROWS('fact_calls')
		annotation Synonyms = ["número de llamadas", "call count", "total llamadas", "volumen"]
```

### 5. Display Folders

Group measures into logical `displayFolder` categories so AI agents can discover related measures and present coherent answers.

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| No displayFolder on any measure | All measures are at root level | Medium | Group into business domains: "Operativo", "Financiero", "Calidad", "Cliente", "Tiempo" |
| Inconsistent folder naming | Mix of languages, casing, or granularity | Low | Standardize folder names across all tables |
| Too many measures at root | > 10 measures without displayFolder | Medium | Organize into folders — AI uses folder context to disambiguate similar measures |

Recommended folder structure:
```
Operativo/          → call volume, handle time, occupancy, utilization
Financiero/         → revenue, cost, margin, discounts
Calidad/            → FCR, CSAT, NPS, quality scores
Cliente/            → churn, lifetime value, satisfaction
Tiempo/             → YTD, MoM, QoQ, rolling averages
Objetivos/          → targets, KPI thresholds, variances
```

TMDL example:
```tmdl
measure 'Total Calls' = COUNTROWS('fact_calls')
	displayFolder: Operativo

measure 'Revenue' = SUM('fact_calls'[revenue])
	displayFolder: Financiero

measure 'CSAT Score' = AVERAGE('fact_surveys'[score])
	displayFolder: Calidad
```

### 6. Format Strings

Every measure and numeric column must have an appropriate `formatString`. AI agents use format strings to present results correctly and to infer the semantic type of a value.

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| Currency measure without currency symbol | Measure with `amount`/`revenue`/`price` but no `€`/`$` in formatString | Medium | Use `€#.##0,00` (es-ES) or `$#,##0.00` (en-US) |
| Percentage measure without % | Measure calculating ratios/rates but formatString lacks `%` | Medium | Use `0.0%` or `#,##0.0%` |
| Duration without unit format | Measure in seconds/minutes with plain numeric format | Medium | Use `#,##0.0` with description clarifying unit, or format as `HH:MM:SS` via DAX FORMAT() |
| Integer measure with decimals | Count/quantity measure showing decimal places | Low | Use `#,##0` for counts, `#.##0` for es-ES |
| Date columns without format | Date displayed in default format | Low | Set explicit format: `dd/MM/yyyy` for es-ES |

### 7. Technical Column Visibility

Hide all columns that an AI agent or end user should never filter/slice by directly. AI should use descriptive columns (names, labels) not technical IDs.

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| FK ID columns visible | Columns ending in `_id`/`_key` with `isHidden: false` | High | Set `isHidden: true` — AI must filter by `agent_name`, not `agent_id` |
| Surrogate keys visible | Auto-increment or UUID columns exposed | High | Hide — these have no business meaning |
| ETL/audit columns visible | Columns like `created_at`, `updated_by`, `batch_id`, `row_hash` | Medium | Hide — irrelevant for analytical queries |
| Source system columns visible | Columns like `source_system`, `legacy_code`, `migration_flag` | Medium | Hide unless explicitly needed for analysis |
| Technical columns in dimension tables | Internal keys alongside descriptive columns | Medium | Only expose descriptive columns; hide all technical plumbing |

TMDL example:
```tmdl
column agent_id
	dataType: int64
	isHidden: true
	isKey: false
	summarizeBy: none
	description: "FK to dim_agent. Hidden — use agent_name for filtering."

column agent_name
	dataType: string
	isHidden: false
	description: "Name of the support agent. Use this column to filter or group by agent."
```

### 8. Display Names & Naming Conventions

AI agents present column and measure names directly to users. Technical names like `call_date` or `avg_ht_sec` are confusing. Use friendly display names.

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| Column uses snake_case without display name | Column name contains underscores and no `displayName` override | Medium | Add friendly display name: `call_date` → "Fecha Llamada", `agent_name` → "Nombre Agente" |
| Measure uses abbreviations | Measure name has acronyms or short forms | Medium | Use full business names: `Avg HT` → "Tiempo Medio de Gestión" |
| Mixed language in names | Some names in English, others in Spanish | Low | Standardize to the model's primary language; use synonyms for the other |
| Table names not user-friendly | Tables exposed as `fact_calls` or `dbo_sales` | Low | Consider display names: "Llamadas" or "Ventas" for user-facing contexts |

### 9. Pre-Computed Measures for AI

AI agents perform best with pre-computed measures they can use directly, rather than needing to compose complex DAX on the fly. Add common derived metrics.

| Missing Pattern | Detection | Severity | Recommendation |
|----------------|-----------|----------|----------------|
| No time-comparison measures | No YoY, MoM, QoQ, or YTD measures | High | Add: `[Revenue YTD]`, `[Revenue vs PY]`, `[Revenue MoM %]` using `TOTALYTD`, `SAMEPERIODLASTYEAR`, `DATEADD` |
| No ratio/efficiency measures | Only raw SUM/COUNT, no derived ratios | High | Add: `[Revenue per Call]`, `[Cost per Resolution]`, `[Calls per Agent]` |
| No percentage measures | Absolute values only, no share/mix | Medium | Add: `[% Resolved First Call]`, `[Agent Utilization %]`, `[Revenue Share %]` |
| No ranking measures | No RANKX-based measures | Medium | Add: `[Agent Rank by Revenue]`, `[Product Rank by Volume]` for top-N questions |
| No moving averages | No trend smoothing measures | Low | Add: `[Revenue 7-Day Avg]`, `[Calls 30-Day Moving Avg]` for trend analysis |
| No target/variance measures | No comparison to goals | Medium | Add: `[Revenue vs Target]`, `[Target Achievement %]` if target data exists |
| No cumulative measures | No running totals | Low | Add: `[Cumulative Revenue]`, `[Running Total Calls]` for progress tracking |

Pre-computed measures help AI agents answer questions like "How are we doing vs last year?" or "Who is the top agent?" without composing DAX.

### 10. Linguistic Schema (Q&A / NLQ)

Configure the Power BI Q&A linguistic schema to enable natural language queries. This directly impacts Copilot and any NLQ interface.

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| No linguistic schema configured | Model has no Q&A linguistic schema | High | Create a linguistic schema YAML defining entities, attributes, relationships, and phrasings |
| Synonyms not in linguistic schema | Synonyms only in annotations, not in Q&A config | Medium | Mirror synonyms into the linguistic schema for Q&A engine consumption |
| No relationship phrasings | Relationships not described with natural language verbs | Medium | Add phrasings: "agent **handles** calls", "customer **places** calls", "call **occurs on** date" |
| No attribute phrasings | Columns not described as attributes of entities | Medium | Add: "call **has a** duration", "agent **has a** name", "customer **has a** segment" |
| Missing noun synonyms | Q&A doesn't understand domain terms | Medium | Add noun definitions: "AHT" = "average handle time", "FCR" = "first call resolution" |
| No verb-based phrasings for measures | Q&A can't interpret action-based queries | Medium | Add: "**calculate** revenue", "**show** average handle time", "**count** calls" |

Linguistic schema YAML example:
```yaml
Entities:
  - Name: Call
    Table: fact_calls
    Synonyms: [llamada, call, phone call, ticket]
    Attributes:
      - Name: Duration
        Column: duration_seconds
        Synonyms: [duración, handle time, call length]
      - Name: Date
        Column: call_date
        Synonyms: [fecha, when, call date]

Relationships:
  - Name: AgentHandlesCall
    Phrasing: "{agent} handles {call}"
    ForeignKey: fact_calls.agent_id
    PrimaryKey: dim_agent.agent_id

Phrasings:
  - Type: Attribute
    Entity: Call
    Attribute: Duration
    Phrasing: "{call} has a {duration}"
  - Type: Verb
    Subject: Agent
    Verb: handles
    Object: Call
```

### 11. Data Granularity & Aggregation Tables

AI queries often need aggregated answers. Pre-aggregated tables or aggregation-aware models reduce response time and improve accuracy.

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| Only detail-level fact table | Fact table has millions of rows, no pre-aggregations | Medium | Create aggregation tables (daily/weekly/monthly summaries) for common query patterns |
| No summary dimension attributes | Dimensions lack hierarchy levels (e.g., City → Region → Country) | Medium | Add rolled-up attributes for AI to answer at different granularities |
| Missing calendar hierarchies | Date dimension without Year → Quarter → Month → Week → Day | Medium | Add standard calendar hierarchies for time-based drill-down |

### 12. Data Documentation for Context Grounding

Beyond TMDL metadata, provide additional context that AI agents can use for grounding and disambiguation.

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| No business glossary | No annotation or external reference defining business terms | Medium | Create a glossary annotation: key metrics definitions, business rules, calculation methodology |
| No data freshness indicator | No description of update frequency or latency | Low | Document in table description: "Updated daily at 06:00 UTC. Data latency: T-1." |
| No known limitations documented | No caveats about data coverage or quality | Low | Document in description: "Excludes internal test calls. Weekend data may have 2-hour delay." |
| No example questions | No annotation with sample natural-language queries | Low | Add annotation with 5-10 example questions the model can answer: "¿Cuántas llamadas atendió el agente X este mes?" |

Example questions annotation:
```tmdl
table 'fact_calls'
	annotation ExampleQuestions = [
		"¿Cuántas llamadas hubo ayer?",
		"¿Cuál es el tiempo medio de gestión por agente?",
		"Top 5 agentes por volumen de llamadas este mes",
		"¿Cuál es la tasa de resolución en primera llamada?",
		"Comparar ingresos de este trimestre con el anterior",
		"¿Qué productos generan más llamadas de soporte?"
	]
```

### AI Readiness Scoring

After evaluating all rules in this section, compute an **AI Readiness Score** (0-100%) for the model:

| Component | Weight | Criteria |
|-----------|--------|----------|
| Table descriptions | 15% | All tables have descriptions with grain and relationships |
| Measure descriptions | 15% | All measures have descriptions with units and usage |
| Column descriptions | 10% | All FKs, amounts, and coded columns described |
| Synonyms | 15% | Tables, key columns, and measures have multilingual synonyms |
| Display folders | 5% | Measures organized in logical folders |
| Format strings | 5% | All numeric measures have appropriate format strings |
| Column visibility | 10% | All technical columns hidden |
| Naming conventions | 5% | Friendly display names, consistent language |
| Pre-computed measures | 10% | Time comparisons, ratios, rankings available |
| Linguistic schema | 5% | Q&A schema with phrasings and synonyms configured |
| Documentation | 5% | Glossary, freshness, limitations, example questions |

Score interpretation:
- **90-100%**: Production-ready for AI/Copilot — model is fully grounded
- **70-89%**: Usable with caveats — AI will sometimes misinterpret queries
- **50-69%**: Significant gaps — AI will frequently generate wrong answers
- **< 50%**: Not ready — AI usage will produce unreliable results

## Workspace Audit Rules

A comprehensive audit of a Fabric workspace evaluating Fabric platform best practices, dimensional modeling quality, and Direct Lake readiness. This is a holistic review that combines findings from other tracks with Fabric-specific governance and architecture rules.

### Fabric Best Practices

#### Workspace Organization

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| No naming convention for items | Items have inconsistent prefixes/suffixes (mix of `rpt_`, `Report_`, no prefix) | Medium | Adopt a standard: `LH_` (lakehouse), `SM_` (semantic model), `NB_` (notebook), `PL_` (pipeline), `RPT_` (report) |
| Dev/test items in production workspace | Items with `test`, `dev`, `tmp`, `copia`, `backup` in name | High | Move to a separate dev workspace; use deployment pipelines for promotion |
| No workspace description | Workspace has no description | Low | Add a description explaining purpose, team ownership, and data domains |
| Too many items (> 50) | Workspace contains excessive items | Medium | Split by domain or team; large workspaces are hard to govern |
| No deployment pipeline configured | No pipeline linking dev → test → prod workspaces | Medium | Configure Fabric deployment pipelines for safe promotion of artifacts |
| Mixed ownership | Items owned by individual users instead of service principal/group | Medium | Transfer ownership to a service principal or shared admin group |

#### Capacity & Performance Governance

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| Workspace not assigned to a capacity | No capacity binding | Critical | Assign to a Fabric capacity — items won't run without it |
| Using shared capacity for production | Workspace on shared (non-dedicated) capacity | High | Move to dedicated capacity (F64+) for predictable performance and SLAs |
| No refresh schedule on semantic models | Semantic models with no automatic refresh | Medium | Configure scheduled refresh aligned with data pipeline completion |
| Lakehouse without scheduled maintenance | No OPTIMIZE/VACUUM automation | Medium | Create a notebook + pipeline that runs OPTIMIZE weekly and VACUUM monthly |
| Long-running notebook executions | Notebooks timing out or running > 30 minutes | Medium | Review Spark configuration; consider partitioning, caching, or pre-aggregation |

#### Security & Governance

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| No workspace roles defined | Only admin + viewer, no contributor/member granularity | Medium | Define roles: Admin (platform team), Member (developers), Contributor (ETL), Viewer (consumers) |
| Sensitive data without RLS | Tables with PII/financial data and no Row-Level Security in semantic model | High | Implement RLS in the semantic model; use `USERNAME()` or `USERPRINCIPALNAME()` filters |
| No sensitivity labels | No Microsoft Purview sensitivity labels applied | Low | Apply sensitivity labels per data classification policy |
| Direct lakehouse access without controls | Users querying lakehouse SQL endpoint directly without governance | Medium | Use semantic models as the governed access layer; restrict direct SQL endpoint access |

### Dimensional Modeling Compliance

#### Star Schema Validation

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| No clear fact/dimension separation | Tables not identifiable as fact or dimension by name or structure | High | Restructure into explicit star schema: `fact_` prefix for transactional tables, `dim_` for reference |
| Fact table contains descriptive attributes | Fact table has string columns with names, descriptions, categories stored directly | High | Extract to dimension tables; keep only FK references + measures in facts |
| Dimension table with measure columns | Dimension has numeric additive columns (amounts, totals) | High | Move measures to fact table or create a factless fact for those metrics |
| No conformed dimensions | Same entity (customer, product, date) duplicated across multiple fact tables with different structures | High | Create conformed dimensions shared across all facts for consistent slicing |
| Missing surrogate keys | Dimensions use natural/business keys as PK | Medium | Add integer surrogate keys for performance and change management (SCD) |
| No Slowly Changing Dimension handling | Dimension records overwritten with no history | Medium | Implement SCD Type 2 (start_date/end_date/is_current) for critical dimensions |
| Calendar table missing fiscal periods | Date dimension only has calendar dates, no fiscal year/quarter | Medium | Add fiscal periods, holidays, working days for business reporting |
| Junk dimensions not consolidated | Multiple low-cardinality flag columns in fact table | Low | Consolidate into a single junk dimension to reduce fact table width |

#### Grain & Granularity

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| Mixed grain in fact table | Some rows at daily level, others at monthly (or order header + order line mixed) | Critical | Separate into distinct fact tables at consistent grain |
| Fact table without clear grain | Cannot determine what one row represents | High | Document the grain explicitly; if ambiguous, restructure |
| Pre-aggregated fact without detail | Only summary-level fact exists with no detail backup | Medium | Keep detail-level fact for drill-through; add aggregation tables separately |

#### Relationship Patterns

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| Many-to-many without bridge table | Direct M:N relationship between two tables | High | Create a bridge/junction table to properly model the M:N relationship |
| Multiple active relationships to same table | Two active relationships from fact to same dimension | High | Make one inactive; use `USERELATIONSHIP()` in measures for the secondary path |
| Self-referencing dimension without parent-child | Hierarchy column (manager_id → employee_id) not modeled | Medium | Implement parent-child hierarchy with PATH/PATHITEM DAX functions |
| Circular dependency in relationships | A → B → C → A path exists | Critical | Redesign to eliminate cycles; consider role-playing or bridge patterns |

### Direct Lake Readiness

Direct Lake is Fabric's highest-performance mode for semantic models — it reads directly from Delta/Parquet files in OneLake without data movement. However, it has strict requirements.

#### Prerequisites & Compatibility

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| Semantic model uses Import mode | Model partitions show `mode: import` or explicit M queries with transformations | High | Convert to Direct Lake: remove transformations, ensure lakehouse tables are query-ready |
| Semantic model uses DirectQuery to SQL endpoint | Partitions use `Sql.Database()` with `mode: directQuery` | Medium | Consider Direct Lake for better performance if data fits within guardrails |
| Tables not in Delta format | Lakehouse contains CSV/Parquet files not loaded as Delta tables | Critical | Convert to Delta tables: `spark.read.parquet(...).write.format("delta").saveAsTable(...)` |
| Data transformations in partition expressions | M/Power Query in partition does joins, filters, or calculations | High | Move all transformations upstream to the lakehouse (notebooks/pipelines); Direct Lake requires clean passthrough |
| Lakehouse and semantic model in different workspaces | Model references tables in a different workspace's lakehouse | Medium | Place in same workspace or use shortcuts; cross-workspace Direct Lake has limitations |

#### Direct Lake Guardrails

Direct Lake has capacity-dependent limits. If exceeded, the model falls back to DirectQuery (performance cliff).

| Guardrail | F2 | F64 | F128+ | What Happens |
|-----------|-----|------|-------|-------------|
| Max tables per model | 500 | 500 | 500 | Model creation fails |
| Max columns per table | 500 | 500 | 500 | Table skipped |
| Max rows per table | 300M | 1.5B | 3B+ | Fallback to DirectQuery |
| Max model size on disk | 10 GB | 40 GB | 80 GB+ | Fallback to DirectQuery |
| Max columns per model | 2,000 | 2,000 | 2,000 | Model creation fails |

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| Table exceeds row limit for capacity | Row count > capacity guardrail | Critical | Partition the table, reduce historical depth, or upgrade capacity SKU |
| Model size exceeds capacity guardrail | Total Delta file size > model size limit | High | Reduce column count, compress strings, or split into multiple models |
| Too many columns in a table | Table has > 300 columns | High | Vertical partitioning: split into related tables |
| Unneeded columns inflating model size | Wide tables with columns never used in reports | Medium | Remove unused columns from lakehouse tables or create views |

#### Data Preparation for Direct Lake

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| String columns with high cardinality | String column with > 1M distinct values | High | Consider hashing, bucketing, or moving to a detail table not in the model |
| Columns with mixed types | Column storing numbers as strings intermittently | High | Enforce strict typing in the lakehouse; Direct Lake cannot handle type mismatches gracefully |
| Decimal columns with excessive precision | `DECIMAL(38,18)` when `DECIMAL(18,2)` suffices | Medium | Reduce precision — smaller Parquet footprint = faster Direct Lake |
| Large text columns (> 1KB avg) | Description/notes columns with long text in Direct Lake model | Medium | Exclude from model or move to a detail table only accessed via drill-through |
| Files not V-Ordered | V-Order disabled on Direct Lake source tables | High | Enable V-Order — Direct Lake reads V-Ordered Parquet significantly faster |
| Too many small files | Avg file < 32 MB in Direct Lake source table | High | Run `OPTIMIZE` — Direct Lake opens each file individually; many small files = slow |
| Data not compacted after incremental load | New data appended as tiny files after each pipeline run | High | Add `OPTIMIZE` step at end of each pipeline/notebook that modifies the table |

#### Direct Lake Semantic Model Configuration

| Issue | Detection | Severity | Recommendation |
|-------|-----------|----------|----------------|
| Fallback to DirectQuery not monitored | No alert on fallback events | Medium | Monitor via Fabric capacity metrics; set alerts for DirectQuery fallback |
| Auto-refresh not configured | Direct Lake model not set to detect Delta changes | Medium | Enable `autoSync` so model picks up new data without manual refresh |
| Framing not triggered after data load | Pipeline loads data but doesn't frame the model | High | Add model framing call (`POST /refresh`) at end of pipeline to update Direct Lake metadata |
| Calculated columns in Direct Lake | Model uses calculated columns (DAX-computed at refresh) | Medium | Move calculation logic to the lakehouse (PySpark/SQL) — calculated columns force import-mode fallback for those columns |
| Calculated tables in model | `CALENDAR()`, `GENERATESERIES()`, or other calculated tables | Medium | Materialize as lakehouse tables; calculated tables aren't Direct Lake compatible |
| RLS with complex DAX filters | Row-Level Security using `LOOKUPVALUE` or other complex patterns | Medium | Simplify RLS to direct column comparisons; complex RLS can trigger fallback |

#### Direct Lake Migration Checklist

When recommending migration from Import/DirectQuery to Direct Lake, provide this ordered checklist:

1. **Verify capacity SKU** — Direct Lake requires F64+ for production workloads
2. **Audit table sizes** — ensure all tables fit within guardrails for the capacity tier
3. **Move transformations upstream** — all data prep must happen in the lakehouse, not in Power Query
4. **Optimize Delta tables** — run OPTIMIZE + VACUUM on all source tables; enable V-Order
5. **Remove calculated tables** — materialize as lakehouse tables
6. **Remove calculated columns** — push logic to lakehouse or convert to measures
7. **Simplify RLS** — ensure filters are simple column comparisons
8. **Create the Direct Lake model** — use TMDL with `mode: directLake` partitions pointing to lakehouse tables
9. **Configure auto-sync** — enable automatic metadata sync with Delta log
10. **Add framing to pipelines** — trigger model refresh after each data load
11. **Monitor fallback** — set up capacity metric alerts for DirectQuery fallback events
12. **Validate performance** — compare query times vs previous mode; verify no fallback

### Workspace Audit Scoring

After evaluating all workspace audit rules, compute a **Workspace Health Score** (0-100%):

| Component | Weight | Criteria |
|-----------|--------|----------|
| Workspace organization | 10% | Consistent naming, no dev artifacts in prod, description set |
| Capacity & performance | 15% | Dedicated capacity, refresh schedules, maintenance automation |
| Security & governance | 15% | Roles defined, RLS where needed, sensitivity labels |
| Star schema compliance | 20% | Clear fact/dim separation, conformed dimensions, correct grain |
| Dimensional modeling quality | 15% | Surrogate keys, SCD handling, hierarchies, no mixed grain |
| Direct Lake readiness | 15% | Tables in Delta, V-Ordered, within guardrails, no transformations in model |
| Direct Lake configuration | 10% | Auto-sync, framing, no calculated tables/columns, monitored fallback |

Score interpretation:
- **90-100%**: Exemplary workspace — production-ready, well-governed, Direct Lake optimized
- **70-89%**: Good foundation — minor improvements needed for full optimization
- **50-69%**: Significant issues — performance and governance risks present
- **< 50%**: Major redesign needed — critical anti-patterns detected

## Recommendation Report Format

Each recommendation must include:

```
┌─────────────────────────────────────────────────────┐
│ [SEVERITY] Category — Short title                   │
├─────────────────────────────────────────────────────┤
│ Target:    {table/model/column}                     │
│ Finding:   What was detected                        │
│ Impact:    Why it matters (performance, correctness) │
│ Action:    Specific steps to fix                    │
│ Effort:    Low / Medium / High                      │
│ Priority:  1-5 (1 = fix immediately)                │
│ Code:      (if applicable) Script/command to run    │
└─────────────────────────────────────────────────────┘
```

Severity levels:
- **Critical**: Data correctness at risk or severe performance degradation
- **High**: Significant performance impact or anti-pattern
- **Medium**: Moderate improvement opportunity
- **Low**: Best-practice suggestion, cosmetic or minor

## Action Plan Generation

When generating an action plan, group recommendations by:

1. **Quick Wins** (Low effort, High/Critical severity) — do these first
2. **Important Fixes** (Medium effort, High/Critical severity) — schedule soon
3. **Improvements** (Any effort, Medium severity) — plan for next sprint
4. **Nice-to-Haves** (Low severity) — backlog

For each group, provide:
- Ordered list of actions with dependencies (e.g., "Run OPTIMIZE before VACUUM")
- Estimated impact summary
- PySpark/SQL/DAX code snippets ready to execute
- Rollback steps where applicable

## Deployment of Recommendations

When the user chooses to **deploy** (apply) recommendations:

### Data Storage optimizations
Generate a PySpark notebook with cells for each optimization:
- OPTIMIZE commands with ZORDER
- VACUUM commands
- ALTER TABLE for property changes
- ANALYZE TABLE for statistics
- Data type casts via Delta table rewrites

### Data Model changes
Generate a PySpark notebook with:
- Table creation DDL for new dimension/fact tables
- INSERT INTO SELECT for data migration
- ALTER TABLE for column renames
- DROP TABLE for consolidated tables (after user confirmation)

### Semantic Model fixes
Generate updated TMDL files with fixes applied:
- Updated measures with correct DAX
- Fixed relationship definitions
- Corrected column configurations
- Deploy using `fabric_semantic_model.py deploy`

## Script Reference

Use [./scripts/fabric_optimization_review.py](./scripts/fabric_optimization_review.py) for Fabric REST API operations during the review.

**Install dependencies** (one-time):
```bash
pip install azure-identity requests
```

### Get table properties and Delta log metadata

```bash
python scripts/fabric_optimization_review.py table-info <workspace_id> <lakehouse_id> <table_name>
```

### Get semantic model definition (TMDL)

```bash
python scripts/fabric_optimization_review.py get-model <workspace_id> <model_id>
```

### List all items in a workspace

```bash
python scripts/fabric_optimization_review.py list-items <workspace_id> [--type lakehouse|semanticmodel]
```

## Gotchas

- **V-Order is enabled by default in Fabric** but can be disabled at the table level. Always check `delta.parquet.vorder.enabled` in table properties rather than assuming.
- **OPTIMIZE is safe but resource-intensive.** Running on very large tables during business hours can impact concurrent queries. Recommend off-peak scheduling.
- **VACUUM is destructive.** Once files are vacuumed, time travel to earlier versions is lost. Always warn the user and confirm retention period.
- **Z-Order is not partitioning.** Z-Order co-locates related data within files but does not create folder structure. Both can be used together.
- **Direct Lake models cannot be deployed via the standard REST API `POST semanticModels` with TMDL.** Use the Fabric Items API with `definition` format or create via the Power BI Desktop / Fabric portal. For the workspace audit, recommend Direct Lake readiness but clarify the deployment path.
- **Direct Lake fallback is silent.** When a model exceeds guardrails, it silently falls back to DirectQuery mode. The only way to detect fallback is via capacity metrics or DAX `INFO.STORAGEMODEUSED()`. Always recommend monitoring.
- **Column-level statistics** are not computed automatically in Fabric Delta tables. Stale or missing statistics cause the optimizer to make bad decisions (full scans instead of file skipping).
- **Bidirectional cross-filtering** is the most common semantic model performance killer. Always flag it unless there's a documented bridge-table pattern.
- **Format strings are locale-dependent.** `#,##0.00` is US format. For `es-ES`, use `#.##0,00` (dot for thousands, comma for decimals).
