**We found it. 🎯** The 500 error is caused by a definite bug in `pipeline.py`, not by the rules file.

The problematic code is here:

```python
if not rule_res["requires_investigation"]:
    ...
    hypotheses_content = [h.get("summary", "") for h in final_state.get("hypotheses", [])]
```

### The problem

`final_state` is only created in the **AI investigation** branch:

```python
else:
    ...
    final_state = investigation_graph.invoke(initial_state)
```

But in the deterministic branch, you're trying to use `final_state` **before it exists**.

So Python raises:

```text
NameError: name 'final_state' is not defined
```

And your `main.py` catches that exception and turns it into HTTP 500.

---

## Fix this exact line

Find:

```python
hypotheses_content = [h.get("summary", "") for h in final_state.get("hypotheses", [])]
```

and change it to:

```python
hypotheses_content = []
```

That's the simplest and correct fix because deterministic rules don't generate AI hypotheses.

### Your corrected deterministic section should be

```python
if not rule_res["requires_investigation"]:
    # Auto classified by rules
    auto_classified += 1
    final_class = rule_res["classification"]
    reasoning = rule_res["reason"]
    steps_log = rule_res["rules_triggered"]
    evidence_list = rule_res.get("evidence_ids", [])

    known_facts = [rule_res["reason"]]

    # Deterministic rules do not generate AI hypotheses
    hypotheses_content = []

    event_date = _parse_event_date(
        rule_res.get("economic_event_date")
    )

    # Map deterministic categories to standard target classifications
    if final_class == "CLEAR_BEFORE_CUTOFF":
        final_class = "BEFORE_CUTOFF"
    elif final_class == "CLEAR_AFTER_CUTOFF":
        final_class = "AFTER_CUTOFF"
```

---

## Why this caused exactly your behavior

Your audit pipeline does:

```text
POST /api/audit/run
        ↓
run_audit()
        ↓
run_evaluation_pipeline()
        ↓
evaluate_transaction_rules()
        ↓
transaction gets deterministic result
        ↓
if not rule_res["requires_investigation"]:
        ↓
uses final_state ❌
        ↓
NameError
        ↓
HTTP 500
```

Your `/api/transactions`, `/api/exceptions`, and `/api/metrics` endpoints can still work because they don't necessarily execute this broken line.

---

## There's another improvement I'd make

Your `main.py` currently hides the traceback:

```python
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

For development, I'd temporarily use:

```python
@app.post("/api/audit/run")
def run_audit():
    """Triggers the full period-end cut-off audit loop across all transactions."""
    try:
        metrics = run_evaluation_pipeline()
        return metrics
    except Exception:
        import traceback
        traceback.print_exc()
        raise
```

That way, if there's **another error after we fix this one**, your terminal will tell us exactly where it is.

You can revert this later.

---

# Then restart and test

Save `pipeline.py`.

If Uvicorn is running with `--reload`, it should reload automatically. Otherwise:

```bash
CTRL+C
```

then:

```bash
uvicorn backend.main:app --reload --port 8000 --log-level debug
```

Then click **Run Audit** again.

### Expected result

Instead of:

```text
POST /api/audit/run HTTP/1.1" 500 Internal Server Error
```

you should hopefully get:

```text
POST /api/audit/run HTTP/1.1" 200 OK
```

and your evaluation results should be generated.

---

### One more thing

I would **not change your `engine.py` rules code yet**. The error we've found is independent of that file.

The immediate fix is:

```python
hypotheses_content = []
```

instead of:

```python
hypotheses_content = [h.get("summary", "") for h in final_state.get("hypotheses", [])]
```

If you make that change and `/api/audit/run` still returns 500, paste the **new terminal traceback**. At that point we'll have moved past this bug and can fix the next one directly.
