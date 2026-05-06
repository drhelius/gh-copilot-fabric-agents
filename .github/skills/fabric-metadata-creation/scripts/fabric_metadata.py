#!/usr/bin/env python3
"""Fabric Metadata Proposal Helper.

Discovers Fabric assets, exports semantic model definitions, renders local
metadata proposal PDFs, and validates generated proposal folders.

Authentication: Uses Azure CLI credentials through DefaultAzureCredential.

Usage:
    python fabric_metadata.py list-workspaces
    python fabric_metadata.py list-items <workspace_id> [<item_type>]
    python fabric_metadata.py list-lakehouse-tables <workspace_id> <lakehouse_id>
    python fabric_metadata.py get-lakehouse-table <workspace_id> <lakehouse_id> <table_name>
    python fabric_metadata.py list-semantic-models <workspace_id> [<model_name>]
    python fabric_metadata.py export-semantic-model <workspace_id> <semantic_model_id> <output_dir>
    python fabric_metadata.py render-pdf <metadata_proposal.json> <metadata_proposal.pdf>
    python fabric_metadata.py render-glossary-md <metadata_proposal.json> <glossary_terms.md>
    python fabric_metadata.py render-glossary-pdf <metadata_proposal.json> <glossary_terms.pdf>
    python fabric_metadata.py render-markdown-pdf <input.md> <output.pdf>
    python fabric_metadata.py validate <output_dir>
"""

from __future__ import annotations

import base64
import html
import json
import sys
import time
from pathlib import Path
from typing import Any


FABRIC_API = "https://api.fabric.microsoft.com/v1"
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
STORAGE_SCOPE = "https://storage.azure.com/.default"
PDF_ACCENT = "#0078d4"
PDF_ACCENT2 = "#106ebe"
FIELD_LABELS = {
    "generated_at": "Fecha de generacion",
    "generated_by": "Generado por",
    "proposal_version": "Version de la propuesta",
    "input_interpreted": "Entrada interpretada",
    "executive_summary": "Resumen ejecutivo",
    "assets": "Activos",
    "columns": "Columnas",
    "glossary_terms": "Terminos de glosario",
    "classifications": "Clasificaciones",
    "sensitivity_labels": "Etiquetas de sensibilidad",
    "critical_data_elements": "Elementos criticos de datos",
    "data_products": "Productos de datos",
    "relationships_lineage": "Relaciones y linaje",
    "data_quality_rules": "Reglas de calidad de datos",
    "governance_notes": "Notas de gobierno",
    "assumptions": "Supuestos",
    "open_questions": "Preguntas abiertas",
    "asset_name": "Nombre del activo",
    "asset_type": "Tipo de activo",
    "fully_qualified_name": "Nombre completamente cualificado",
    "platform": "Plataforma",
    "source_system": "Sistema origen",
    "database_name": "Base de datos",
    "schema_name": "Esquema",
    "object_type": "Tipo de objeto",
    "data_domain": "Dominio de datos",
    "data_product": "Producto de datos",
    "environment": "Entorno",
    "lifecycle_status": "Estado del ciclo de vida",
    "business_description": "Descripcion de negocio",
    "technical_description": "Descripcion tecnica",
    "data_owner": "Propietario de datos",
    "data_steward": "Responsable de gobierno de datos",
    "owner_or_steward": "Propietario o steward",
    "glossary_terms": "Terminos de glosario",
    "upstream_lineage": "Linaje ascendente",
    "downstream_lineage": "Linaje descendente",
    "source_of_truth": "Fuente de referencia",
    "security_notes": "Notas de seguridad",
    "quality_notes": "Notas de calidad",
    "lineage_summary": "Resumen de linaje",
    "quality_summary": "Resumen de calidad",
    "confidence": "Confianza",
    "metadata_source": "Fuente de metadatos",
    "column_name": "Nombre de columna",
    "business_name": "Nombre de negocio",
    "data_type": "Tipo de dato",
    "nullable": "Permite nulos",
    "key_role": "Rol de clave",
    "measure_or_dimension": "Medida o dimension",
    "semantic_type": "Tipo semantico",
    "classification": "Clasificacion",
    "sensitivity_label": "Etiqueta de sensibilidad",
    "pii_indicator": "Indicador de datos personales",
    "critical_data_element_candidate": "Candidato a dato critico",
    "derivation_logic": "Logica de derivacion",
    "allowed_values": "Valores permitidos",
    "example_values": "Valores de ejemplo",
    "quality_rules": "Reglas de calidad",
    "relationship_hints": "Pistas de relacion",
    "lineage_hints": "Pistas de linaje",
    "masking_recommendation": "Recomendacion de enmascaramiento",
    "term_name": "Termino",
    "definition": "Definicion",
    "synonyms": "Sinonimos",
    "related_terms": "Terminos relacionados",
    "domain": "Dominio",
    "status": "Estado",
    "associated_assets": "Activos asociados",
    "associated_columns": "Columnas asociadas",
    "business_rules": "Reglas de negocio",
    "classification_name": "Nombre de clasificacion",
    "classification_reason": "Motivo de clasificacion",
    "detection_basis": "Base de deteccion",
    "suggested_label": "Etiqueta sugerida",
    "label_reason": "Motivo de la etiqueta",
    "protection_recommendation": "Recomendacion de proteccion",
    "quality_dimension": "Dimension de calidad",
    "quality_rule": "Regla de calidad",
    "severity": "Severidad",
    "upstream_source": "Origen ascendente",
    "downstream_consumer": "Consumidor descendente",
    "relationship_or_join_hint": "Pista de relacion o union",
    "cde_name": "Nombre del dato critico",
    "business_reason": "Motivo de negocio",
    "data_product_name": "Nombre del producto de datos",
    "purpose": "Proposito",
    "included_assets": "Activos incluidos",
    "target_consumers": "Consumidores objetivo",
    "review_required": "Requiere revision",
}
VALUE_LABELS = {
    "metadata_source": {
        "explicit": "explicita",
        "inferred": "inferida",
        "mixed": "mixta",
    },
    "confidence": {
        "high": "alta",
        "medium": "media",
        "low": "baja",
    },
    "status": {
        "Proposed": "Propuesto",
        "proposed": "propuesto",
        "TBD": "Por determinar",
        "Unknown": "Desconocido",
    },
}


