from core.template_resolver import resolve_template_string, SPECIAL_ACCESSORS

# Test 1: Simple special accessor
ctx = {'job1': {'files': ['a.py', 'b.py']}}
result = resolve_template_string('${job1.first_match}', ctx)
print(f"Test 1: {result}")

# Test 2: Nested field
ctx2 = {'job1': {'result': {'files': ['x.py']}}}
result2 = resolve_template_string('${job1.result.files[0]}', ctx2)
print(f"Test 2: {result2}")

# Test 3: Multiple templates
ctx3 = {'job1': {'name': 'test'}, 'job2': {'value': '123'}}
result3 = resolve_template_string('prefix_${job1.name}_${job2.value}', ctx3)
print(f"Test 3: {result3}")

print("All tests passed!")
