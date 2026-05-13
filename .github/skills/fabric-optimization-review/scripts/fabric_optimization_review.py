"""
Fabric Optimization Review — inspect tables, semantic models, and workspace items via Fabric REST API.

Authentication: Uses Azure CLI credentials (az login) via DefaultAzureCredential.
No .env file needed if you are already logged in.

Usage:
    python fabric_optimization_review.py table-info  <workspace_id> <lakehouse_id> <table_name>
    python fabric_optimization_review.py get-model   <workspace_id> <model_id>
    python fabric_optimization_review.py list-items  <workspace_id> [--type lakehouse|semanticmodel]
    python fabric_optimization_review.py list-tables <workspace_id> <lakehouse_id>

Commands:
    table-info   — Get Delta table metadata (properties, file stats, schema, partitioning)
    get-model    — Download semantic model definition (TMDL files) for review
    list-items   — List workspace items, optionally filtered by type
    list-tables  — List all tables in a lakehouse with schemas
"""

import sys
import os
import json
import base64
import requests
from azure.identity import DefaultAzureCredential

FABRIC_API = "https://api.fabric.microsoft.com/v1"
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"


def get_headers():
    """Get auth headers using the logged-in user's Azure CLI credentials."""
    credential = DefaultAzureCredential()
    token = credential.get_token(FABRIC_SCOPE)
    return {
        "Authorization": f"Bearer {token.token}",
        "Content-Type": "application/json",
    }