def get_headers(scope: str = FABRIC_SCOPE, content_type: str | None = "application/json") -> dict[str, str]:
    """Get auth headers using the logged-in user's Azure CLI credentials."""
    try:
        from azure.identity import DefaultAzureCredential
    except ImportError as error:
        raise RuntimeError("azure-identity is required for Fabric calls. Run: pip install azure-identity") from error

    credential = DefaultAzureCredential()
    token = credential.get_token(scope)
    headers = {"Authorization": f"Bearer {token.token}"}
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def request_json(method: str, url: str, *, expected: tuple[int, ...] = (200,), **kwargs: Any) -> Any:
    """Run an HTTP request and return parsed JSON or exit with a helpful error."""
    try:
        import requests
    except ImportError as error:
        raise RuntimeError("requests is required for Fabric calls. Run: pip install requests") from error

    response = requests.request(method, url, headers=get_headers(), timeout=60, **kwargs)
    if response.status_code not in expected:
        print(f"Error {response.status_code}: {response.text}", file=sys.stderr)
        sys.exit(1)
    if not response.text.strip():
        return {}
    return response.json()


def print_json(data: Any) -> None:
    """Print stable JSON for downstream parsing."""
    print(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))


def list_workspaces() -> list[dict[str, Any]]:
    """List Fabric workspaces visible to the current account."""
    data = request_json("GET", f"{FABRIC_API}/workspaces")
    workspaces = []
    for workspace in data.get("value", []):
        workspaces.append({
            "id": workspace.get("id"),
            "displayName": workspace.get("displayName"),
            "type": workspace.get("type"),
            "capacityId": workspace.get("capacityId"),
        })
    print_json(workspaces)
    return workspaces


def list_items(workspace_id: str, item_type: str | None = None) -> list[dict[str, Any]]:
    """List Fabric items in a workspace, optionally filtered by type."""
    data = request_json("GET", f"{FABRIC_API}/workspaces/{workspace_id}/items")
    items = []
    requested_type = item_type.lower() if item_type else None

    for item in data.get("value", []):
        actual_type = item.get("type") or item.get("itemType")
        if requested_type and str(actual_type).lower() != requested_type:
            continue
        items.append({
            "id": item.get("id"),
            "displayName": item.get("displayName"),
            "type": actual_type,
            "description": item.get("description"),
        })

    print_json(items)
    return items


def normalise_delta_type(delta_type: Any) -> str:
    """Convert a Delta schema type value to a readable string."""
    if isinstance(delta_type, str):
        return delta_type
    if isinstance(delta_type, dict):
        type_name = delta_type.get("type", "unknown")
        if type_name == "decimal":
            return f"decimal({delta_type.get('precision')},{delta_type.get('scale')})"
        if type_name in {"array", "map", "struct"}:
            return json.dumps(delta_type, sort_keys=True)
        return str(type_name)
    return str(delta_type)


def extract_delta_schema(delta_log_url: str) -> list[dict[str, Any]]:
    """Read the first Delta log metadata entry and extract columns."""
    try:
        import requests
    except ImportError as error:
        raise RuntimeError("requests is required for Fabric calls. Run: pip install requests") from error

    response = requests.get(delta_log_url, headers=get_headers(STORAGE_SCOPE, None), timeout=30)
    if response.status_code != 200:
        return []

    for line in response.text.strip().splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if "metaData" not in entry:
            continue
        schema_text = entry["metaData"].get("schemaString", "{}")
        schema = json.loads(schema_text)
        columns = []
        for field in schema.get("fields", []):
            columns.append({
                "name": field.get("name"),
                "type": normalise_delta_type(field.get("type")),
                "nullable": field.get("nullable", True),
                "metadata": field.get("metadata", {}),
            })
        return columns
    return []


