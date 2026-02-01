# core/template_resolver.py
"""
Template Parameter Resolution for Job Chains

Resolves template strings like ${job_name.field} in job parameters
by looking up previous job results and artifacts.

Supports:
- Simple field access: ${job.field}
- Nested fields: ${job.nested.field}
- Array indexing: ${job.files[0]}
- Special accessors: ${job.first_match} → job.files[0]
- Multiple templates in one string: "prefix_${job.x}_suffix"
- Strict/lenient modes for missing references
"""

import re
from typing import Any, Dict, List, Optional, Union


class TemplateResolutionError(Exception):
    """Raised when template resolution fails in strict mode."""
    pass


# Special accessor aliases
SPECIAL_ACCESSORS = {
    "first_match": lambda result: _safe_index(result.get("files", []), 0),
    "all_files": lambda result: result.get("files", []),
    "first_file": lambda result: _safe_index(result.get("files", []), 0),
    "content": lambda result: result.get("content", ""),
}


def _safe_index(lst: List, idx: int, default=None):
    """Safely get list item by index."""
    try:
        return lst[idx] if isinstance(lst, list) and 0 <= idx < len(lst) else default
    except (IndexError, TypeError):
        return default


def _parse_field_path(path: str) -> List[Union[str, int]]:
    """
    Parse a field path like 'foo.bar[0].baz' into tokens.
    
    Returns: ['foo', 'bar', 0, 'baz']
    """
    tokens = []
    # Split by dots, but handle array indices
    parts = path.split('.')
    for part in parts:
        # Check for array index: field[0]
        match = re.match(r'^(\w+)\[(\d+)\]$', part)
        if match:
            tokens.append(match.group(1))
            tokens.append(int(match.group(2)))
        else:
            tokens.append(part)
    return tokens


def _resolve_field_path(obj: Any, path: str, strict: bool = True) -> Any:
    """
    Resolve a field path in an object.
    
    Examples:
        obj = {"foo": {"bar": [1, 2, 3]}}
        _resolve_field_path(obj, "foo.bar[0]") → 1
    """
    tokens = _parse_field_path(path)
    current = obj
    
    for token in tokens:
        if isinstance(token, int):
            # Array index
            current = _safe_index(current, token)
            if current is None:
                if strict:
                    raise TemplateResolutionError(f"Array index {token} out of bounds in path: {path}")
                return None
        elif isinstance(token, str):
            # Dict key
            if isinstance(current, dict):
                current = current.get(token)
                if current is None:
                    if strict:
                        raise TemplateResolutionError(f"Field '{token}' not found in path: {path}")
                    return None
            else:
                if strict:
                    raise TemplateResolutionError(f"Cannot access field '{token}' on non-dict object")
                return None
        else:
            if strict:
                raise TemplateResolutionError(f"Invalid token type in path: {token}")
            return None
    
    return current


def resolve_template_string(
    template: str,
    context: Dict[str, Any],
    strict: bool = True
) -> Any:
    """
    Resolve a template string with ${...} placeholders.
    
    Args:
        template: String potentially containing ${job.field} patterns
        context: Dict mapping job names to their results
        strict: If True, raise error on missing references
    
    Returns:
        - If template is exactly "${...}", returns the resolved value (can be non-string)
        - Otherwise, returns string with all templates replaced
    
    Examples:
        resolve_template_string("${job.field}", ctx) → <value>
        resolve_template_string("prefix_${job.x}_suffix", ctx) → "prefix_value_suffix"
    """
    # Pattern: ${job_name.field.path[0]}
    pattern = r'\$\{([^}]+)\}'
    
    matches = list(re.finditer(pattern, template))
    
    if not matches:
        # No templates, return as-is
        return template
    
    # Check if entire string is a single template
    if len(matches) == 1 and matches[0].group(0) == template:
        # Return the actual value (can be non-string)
        ref = matches[0].group(1)
        return _resolve_reference(ref, context, strict)
    
    # Multiple templates or template within string → string replacement
    result = template
    for match in reversed(matches):  # Reverse to preserve indices
        ref = match.group(1)
        value = _resolve_reference(ref, context, strict)
        
        # Convert to string for replacement
        if value is None:
            value_str = "" if not strict else "None"
        elif isinstance(value, (list, dict)):
            # Don't stringify complex types in the middle of a string
            if strict:
                raise TemplateResolutionError(
                    f"Cannot embed complex type ({type(value).__name__}) in string: {ref}"
                )
            value_str = str(value)
        else:
            value_str = str(value)
        
        result = result[:match.start()] + value_str + result[match.end():]
    
    return result


def _resolve_reference(ref: str, context: Dict[str, Any], strict: bool) -> Any:
    """
    Resolve a single reference like 'job_name.field.path'.
    
    Handles:
    - Special accessors (first_match, all_files)
    - Nested field paths
    - Array indexing
    """
    # Split into job_name and field_path
    parts = ref.split('.', 1)
    job_name = parts[0]
    field_path = parts[1] if len(parts) > 1 else None
    
    # Lookup job result
    if job_name not in context:
        if strict:
            raise TemplateResolutionError(f"Job '{job_name}' not found in context")
        return None
    
    job_result = context[job_name]
    
    if not field_path:
        # Just the job name, return entire result
        return job_result
    
    # Check for special accessors
    first_field = field_path.split('.')[0].split('[')[0]
    if first_field in SPECIAL_ACCESSORS:
        accessor_func = SPECIAL_ACCESSORS[first_field]
        value = accessor_func(job_result)
        
        # If there's more path after the accessor, continue resolving
        remaining_path = field_path[len(first_field):]
        if remaining_path.startswith('.'):
            remaining_path = remaining_path[1:]
        if remaining_path:
            return _resolve_field_path(value, remaining_path, strict)
        return value
    
    # Regular field path resolution
    return _resolve_field_path(job_result, field_path, strict)


