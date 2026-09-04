import json
import os

from backend.evaluation.pipeline import GT_PATH


def test_ground_truth_exists_and_covers_fifty_plus_cases():
    assert os.path.exists(GT_PATH), "Run python -m backend.database.seed"
    with open(GT_PATH) as f:
        gt = json.load(f)
    assert len(gt) >= 50
    classes = {row["classification"] for row in gt.values()}
    assert "BEFORE_CUTOFF" in classes
    assert "AFTER_CUTOFF" in classes
    assert "UNRESOLVED" in classes
    assert "POTENTIAL_MISSTATEMENT" in classes


def test_ground_truth_not_imported_by_agent_graph():
    import inspect
    from backend.agents import graph, nodes
    graph_src = inspect.getsource(graph)
    nodes_src = inspect.getsource(nodes)
    assert "ground_truth" not in graph_src
    assert "ground_truth" not in nodes_src