def list_lakehouse_tables(workspace_id: str, lakehouse_id: str, *, emit: bool = True) -> list[dict[str, Any]]:
    """List lakehouse tables and attempt to include Delta schemas."""
    tables_response = request_json(
        "GET",
        f"{FABRIC_API}/workspaces/{workspace_id}/lakehouses/{lakehouse_id}/tables",
    )
    tables_data = tables_response.get("data") or tables_response.get("value") or []

    lakehouse_response = request_json(
        "GET",
        f"{FABRIC_API}/workspaces/{workspace_id}/lakehouses/{lakehouse_id}",
    )
    onelake_tables_path = lakehouse_response.get("properties", {}).get("oneLakeTablesPath", "")

    results = []
    for table_info in tables_data:
        table_name = table_info.get("name") or table_info.get("displayName") or "unknown"
        table_format = table_info.get("format", "unknown")
        table = {
            "name": table_name,
            "format": table_format,
            "type": table_info.get("type", "Table"),
            "location": table_info.get("location"),
            "columns": [],
            "metadata_source": "explicit",
        }

        if str(table_format).lower() == "delta" and onelake_tables_path:
            delta_log_url = f"{onelake_tables_path}/{table_name}/_delta_log/00000000000000000000.json"
            try:
                table["columns"] = extract_delta_schema(delta_log_url)
            except Exception as error:  # noqa: BLE001 - keep CLI discovery resilient
                print(f"Warning: could not read Delta schema for {table_name}: {error}", file=sys.stderr)

        results.append(table)

    if emit:
        print_json(results)
    return results


def get_lakehouse_table(workspace_id: str, lakehouse_id: str, table_name: str) -> dict[str, Any]:
    """Get one lakehouse table entry from the table list."""
    tables = list_lakehouse_tables(workspace_id, lakehouse_id, emit=False)
    for table in tables:
        if table.get("name") == table_name:
            print_json(table)
            return table
    print(f"Table not found: {table_name}", file=sys.stderr)
    sys.exit(1)


def list_semantic_models(workspace_id: str, model_name: str | None = None) -> list[dict[str, Any]]:
    """List semantic models in a Fabric workspace."""
    data = request_json("GET", f"{FABRIC_API}/workspaces/{workspace_id}/semanticModels")
    models = []
    for model in data.get("value", []):
        if model_name and model.get("displayName") != model_name:
            continue
        models.append({
            "id": model.get("id"),
            "displayName": model.get("displayName"),
            "description": model.get("description"),
            "type": "SemanticModel",
        })
    print_json(models)
    return models


def poll_long_running_operation(operation_url: str, max_wait: int = 300) -> Any:
    """Poll a Fabric long-running operation until it completes."""
    try:
        import requests
    except ImportError as error:
        raise RuntimeError("requests is required for Fabric calls. Run: pip install requests") from error

    elapsed_seconds = 0
    while elapsed_seconds < max_wait:
        response = requests.get(operation_url, headers=get_headers(), timeout=30)
        if response.status_code != 200:
            print(f"Poll error {response.status_code}: {response.text}", file=sys.stderr)
            sys.exit(1)

        data = response.json()
        status = data.get("status", "Unknown")
        print(f"Status: {status} ({elapsed_seconds}s elapsed)", file=sys.stderr)

        if status in {"Succeeded", "Completed"}:
            return data
        if status in {"Failed", "Cancelled"}:
            print(json.dumps(data.get("error", data), indent=2), file=sys.stderr)
            sys.exit(1)

        retry_after = int(response.headers.get("Retry-After", 10))
        time.sleep(retry_after)
        elapsed_seconds += retry_after

    print(f"Timed out after {max_wait}s", file=sys.stderr)
    sys.exit(1)


def get_operation_result(operation_url: str, operation_data: dict[str, Any] | None = None) -> Any:
    """Fetch the result payload for a completed Fabric long-running operation."""
    try:
        import requests
    except ImportError as error:
        raise RuntimeError("requests is required for Fabric calls. Run: pip install requests") from error

    operation_data = operation_data or {}
    embedded_result = operation_data.get("result") or operation_data.get("response")
    if embedded_result:
        return embedded_result

    result_url = operation_data.get("resultUrl") or operation_data.get("resourceLocation")
    if not result_url:
        result_url = operation_url.split("?", 1)[0].rstrip("/") + "/result"

    response = requests.get(result_url, headers=get_headers(), timeout=60)
    if response.status_code != 200:
        print(f"Operation result error {response.status_code}: {response.text}", file=sys.stderr)
        sys.exit(1)
    if not response.text.strip():
        return {}
    return response.json()


