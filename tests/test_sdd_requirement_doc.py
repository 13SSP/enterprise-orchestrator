import sys
import shutil
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "cortex-ai" / "backend"))

import main
app = main.app
client = TestClient(app)


def test_sdd_pod_creation_with_requirement_doc():
    """
    Verify creating an SDD pod with a requirement document:
    1. Requirement document is analyzed and decomposed into System Spec, Plan, and modular Features.
    2. Local specs/ directory is created on disk with spec.md and individual feature markdown files.
    3. Requirement document is added to pod documents.
    4. Features appear in Space 1 features list.
    """
    test_local_dir = root_dir / "workspace-projects" / "test-calc-req-doc"
    if test_local_dir.exists():
        try:
            shutil.rmtree(test_local_dir)
        except Exception:
            pass

    req_doc_content = """# DivisionCalculator Requirements

## Overview
The DivisionCalculator is a specialized microservice designed to perform division operations between two numbers. It ensures precision, validates inputs, and provides clear error reporting for mathematical edge cases like division by zero.

## Functional Requirements
1. The system must accept a numerator and a denominator as input.
2. The system must return the quotient as a floating-point number.
3. The system must handle division by zero by returning a specific error message and status code.
4. The system must support negative numbers and decimals.

## Non-Functional Requirements
1. **Validation**: All inputs must be validated using Pydantic V2.
2. **Performance**: Stateless execution with sub-50ms response time.
3. **Reliability**: 100% test coverage for the calculation logic.
"""

    payload = {
        "name": "DivisionCalculator Pod",
        "description": "High-precision division microservice with spec decomposition",
        "workspace_type": "sdd",
        "visibility": "private",
        "requirement_doc_name": "DivisionCalculator_Requirements.md",
        "requirement_doc_content": req_doc_content,
        "sdd_config": {
            "local_space_path": str(test_local_dir).replace("\\", "/"),
            "git_action": "init"
        }
    }

    r = client.post("/api/pods?persona=bob_ops", json=payload)
    assert r.status_code == 200
    data = r.json()
    ws = data["workspace"]
    ws_id = ws["workspace_id"]

    try:
        # 1. Verify requirement doc metadata and document entry
        assert "requirement_doc" in ws and ws["requirement_doc"] is not None
        assert ws["requirement_doc"]["name"] == "DivisionCalculator_Requirements.md"
        assert "DivisionCalculator" in ws["requirement_doc"]["content"]

        docs = ws.get("documents", [])
        assert any("DivisionCalculator_Requirements" in (d.get("name") or "") for d in docs)

        # 2. Verify System Spec and Technical Plan generated
        assert ws.get("spec") is not None
        assert "raw_markdown" in ws["spec"]

        assert ws.get("plan") is not None
        assert len(ws["plan"].get("data_models", [])) >= 1

        # 3. Verify Features array decomposed from requirement doc
        features = ws.get("features", [])
        assert len(features) >= 1
        feat_titles = [f["title"] for f in features]
        # Should have domain features
        assert any("division" in t.lower() or "calculation" in t.lower() or "core" in t.lower() for t in feat_titles)

        # 4. Verify local spec files on disk
        specs_folder = test_local_dir / "specs"
        assert specs_folder.exists(), "specs folder must be created in local working directory"
        
        # Original requirement doc must be saved in specs folder
        assert (specs_folder / "DivisionCalculator_Requirements.md").exists()
        
        # System spec must be saved
        assert (specs_folder / "spec.md").exists() or (specs_folder / "system_spec.md").exists()
        
        # Feature spec files must be saved
        spec_files = list(specs_folder.glob("feat-*.md"))
        assert len(spec_files) >= 1, f"Expected at least 1 feature spec file, found: {spec_files}"

        # 5. Verify feature listing via API
        r_feat = client.get(f"/api/pods/{ws_id}/features?persona=bob_ops")
        assert r_feat.status_code == 200
        feat_list = r_feat.json()["features"]
        assert len(feat_list) >= 1

    finally:
        # Cleanup pod and test directory
        client.delete(f"/api/pods/{ws_id}?persona=bob_ops")
        if test_local_dir.exists():
            try:
                shutil.rmtree(test_local_dir)
            except Exception:
                pass