def resolve_template_params(
    params: Dict[str, Any],
    context: Dict[str, Any],
    strict: bool = True,
    _visited: Optional[set] = None
) -> Dict[str, Any]:
    """
    Recursively resolve all template strings in a params dict.
    
    Also handles semantic keywords like:
    - "selection": "first_from_previous_job" → resolves to first file from previous job
    - "source": "job_name" → resolves to job result
    
    Args:
        params: Parameters dict potentially containing templates
        context: Resolution context (job results)
        strict: Strict mode for missing references
        _visited: Internal cycle detection
    
    Returns:
        New dict with all templates resolved
    """
    if _visited is None:
        _visited = set()
    
    # Cycle detection (simple)
    params_id = id(params)
    if params_id in _visited:
        if strict:
            raise TemplateResolutionError("Circular reference detected in params")
        return params
    _visited.add(params_id)
    
    resolved = {}
    for key, value in params.items():
        if isinstance(value, str):
            # Check for semantic keywords first
            resolved_value = _resolve_semantic_keyword(key, value, context, strict)
            if resolved_value is not None:
                resolved[key] = resolved_value
            else:
                # Regular template string resolution
                resolved[key] = resolve_template_string(value, context, strict)
        elif isinstance(value, dict):
            # Recursively resolve nested dict
            resolved[key] = resolve_template_params(value, context, strict, _visited)
        elif isinstance(value, list):
            # Recursively resolve list items
            resolved[key] = [
                resolve_template_string(item, context, strict) if isinstance(item, str)
                else resolve_template_params(item, context, strict, _visited) if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            # Non-template value, keep as-is
            resolved[key] = value
    
    _visited.remove(params_id)
    return resolved


def _resolve_semantic_keyword(
    param_name: str,
    param_value: str,
    context: Dict[str, Any],
    strict: bool
) -> Optional[Any]:
    """
    Resolve semantic keywords in parameter values.
    
    Examples:
        "selection": "first_from_previous_job" → first file from previous job
        "source": "job_name" → job result
    
    Returns None if not a semantic keyword.
    """
    # Pattern: "first_from_previous_job"
    if param_value == "first_from_previous_job":
        # Find the most recent job with 'files' in result
        for job_name in reversed(list(context.keys())):
            if job_name.startswith("_"):
                continue  # Skip special keys like _artifacts
            job_result = context[job_name]
            if isinstance(job_result, dict) and "files" in job_result:
                files = job_result["files"]
                if files and len(files) > 0:
                    # Return first file path
                    first_file = files[0]
                    # If it's a dict with 'path' key, extract path
                    if isinstance(first_file, dict):
                        return first_file.get("path", first_file.get("rel_path", str(first_file)))
                    return first_file
        
        if strict:
            raise TemplateResolutionError("No previous job with files found for 'first_from_previous_job'")
        return None
    
    # Pattern: "all_from_previous_job"
    if param_value == "all_from_previous_job":
        for job_name in reversed(list(context.keys())):
            if job_name.startswith("_"):
                continue
            job_result = context[job_name]
            if isinstance(job_result, dict) and "files" in job_result:
                return job_result["files"]
        
        if strict:
            raise TemplateResolutionError("No previous job with files found for 'all_from_previous_job'")
        return None
    
    # Pattern: "source": "job_name" (reference to another job's result)
    if param_name in ["source", "input_from"] and param_value in context:
        return context[param_value]
    
    # Not a semantic keyword
    return None


def build_resolution_context(chain_id: str, storage) -> Dict[str, Any]:
    """
    Build resolution context for a chain.
    
    Returns dict mapping job names to their results:
    {
        "walk_tree_worker": {"ok": True, "files": [...]},
        "read_first_file": {"ok": True, "content": "..."},
        ...
    }
    
    Also includes artifacts under special key "_artifacts".
    """
    from hub.database import get_db
    
    context = {}
    
    with get_db() as conn:
        # Get chain context for artifacts
        chain_ctx = storage.get_chain_context(conn, chain_id)
        if chain_ctx:
            context["_artifacts"] = chain_ctx.get("artifacts", {})
        
        # Get all specs for this chain to find job names
        specs = conn.execute(
            """
            SELECT spec_id, kind, params_json, dispatched_job_id
            FROM chain_specs
            WHERE chain_id=? AND dispatched_job_id IS NOT NULL
            ORDER BY created_at ASC
            """,
            (chain_id,)
        ).fetchall()
        
        for spec_row in specs:
            spec_id = spec_row[0]
            params_json = spec_row[2]
            job_id = spec_row[3]
            
            # Extract job name from params
            params = storage._json_loads(params_json) or {}
            job_name = params.get("name") or spec_id[:8]  # Fallback to spec_id prefix
            
            # Get job result
            job = storage.get_job(job_id)
            if job and job.status == "completed" and job.result:
                context[job_name] = job.result
    
    return context