def table_info(workspace_id: str, lakehouse_id: str, table_name: str):
    """Get Delta table metadata including properties, schema, and file stats.

    Reads the Delta log to extract:
    - Table schema (columns, types, nullable)
    - Table properties (V-Order, partitioning, retention)
    - File-level statistics (count, sizes)
    - Partition columns
    """
    headers = get_headers()

    # Get lakehouse info for OneLake path
    lh_url = f"{FABRIC_API}/workspaces/{workspace_id}/lakehouses/{lakehouse_id}"
    lh_resp = requests.get(lh_url, headers=headers, timeout=30)

    if lh_resp.status_code != 200:
        print(f"Error getting lakehouse: {lh_resp.status_code}: {lh_resp.text}", file=sys.stderr)
        sys.exit(1)

    lh_data = lh_resp.json()
    onelake_path = lh_data.get("properties", {}).get("oneLakeTablesPath", "")

    if not onelake_path:
        print("Error: oneLakeTablesPath not found in lakehouse properties", file=sys.stderr)
        sys.exit(1)

    result = {
        "table_name": table_name,
        "lakehouse": lh_data.get("displayName", ""),
        "schema": [],
        "properties": {},
        "partition_columns": [],
        "file_stats": {},
    }

    # Read Delta log for schema and metadata
    delta_log_url = f"{onelake_path}/{table_name}/_delta_log/00000000000000000000.json"
    try:
        delta_resp = requests.get(delta_log_url, headers=headers, timeout=30)
        if delta_resp.status_code == 200:
            add_file_count = 0
            total_size = 0
            file_sizes = []

            for line in delta_resp.text.strip().split("\n"):
                entry = json.loads(line)

                if "metaData" in entry:
                    meta = entry["metaData"]
                    # Schema
                    schema_str = meta.get("schemaString", "{}")
                    schema = json.loads(schema_str)
                    for field in schema.get("fields", []):
                        result["schema"].append({
                            "name": field.get("name"),
                            "type": field.get("type"),
                            "nullable": field.get("nullable", True),
                        })

                    # Properties
                    result["properties"] = meta.get("configuration", {})

                    # Partition columns
                    result["partition_columns"] = meta.get("partitionColumns", [])

                if "add" in entry:
                    add_file_count += 1
                    size = entry["add"].get("size", 0)
                    total_size += size
                    file_sizes.append(size)

            if file_sizes:
                file_sizes.sort()
                result["file_stats"] = {
                    "file_count": add_file_count,
                    "total_size_bytes": total_size,
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                    "avg_file_size_mb": round(total_size / add_file_count / (1024 * 1024), 2),
                    "min_file_size_mb": round(file_sizes[0] / (1024 * 1024), 2),
                    "max_file_size_mb": round(file_sizes[-1] / (1024 * 1024), 2),
                    "median_file_size_mb": round(file_sizes[len(file_sizes) // 2] / (1024 * 1024), 2),
                }
        else:
            print(f"Warning: Could not read Delta log (HTTP {delta_resp.status_code})", file=sys.stderr)
    except Exception as e:
        print(f"Warning: Error reading Delta log: {e}", file=sys.stderr)

    # Try reading additional log files for OPTIMIZE/VACUUM history
    for i in range(1, 20):
        log_num = str(i).zfill(20)
        log_url = f"{onelake_path}/{table_name}/_delta_log/{log_num}.json"
        try:
            resp = requests.get(log_url, headers=headers, timeout=10)
            if resp.status_code != 200:
                break
            for line in resp.text.strip().split("\n"):
                entry = json.loads(line)
                if "commitInfo" in entry:
                    op = entry["commitInfo"].get("operation", "")
                    if op in ("OPTIMIZE", "VACUUM START", "VACUUM END"):
                        if "maintenance_history" not in result:
                            result["maintenance_history"] = []
                        result["maintenance_history"].append({
                            "operation": op,
                            "timestamp": entry["commitInfo"].get("timestamp"),
                            "metrics": entry["commitInfo"].get("operationMetrics", {}),
                        })
        except Exception:
            break

    print(json.dumps(result, indent=2))
    return result


def get_semantic_model(workspace_id: str, model_id: str):
    """Download semantic model definition (TMDL) for review.

    Uses GET /v1/workspaces/{id}/semanticModels/{id} with format=TMDL
    to retrieve the model definition files.
    """
    headers = get_headers()

    # Get model info
    url = f"{FABRIC_API}/workspaces/{workspace_id}/semanticModels/{model_id}"
    resp = requests.get(url, headers=headers, timeout=30)

    if resp.status_code != 200:
        print(f"Error {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)

    model_info = resp.json()
    print(f"Model: {model_info.get('displayName', 'Unknown')}")
    print(f"ID: {model_info.get('id', '')}")

    # Get definition
    def_url = f"{url}/getDefinition?format=TMDL"
    def_resp = requests.post(def_url, headers=headers, timeout=60)

    if def_resp.status_code == 200:
        definition = def_resp.json()
        parts = definition.get("definition", {}).get("parts", [])
        result = {"model_name": model_info.get("displayName"), "files": {}}

        for part in parts:
            path = part.get("path", "")
            payload = part.get("payload", "")
            try:
                content = base64.b64decode(payload).decode("utf-8")
                result["files"][path] = content
            except Exception:
                result["files"][path] = "(binary or decode error)"

        print(json.dumps(result, indent=2))
        return result
    elif def_resp.status_code == 202:
        # Long-running operation
        location = def_resp.headers.get("Location")
        print(f"Definition retrieval in progress. Poll: {location}")
        return None
    else:
        print(f"Error getting definition: {def_resp.status_code}: {def_resp.text}", file=sys.stderr)
        sys.exit(1)


def list_items(workspace_id: str, item_type: str = None):
    """List workspace items, optionally filtered by type."""
    headers = get_headers()
    url = f"{FABRIC_API}/workspaces/{workspace_id}/items"
    resp = requests.get(url, headers=headers, timeout=30)

    if resp.status_code != 200:
        print(f"Error {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)

    items = resp.json().get("value", [])

    if item_type:
        type_map = {
            "lakehouse": "Lakehouse",
            "semanticmodel": "SemanticModel",
            "notebook": "Notebook",
            "report": "Report",
        }
        fabric_type = type_map.get(item_type.lower(), item_type)
        items = [i for i in items if i.get("type") == fabric_type]

    if not items:
        print("No items found.")
    else:
        for item in items:
            print(f"{item.get('id')}  {item.get('type'):20s}  {item.get('displayName')}")

    return items


def list_tables(workspace_id: str, lakehouse_id: str):
    """List all tables in a lakehouse with their column schemas."""
    headers = get_headers()

    url = f"{FABRIC_API}/workspaces/{workspace_id}/lakehouses/{lakehouse_id}/tables"
    resp = requests.get(url, headers=headers, timeout=60)

    if resp.status_code != 200:
        print(f"Error {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)

    tables_data = resp.json().get("data", [])
    if not tables_data:
        print("No tables found.")
        return []

    # Get OneLake path for Delta log reading
    lh_resp = requests.get(
        f"{FABRIC_API}/workspaces/{workspace_id}/lakehouses/{lakehouse_id}",
        headers=headers, timeout=30
    )
    lh_data = lh_resp.json()
    onelake_path = lh_data.get("properties", {}).get("oneLakeTablesPath", "")

    results = []
    for table_info_item in tables_data:
        table_name = table_info_item.get("name", "unknown")
        table_format = table_info_item.get("format", "unknown")
        table = {"name": table_name, "format": table_format, "columns": []}

        if table_format.lower() == "delta" and onelake_path:
            delta_log_url = f"{onelake_path}/{table_name}/_delta_log/00000000000000000000.json"
            try:
                delta_resp = requests.get(delta_log_url, headers=headers, timeout=30)
                if delta_resp.status_code == 200:
                    for line in delta_resp.text.strip().split("\n"):
                        entry = json.loads(line)
                        if "metaData" in entry:
                            schema_str = entry["metaData"].get("schemaString", "{}")
                            schema = json.loads(schema_str)
                            for field in schema.get("fields", []):
                                table["columns"].append({
                                    "name": field.get("name"),
                                    "type": field.get("type"),
                                    "nullable": field.get("nullable", True),
                                })
                            break
            except Exception as e:
                print(f"  Warning: Could not read Delta log for {table_name}: {e}", file=sys.stderr)

        results.append(table)

    print(json.dumps(results, indent=2))
    return results


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "table-info" and len(sys.argv) == 5:
        table_info(sys.argv[2], sys.argv[3], sys.argv[4])
    elif command == "get-model" and len(sys.argv) == 4:
        get_semantic_model(sys.argv[2], sys.argv[3])
    elif command == "list-items":
        item_type = None
        ws_id = sys.argv[2] if len(sys.argv) > 2 else None
        if not ws_id:
            print("Error: workspace_id required", file=sys.stderr)
            sys.exit(1)
        # Check for --type flag
        if "--type" in sys.argv:
            idx = sys.argv.index("--type")
            if idx + 1 < len(sys.argv):
                item_type = sys.argv[idx + 1]
        list_items(ws_id, item_type)
    elif command == "list-tables" and len(sys.argv) == 4:
        list_tables(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
