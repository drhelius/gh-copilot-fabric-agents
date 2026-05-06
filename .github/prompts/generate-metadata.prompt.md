---
description: "Generate reviewable metadata proposals for Microsoft Fabric lakehouse tables or semantic models. Use when: metadata creation, Purview mapping, glossary, classification, sensitivity, lineage, data quality rules."
agent: "fabric-metadata-creation"
tools: [vscode, execute, read, agent, browser, edit, search, web, 'fabric-mcp/*', todo]
argument-hint: "Workspace, lakehouse table(s), or semantic model(s) to analyze"
---

Extract the workspace, lakehouse, tables, files, semantic model, and business context from the user's input above. If the target assets are missing or ambiguous, discover candidates with Fabric MCP tools or the metadata helper script, then ask the user to select the assets once. After target selection, execute all workflow phases automatically and generate only these local artifacts: `metadata_proposal.json`, `metadata_proposal.pdf`, `glossary_terms.md`, and `glossary_terms.pdf`. Write human-readable content in Spanish, but preserve original source identifiers and names exactly.