def get_definition_parts(definition_response: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract definition parts from the known Fabric getDefinition response shapes."""
    definition = definition_response.get("definition", definition_response)
    if isinstance(definition, dict):
        parts = definition.get("parts")
        if isinstance(parts, list):
            return parts

    parts = definition_response.get("parts")
    if isinstance(parts, list):
        return parts

    return []


def post_definition_request(requests_module: Any, url: str) -> Any:
    """Post a getDefinition request and return the decoded definition payload."""
    response = requests_module.post(url, headers=get_headers(), timeout=60)

    if response.status_code == 200:
        return response.json()
    if response.status_code == 202:
        operation_url = response.headers.get("Location") or response.headers.get("Operation-Location")
        if not operation_url:
            print("Fabric returned 202 without an operation URL.", file=sys.stderr)
            sys.exit(1)
        operation_data = poll_long_running_operation(operation_url)
        return get_operation_result(operation_url, operation_data)

    return response


def export_semantic_model(workspace_id: str, semantic_model_id: str, output_dir: str) -> dict[str, Any]:
    """Export a semantic model definition to a local folder."""
    try:
        import requests
    except ImportError as error:
        raise RuntimeError("requests is required for Fabric calls. Run: pip install requests") from error

    request_urls = [
        f"{FABRIC_API}/workspaces/{workspace_id}/semanticModels/{semantic_model_id}/getDefinition?format=TMDL",
        f"{FABRIC_API}/workspaces/{workspace_id}/semanticModels/{semantic_model_id}/getDefinition",
        f"{FABRIC_API}/workspaces/{workspace_id}/items/{semantic_model_id}/getDefinition?format=TMDL",
        f"{FABRIC_API}/workspaces/{workspace_id}/items/{semantic_model_id}/getDefinition",
    ]

    definition_response = None
    last_error = None
    for url in request_urls:
        candidate_response = post_definition_request(requests, url)
        if hasattr(candidate_response, "status_code"):
            last_error = candidate_response
            if candidate_response.status_code in {400, 404, 405}:
                continue
            print(f"Error {candidate_response.status_code}: {candidate_response.text}", file=sys.stderr)
            sys.exit(1)

        candidate_parts = get_definition_parts(candidate_response)
        if candidate_parts:
            definition_response = candidate_response
            parts = candidate_parts
            break

        definition_response = candidate_response
        parts = []

    if definition_response is None:
        if last_error is not None:
            print(f"Error {last_error.status_code}: {last_error.text}", file=sys.stderr)
        else:
            print("No semantic model definition response received.", file=sys.stderr)
        sys.exit(1)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    raw_response_path = output_path / "definition_response.json"
    raw_response_path.write_text(json.dumps(definition_response, indent=2, ensure_ascii=False), encoding="utf-8")

    manifest = []
    for part in parts:
        relative_path = part.get("path")
        payload = part.get("payload")
        if not relative_path or payload is None:
            continue
        decoded = base64.b64decode(payload).decode("utf-8")
        destination = output_path / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(decoded, encoding="utf-8")
        manifest.append({"path": relative_path, "bytes": len(decoded.encode("utf-8"))})

    manifest_path = output_path / "export_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    result = {"output_dir": str(output_path), "parts": manifest, "raw_response": str(raw_response_path)}
    print_json(result)
    return result


def load_structured_file(path: Path) -> Any:
    """Load JSON from a proposal file."""
    suffix = path.suffix.lower()
    if suffix == ".json":
        with path.open(encoding="utf-8") as file_handle:
            return json.load(file_handle)
    raise ValueError(f"Unsupported structured file type: {path.suffix}")


def titleize(value: str) -> str:
    """Convert snake_case identifiers to readable title text."""
    return str(value).replace("_", " ").replace("-", " ").title()


def field_label(field_name: str) -> str:
    """Return the Spanish display label for a metadata field."""
    return FIELD_LABELS.get(field_name, f"Campo original: {field_name}")


def display_value(field_name: str | None, value: Any) -> Any:
    """Translate schema values that are not source identifiers for Spanish review output."""
    if isinstance(value, bool):
        return "Si" if value else "No"
    if field_name and isinstance(value, str):
        return VALUE_LABELS.get(field_name, {}).get(value, value)
    return value


def markdown_cell(value: Any, field_name: str | None = None) -> str:
    """Format a nested source value as literal text inside a Markdown table cell."""
    value = display_value(field_name, value)
    if value is None:
        text = ""
    elif isinstance(value, dict):
        parts = [f"{field_label(str(key))}: {markdown_cell(nested_value, str(key))}" for key, nested_value in value.items()]
        text = "; ".join(parts)
    elif isinstance(value, list):
        if not value:
            text = "Ninguno"
        else:
            text = "; ".join(markdown_cell(item, field_name) for item in value)
    else:
        text = str(value)

    return html.escape(text, quote=False).replace("\n", "<br>").replace("|", "&#124;")


def literal_heading(value: Any) -> str:
    """Format a source value as literal inline text inside a heading."""
    return html.escape(str(value), quote=False).replace("\n", " ").strip()


def item_heading(item: dict[str, Any], index: int) -> str:
    """Pick a stable heading for a proposal object."""
    asset_name = item.get("asset_name")
    column_name = item.get("column_name")
    if column_name:
        column_ref = f"{asset_name}.{column_name}" if asset_name else str(column_name)
        if item.get("classification_name"):
            return literal_heading(f"{column_ref}: {item['classification_name']}")
        if item.get("suggested_label"):
            return literal_heading(f"{column_ref}: {item['suggested_label']}")
        if item.get("quality_dimension"):
            return literal_heading(f"{column_ref}: {item['quality_dimension']}")
        return literal_heading(column_ref)

    if asset_name and item.get("suggested_label"):
        return literal_heading(f"{asset_name}: {item['suggested_label']}")

    heading_fields = [
        "term_name",
        "classification_name",
        "suggested_label",
        "cde_name",
        "data_product_name",
        "quality_rule",
        "relationship_or_join_hint",
        "upstream_source",
        "asset_name",
    ]
    for field_name in heading_fields:
        value = item.get(field_name)
        if value:
            return literal_heading(value)
    return f"Elemento {index}"


def asset_display_name(asset: dict[str, Any], index: int) -> str:
    """Pick a literal display name for an asset."""
    return item_heading(asset, index)


def item_asset_references(item: dict[str, Any]) -> set[str]:
    """Collect likely asset references from a proposal object."""
    reference_fields = [
        "asset_name",
        "table_name",
        "parent_asset",
        "source_asset",
        "fully_qualified_name",
        "associated_assets",
    ]
    references: set[str] = set()
    for field_name in reference_fields:
        value = item.get(field_name)
        if isinstance(value, str) and value:
            references.add(value)
        elif isinstance(value, list):
            references.update(str(entry) for entry in value if entry)
    return references


def item_matches_asset(item: dict[str, Any], asset: dict[str, Any]) -> bool:
    """Return whether a proposal item appears to belong to an asset."""
    asset_names = {
        str(asset.get(field_name))
        for field_name in ("asset_name", "fully_qualified_name", "table_name")
        if asset.get(field_name)
    }
    references = item_asset_references(item)
    if asset_names & references:
        return True
    item_fqn = str(item.get("fully_qualified_name", ""))
    return any(item_fqn.startswith(f"{asset_name}.") for asset_name in asset_names)


def table_for_item(item: dict[str, Any], first_header: str = "Campo") -> list[str]:
    """Render one proposal object as a compact two-column Markdown table."""
    lines = [f"| {first_header} | Valor |", "|---|---|"]
    for key, value in item.items():
        lines.append(f"| {field_label(str(key))} | {markdown_cell(value, str(key))} |")
    return lines


def markdown_for_value(value: Any, item_prefix: str = "Elemento", first_header: str = "Campo") -> list[str]:
    """Render a nested value as Markdown suitable for report sections."""
    if isinstance(value, list):
        if not value:
            return ["No hay contenido propuesto disponible."]
        if all(isinstance(item, dict) for item in value):
            lines: list[str] = []
            for index, item in enumerate(value, start=1):
                lines.append(f"#### {item_prefix} {index}: {item_heading(item, index)}")
                lines.extend(table_for_item(item, first_header))
                lines.append("")
            return lines
        return [f"- {markdown_cell(item)}" for item in value]

    if isinstance(value, dict):
        if not value:
            return ["No hay contenido propuesto disponible."]
        return table_for_item(value, first_header)

    if value in {None, ""}:
        return ["No hay contenido propuesto disponible."]
    return [markdown_cell(value)]


def page_break() -> str:
    """Return a page-break marker understood by the PDF stylesheet."""
    return '<div class="page-break"></div>'


def proposal_to_markdown(data: Any) -> str:
    """Create a Spanish styled-PDF-friendly Markdown proposal from JSON data."""
    proposal = data.get("metadata_proposal", data) if isinstance(data, dict) else data
    lines = [
        "# Propuesta de Metadatos de Fabric",
        "",
        "## Indice",
        "",
        "[TOC]",
        "",
        page_break(),
        "",
    ]
    if isinstance(proposal, dict):
        assets = proposal.get("assets", []) if isinstance(proposal.get("assets", []), list) else []
        columns = proposal.get("columns", []) if isinstance(proposal.get("columns", []), list) else []
        included_keys = {
            "generated_at",
            "generated_by",
            "proposal_version",
            "executive_summary",
            "input_interpreted",
            "assets",
            "columns",
            "glossary_terms",
            "classifications",
            "sensitivity_labels",
            "critical_data_elements",
            "data_products",
            "governance_notes",
            "relationships_lineage",
            "data_quality_rules",
            "assumptions",
            "open_questions",
        }

        lines.extend(["## 1. Resumen ejecutivo", ""])
        summary_fields = {
            "generated_at": proposal.get("generated_at"),
            "generated_by": proposal.get("generated_by"),
            "proposal_version": proposal.get("proposal_version"),
            "executive_summary": proposal.get("executive_summary"),
        }
        lines.extend(table_for_item(summary_fields, "Campo del resumen"))
        lines.append("")

        lines.extend(["## 2. Entrada interpretada", ""])
        lines.extend(markdown_for_value(proposal.get("input_interpreted", {}), first_header="Campo de entrada"))
        lines.append("")

        lines.extend(["## 3. Activos y columnas", ""])
        if assets:
            assigned_column_indexes: set[int] = set()
            for asset_index, asset in enumerate(assets, start=1):
                if not isinstance(asset, dict):
                    continue
                if asset_index > 1:
                    lines.extend([page_break(), ""])
                asset_name = asset_display_name(asset, asset_index)
                asset_header = f"Campo del activo: {markdown_cell(asset_name)}"
                lines.extend([f"### 3.{asset_index}. Activo: {asset_name}", ""])
                lines.extend(table_for_item(asset, asset_header))
                lines.append("")
                related_columns = []
                for column_index, column in enumerate(columns):
                    if isinstance(column, dict) and item_matches_asset(column, asset):
                        related_columns.append(column)
                        assigned_column_indexes.add(column_index)
                if related_columns:
                    lines.extend([f"#### 3.{asset_index}.1. Columnas del activo", ""])
                    for related_index, column in enumerate(related_columns, start=1):
                        column_name = item_heading(column, related_index)
                        lines.extend([
                            f"##### 3.{asset_index}.1.{related_index}. Columna: {column_name}",
                            "",
                        ])
                        lines.extend(table_for_item(column, f"Campo de columna (activo: {markdown_cell(asset_name)})"))
                        lines.append("")
                else:
                    lines.extend([f"#### 3.{asset_index}.1. Columnas del activo", "", "No hay columnas asociadas explicitamente a este activo.", ""])

            unassigned_columns = [
                column
                for column_index, column in enumerate(columns)
                if column_index not in assigned_column_indexes and isinstance(column, dict)
            ]
            if unassigned_columns:
                unassigned_section = len(assets) + 1
                lines.extend([page_break(), "", f"### 3.{unassigned_section}. Columnas sin activo asociado", ""])
                for column_index, column in enumerate(unassigned_columns, start=1):
                    lines.extend([f"#### 3.{unassigned_section}.{column_index}. Columna: {item_heading(column, column_index)}", ""])
                    lines.extend(table_for_item(column, "Campo de columna"))
                    lines.append("")
        else:
            lines.extend(["No hay activos propuestos disponibles.", ""])
            if columns:
                lines.extend(["### 3.1. Columnas", ""])
                lines.extend(markdown_for_value(columns, "Columna", "Campo de columna"))
                lines.append("")

        lines.extend([page_break(), "", "## 4. Glosario", ""])
        lines.extend(markdown_for_value(proposal.get("glossary_terms", []), "Termino", "Campo del termino"))
        lines.append("")

        governance_groups = [
            ("1", "Clasificaciones", proposal.get("classifications", []), "Clasificacion", "Campo de clasificacion"),
            ("2", "Etiquetas de sensibilidad", proposal.get("sensitivity_labels", []), "Etiqueta", "Campo de etiqueta"),
            ("3", "Elementos criticos de datos", proposal.get("critical_data_elements", []), "Dato critico", "Campo del dato critico"),
            ("4", "Productos de datos", proposal.get("data_products", []), "Producto", "Campo del producto"),
        ]
        lines.extend(["## 5. Sugerencias de gobierno", ""])
        for subsection, title, value, item_prefix, first_header in governance_groups:
            lines.extend([f"### 5.{subsection}. {title}", ""])
            lines.extend(markdown_for_value(value, item_prefix, first_header))
            lines.append("")

        lines.extend(["## 6. Relaciones, linaje y calidad de datos", ""])
        lines.extend(["### 6.1. Relaciones y linaje", ""])
        lines.extend(markdown_for_value(proposal.get("relationships_lineage", []), "Relacion", "Campo de relacion"))
        lines.append("")
        lines.extend(["### 6.2. Reglas de calidad", ""])
        lines.extend(markdown_for_value(proposal.get("data_quality_rules", []), "Regla", "Campo de calidad"))
        lines.append("")

        lines.extend(["## 7. Supuestos y preguntas abiertas", ""])
        lines.extend(["### 7.1. Supuestos", ""])
        lines.extend(markdown_for_value(proposal.get("assumptions", [])))
        lines.append("")
        lines.extend(["### 7.2. Preguntas abiertas", ""])
        lines.extend(markdown_for_value(proposal.get("open_questions", [])))
        lines.append("")

        for key, value in proposal.items():
            if key in included_keys:
                continue
            lines.extend([f"## Anexo: {field_label(str(key))}", ""])
            lines.extend(markdown_for_value(value))
            lines.append("")
    else:
        lines.extend(markdown_for_value(proposal))

    return "\n".join(lines).rstrip() + "\n"


def markdown_pdf_html(markdown_text: str) -> str:
    """Convert Markdown to full HTML with the report PDF stylesheet."""
    try:
        import markdown
    except ImportError as error:
        raise RuntimeError("markdown is required for styled PDF output. Run: pip install markdown weasyprint") from error

    html_body = markdown.markdown(markdown_text, extensions=["tables", "fenced_code", "toc"])
    return f"""<!DOCTYPE html>
<html><head><meta charset=\"utf-8\">
<style>
  @page {{ size: A4; margin: 1.5cm; }}
  body {{ font-family: Segoe UI, Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.5; color: #1a1a1a; }}
  h1 {{ color: {PDF_ACCENT}; font-size: 20pt; border-bottom: 2px solid {PDF_ACCENT}; padding-bottom: 6px; page-break-after: avoid; }}
  h2 {{ color: {PDF_ACCENT2}; font-size: 14pt; margin-top: 20px; border-bottom: 1px solid #ddd; padding-bottom: 4px; page-break-after: avoid; }}
    h3 {{ color: #333; font-size: 12pt; margin-top: 16px; page-break-after: avoid; }}
    h4 {{ color: #333; font-size: 10.5pt; margin-top: 12px; page-break-after: avoid; }}
    h5 {{ color: #333; font-size: 10pt; margin-top: 10px; page-break-after: avoid; }}
    table {{ border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 9pt; }}
  th {{ background-color: {PDF_ACCENT}; color: white; padding: 6px 8px; text-align: left; }}
  td {{ padding: 5px 8px; border: 1px solid #ddd; vertical-align: top; word-break: break-word; }}
  tr:nth-child(even) {{ background-color: #f5f5f5; }}
    .toc {{ border: 1px solid #ddd; padding: 10px 14px; margin: 12px 0; background: #fafafa; }}
    .toc ul {{ margin: 4px 0 4px 18px; padding: 0; }}
    .toc a {{ color: {PDF_ACCENT2}; text-decoration: none; }}
    .page-break {{ break-before: page; page-break-before: always; height: 0; }}
  code {{ background: #f0f0f0; padding: 1px 4px; border-radius: 3px; font-size: 9pt; font-family: Consolas, monospace; }}
  pre {{ background: #1e1e1e; color: #d4d4d4; padding: 12px; border-radius: 4px; font-size: 8.5pt; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; }}
  pre code {{ background: none; color: inherit; padding: 0; }}
  strong {{ color: {PDF_ACCENT}; }}
  hr {{ border: none; border-top: 1px solid #ccc; margin: 16px 0; }}
  p {{ margin: 6px 0; }}
</style>
</head><body>{html_body}</body></html>"""


def render_markdown_pdf(markdown_text: str, output_path: Path) -> None:
    """Render Markdown to a styled A4 PDF with WeasyPrint."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from weasyprint import HTML
    except ImportError as error:
        raise RuntimeError("weasyprint is required for styled PDF output. Run: pip install markdown weasyprint") from error

    html = markdown_pdf_html(markdown_text)
    HTML(string=html, base_url=str(output_path.parent)).write_pdf(str(output_path))


def render_markdown_pdf_file(input_file: str, output_file: str) -> Path:
    """Render a Markdown file to a styled PDF."""
    input_path = Path(input_file)
    output_path = Path(output_file)
    markdown_text = input_path.read_text(encoding="utf-8")
    render_markdown_pdf(markdown_text, output_path)
    print(f"Rendered Markdown PDF: {output_path}")
    return output_path


def render_pdf(input_file: str, output_file: str) -> Path:
    """Render a proposal JSON file to PDF."""
    input_path = Path(input_file)
    output_path = Path(output_file)
    data = load_structured_file(input_path)
    markdown_text = proposal_to_markdown(data)
    render_markdown_pdf(markdown_text, output_path)

    print(f"Rendered PDF: {output_path}")
    return output_path


def glossary_to_markdown(data: Any) -> str:
    """Create a Spanish steward-friendly Markdown glossary report from a proposal."""
    proposal = data.get("metadata_proposal", data) if isinstance(data, dict) else {}
    terms = proposal.get("glossary_terms", []) if isinstance(proposal, dict) else []
    input_interpreted = proposal.get("input_interpreted", {}) if isinstance(proposal, dict) else {}
    generated_at = proposal.get("generated_at", "Desconocido") if isinstance(proposal, dict) else "Desconocido"

    lines = [
        "# Propuesta de Glosario de Negocio",
        "",
        "## Indice",
        "",
        "[TOC]",
        "",
        page_break(),
        "",
        "## 1. Contexto",
        "",
        f"**Fecha de generacion:** {markdown_cell(generated_at)}",
        "",
        "**Proposito:** Glosario independiente para revision por stewards generado a partir de evidencia de metadatos de Fabric.",
        "",
        "**Estado:** Los terminos son propuestas y requieren aprobacion antes de cualquier ingestion en catalogo.",
        "",
    ]

    if input_interpreted:
        lines.extend(["### 1.1. Entrada interpretada", ""])
        lines.extend(markdown_for_value(input_interpreted, first_header="Campo de entrada"))
        lines.append("")

    if not terms:
        lines.extend(["## 2. Terminos de glosario", "", "No se propusieron terminos de glosario con la evidencia disponible.", ""])
        return "\n".join(lines).rstrip() + "\n"

    grouped_terms: dict[str, list[dict[str, Any]]] = {}
    for term in terms:
        if not isinstance(term, dict):
            continue
        domain = term.get("domain") or "Dominio desconocido"
        grouped_terms.setdefault(str(domain), []).append(term)

    lines.extend(["## 2. Resumen por dominio", "", "| Dominio | Terminos propuestos |", "|---|---|"])
    for domain in sorted(grouped_terms):
        lines.append(f"| {markdown_cell(domain)} | {len(grouped_terms[domain])} |")
    lines.append("")

    lines.extend([page_break(), "", "## 3. Terminos del glosario", ""])
    field_order = [
        "definition",
        "synonyms",
        "related_terms",
        "business_rules",
        "owner_or_steward",
        "status",
        "associated_assets",
        "associated_columns",
        "confidence",
        "metadata_source",
        "open_questions",
    ]
    for domain_index, domain in enumerate(sorted(grouped_terms), start=1):
        if domain_index > 1:
            lines.extend([page_break(), ""])
        lines.extend([f"### 3.{domain_index}. Dominio: {markdown_cell(domain)}", ""])
        sorted_terms = sorted(grouped_terms[domain], key=lambda item: str(item.get("term_name", "")))
        for index, term in enumerate(sorted_terms, start=1):
            term_name = term.get("term_name") or f"Termino {index}"
            lines.extend([f"#### 3.{domain_index}.{index}. Termino: {literal_heading(term_name)}", "", f"| Campo del termino: {markdown_cell(term_name)} | Valor |", "|---|---|"])
            for field_name in field_order:
                if field_name not in term:
                    continue
                lines.append(f"| {field_label(field_name)} | {markdown_cell(term[field_name], field_name)} |")
            lines.append("")

    lines.extend([
        "## 4. Guia de revision",
        "",
        "- Confirmar si cada termino propuesto coincide con el vocabulario de la organizacion.",
        "- Asignar propietarios y stewards reales solo despues de aprobacion humana.",
        "- Validar sinonimos, terminos relacionados y activos asociados antes de la ingestion en catalogo.",
        "- Tratar la confianza como indicador de evidencia, no como decision de gobierno.",
    ])
    return "\n".join(lines).rstrip() + "\n"


def render_glossary_md(input_file: str, output_file: str) -> Path:
    """Render only the glossary terms from a proposal JSON file to Markdown."""
    input_path = Path(input_file)
    output_path = Path(output_file)
    data = load_structured_file(input_path)
    markdown_text = glossary_to_markdown(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown_text, encoding="utf-8")
    print(f"Rendered glossary Markdown: {output_path}")
    return output_path


def render_glossary_pdf(input_file: str, output_file: str) -> Path:
    """Render only the glossary terms from a proposal JSON file to PDF."""
    input_path = Path(input_file)
    output_path = Path(output_file)
    data = load_structured_file(input_path)
    markdown_text = glossary_to_markdown(data)
    render_markdown_pdf(markdown_text, output_path)

    print(f"Rendered glossary PDF: {output_path}")
    return output_path


def validate_proposal_content(data: Any) -> list[str]:
    """Validate required compact metadata fields in a proposal payload."""
    proposal = data.get("metadata_proposal", data) if isinstance(data, dict) else data
    if not isinstance(proposal, dict):
        return ["metadata_proposal must be a JSON object"]

    errors: list[str] = []
    asset_column_required = {"confidence", "metadata_source", "assumptions", "open_questions"}
    object_required = {"confidence", "metadata_source"}
    collection_requirements = {
        "assets": asset_column_required,
        "columns": asset_column_required,
        "glossary_terms": object_required,
        "classifications": object_required,
        "sensitivity_labels": object_required,
        "critical_data_elements": object_required,
        "data_products": object_required,
        "relationships_lineage": object_required,
        "data_quality_rules": object_required,
    }

    for collection_name, required_fields in collection_requirements.items():
        collection = proposal.get(collection_name, [])
        if not isinstance(collection, list):
            errors.append(f"metadata_proposal.{collection_name} must be a list")
            continue
        for index, item in enumerate(collection, start=1):
            if not isinstance(item, dict):
                errors.append(f"metadata_proposal.{collection_name}[{index}] must be an object")
                continue
            missing_fields = sorted(field for field in required_fields if field not in item)
            if missing_fields:
                errors.append(
                    f"metadata_proposal.{collection_name}[{index}] missing required field(s): "
                    + ", ".join(missing_fields)
                )

    return errors


def validate_output_dir(output_dir: str) -> int:
    """Validate a generated metadata proposal folder."""
    directory = Path(output_dir)
    required_files = [
        "metadata_proposal.json",
        "metadata_proposal.pdf",
        "glossary_terms.md",
        "glossary_terms.pdf",
    ]
    deprecated_files = ["metadata_proposal.md", "metadata_proposal.yaml", "evidence.json"]
    errors = []

    if not directory.is_dir():
        print(f"Error: {directory} is not a directory", file=sys.stderr)
        return 2

    for filename in required_files:
        file_path = directory / filename
        if not file_path.is_file():
            errors.append(f"Missing required file: {filename}")

    for filename in deprecated_files:
        if (directory / filename).exists():
            errors.append(f"Deprecated artifact should not be generated: {filename}")

    json_path = directory / "metadata_proposal.json"
    if json_path.is_file():
        try:
            proposal_data = load_structured_file(json_path)
            errors.extend(validate_proposal_content(proposal_data))
        except Exception as error:  # noqa: BLE001 - validation should report all errors
            errors.append(f"Invalid JSON: {error}")

    pdf_path = directory / "metadata_proposal.pdf"
    if pdf_path.is_file() and pdf_path.stat().st_size == 0:
        errors.append("PDF file is empty")

    glossary_pdf_path = directory / "glossary_terms.pdf"
    if glossary_pdf_path.is_file() and glossary_pdf_path.stat().st_size == 0:
        errors.append("Glossary PDF file is empty")

    glossary_markdown_path = directory / "glossary_terms.md"
    if glossary_markdown_path.is_file():
        glossary_text = glossary_markdown_path.read_text(encoding="utf-8").lower()
        if "glossary" not in glossary_text and "glosario" not in glossary_text:
            errors.append("Glossary markdown missing standalone glossary title")

    if errors:
        print("FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("OK: metadata proposal folder is valid")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    command = sys.argv[1]

    if command == "list-workspaces" and len(sys.argv) == 2:
        list_workspaces()
        return 0
    if command == "list-items" and len(sys.argv) in {3, 4}:
        list_items(sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else None)
        return 0
    if command == "list-lakehouse-tables" and len(sys.argv) == 4:
        list_lakehouse_tables(sys.argv[2], sys.argv[3])
        return 0
    if command == "get-lakehouse-table" and len(sys.argv) == 5:
        get_lakehouse_table(sys.argv[2], sys.argv[3], sys.argv[4])
        return 0
    if command == "list-semantic-models" and len(sys.argv) in {3, 4}:
        list_semantic_models(sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else None)
        return 0
    if command == "export-semantic-model" and len(sys.argv) == 5:
        export_semantic_model(sys.argv[2], sys.argv[3], sys.argv[4])
        return 0
    if command == "render-pdf" and len(sys.argv) == 4:
        render_pdf(sys.argv[2], sys.argv[3])
        return 0
    if command == "render-glossary-md" and len(sys.argv) == 4:
        render_glossary_md(sys.argv[2], sys.argv[3])
        return 0
    if command == "render-glossary-pdf" and len(sys.argv) == 4:
        render_glossary_pdf(sys.argv[2], sys.argv[3])
        return 0
    if command == "render-markdown-pdf" and len(sys.argv) == 4:
        render_markdown_pdf_file(sys.argv[2], sys.argv[3])
        return 0
    if command == "validate" and len(sys.argv) == 3:
        return validate_output_dir(sys.argv[2])

    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
