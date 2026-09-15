#!/usr/bin/env python3
"""Deployment-level boundary audit harness.

This tool prepares an auditable inventory from a frozen deployment checkout.
It deliberately returns AMBIGUOUS unless an auditor supplies deployment-level
observations proving completeness. Repository inspection is evidence input,
not an independent completeness claim.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
from typing import Iterable

REQUIRED = {
    "process_identity": "processes and OS identities",
    "ipc": "IPC endpoints, sockets, pipes, queues, shared memory",
    "filesystem": "filesystem paths and file descriptors",
    "privileged_helpers": "adapters and privileged helpers",
    "direct_api": "importable/direct/deprecated APIs",
    "recovery": "startup/recovery/migration/reconciliation",
    "race_toctou": "race and TOCTOU paths",
    "side_channels": "subprocess/plugin/network/side channels",
}
SUSPICIOUS_CALLS = {
    "open", "os.open", "os.write", "os.replace", "os.rename", "os.unlink",
    "subprocess.run", "subprocess.Popen", "subprocess.call", "os.system",
    "socket.socket", "socket.create_connection", "os.pipe", "os.pipe2",
}


def py_files(root: Path) -> Iterable[Path]:
    yield from root.rglob("*.py")


def dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = dotted(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    return "<dynamic>"


def inventory(root: Path) -> dict:
    files = []
    calls = []
    imports = []
    for path in py_files(root):
        if any(part in {".git", ".venv", "venv", "__pycache__"} for part in path.parts):
            continue
        rel = str(path.relative_to(root))
        files.append(rel)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append({"file": rel, "line": node.lineno, "module": dotted(node.module) if isinstance(node, ast.ImportFrom) else ",".join(a.name for a in node.names)})
            elif isinstance(node, ast.Call):
                name = dotted(node.func)
                if name in SUSPICIOUS_CALLS or any(token in name.lower() for token in ("commit", "write", "publish", "enqueue", "send")):
                    calls.append({"file": rel, "line": node.lineno, "call": name})
    return {
        "files": sorted(files),
        "suspicious_calls": sorted(calls, key=lambda x: (x["file"], x["line"])),
        "imports": sorted(imports, key=lambda x: (x["file"], x["line"])),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--output", default="deployment-boundary-audit.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    evidence = inventory(root)
    result = {
        "evidence_type": "deployment-boundary-escape-audit-harness",
        "scope": str(root),
        "verdict": "AMBIGUOUS",
        "reason": "Static repository inventory cannot establish deployment-level interface completeness independently.",
        "required_independent_checks": REQUIRED,
        "static_inventory": evidence,
        "external_observations": [],
        "auditor_conclusion": None,
        "instructions": [
            "Freeze the deployment and record provider/service/database identifiers.",
            "Enumerate OS identities, reachable IPC, filesystem write paths, helpers and adapters.",
            "Attempt adversarial writes through every discovered alternate path.",
            "Exercise startup/recovery/migration/reconciliation and race/TOCTOU cases.",
            "Record subprocess/plugin/network side-channel attempts.",
            "Set auditor_conclusion only from independently collected deployment evidence.",
        ],
    }
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": result["verdict"], "output": args.output, "suspicious_calls": len(evidence["suspicious_calls"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
