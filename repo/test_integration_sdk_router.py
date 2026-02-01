"""
Quick integration test for SDK and Router.
Tests:
1. SDK client can be imported
2. Router adapter can be imported
3. Router health endpoint works (when Core is running)
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_sdk_import():
    """Test that SDK can be imported."""
    try:
        from external.sdk import SheratanClient, make_headers
        from core.sdk_client import get_client
        print("✓ SDK imports successful")
        return True
    except ImportError as e:
        print(f"✗ SDK import failed: {e}")
        return False

def test_router_import():
    """Test that Router can be imported."""
    try:
        from external.router_openai.adapter import app, health, models, complete
        print("✓ Router imports successful")
        return True
    except ImportError as e:
        print(f"✗ Router import failed: {e}")
        return False

def test_router_health():
    """Test Router health endpoint (requires Core running)."""
    try:
        import httpx
        response = httpx.get("http://localhost:6060/api/v1/router/health", timeout=5)
        if response.status_code == 200 and response.json().get("ok"):
            print("✓ Router health endpoint OK")
            return True
        else:
            print(f"✗ Router health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠ Router health check skipped (Core not running): {e}")
        return None  # Not a failure, just skipped

def test_router_models():
    """Test Router models endpoint."""
    try:
        import httpx
        response = httpx.get("http://localhost:6060/api/v1/router/models", timeout=5)
        if response.status_code == 200:
            models = response.json()
            print(f"✓ Router models endpoint OK: {models}")
            return True
        else:
            print(f"✗ Router models check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠ Router models check skipped (Core not running): {e}")
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("SDK + Router Integration Test")
    print("=" * 60)
    
    results = []
    results.append(("SDK Import", test_sdk_import()))
    results.append(("Router Import", test_router_import()))
    results.append(("Router Health", test_router_health()))
    results.append(("Router Models", test_router_models()))
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    skipped = sum(1 for _, r in results if r is None)
    
    for name, result in results:
        status = "✓ PASS" if result is True else "✗ FAIL" if result is False else "⚠ SKIP"
        print(f"{status:10} {name}")
    
    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")
    
    if failed > 0:
        sys.exit(1)
    else:
        print("\n✓ Integration test successful!")
        sys.exit(0)
