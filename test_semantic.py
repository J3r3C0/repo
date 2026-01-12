from core.template_resolver import resolve_template_params, _resolve_semantic_keyword

# Test semantic keyword resolution
print("Testing semantic keyword resolution...")

# Test 1: first_from_previous_job
ctx1 = {
    "walk_tree_job": {
        "ok": True,
        "files": ["worker/__init__.py", "worker/worker_loop.py", "worker/state_store.py"]
    }
}

params1 = {
    "selection": "first_from_previous_job"
}

resolved1 = resolve_template_params(params1, ctx1, strict=True)
print(f"Test 1 - first_from_previous_job:")
print(f"  Input:  {params1}")
print(f"  Output: {resolved1}")
assert resolved1["selection"] == "worker/__init__.py", f"Expected 'worker/__init__.py', got {resolved1['selection']}"
print("  ✅ PASS")

# Test 2: Combined with template strings
ctx2 = {
    "job1": {"files": ["a.py", "b.py"]},
    "job2": {"name": "test"}
}

params2 = {
    "path": "first_from_previous_job",
    "prefix": "${job2.name}"
}

resolved2 = resolve_template_params(params2, ctx2, strict=True)
print(f"\nTest 2 - Combined semantic + template:")
print(f"  Input:  {params2}")
print(f"  Output: {resolved2}")
assert resolved2["path"] == "a.py", f"Expected 'a.py', got {resolved2['path']}"
assert resolved2["prefix"] == "test", f"Expected 'test', got {resolved2['prefix']}"
print("  ✅ PASS")

# Test 3: Nested params
ctx3 = {
    "walk_job": {"files": ["x.py", "y.py"]}
}

params3 = {
    "targets": [
        {"path": "first_from_previous_job"},
        {"path": "${walk_job.files[1]}"}
    ]
}

resolved3 = resolve_template_params(params3, ctx3, strict=True)
print(f"\nTest 3 - Nested params:")
print(f"  Input:  {params3}")
print(f"  Output: {resolved3}")
assert resolved3["targets"][0]["path"] == "x.py"
assert resolved3["targets"][1]["path"] == "y.py"
print("  ✅ PASS")

print("\n✅ All semantic keyword tests passed!")
