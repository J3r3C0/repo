"""
SDK Client Wrapper for Sheratan Core.
Provides factory function for creating SDK clients with Core-specific defaults.
"""

from external.sdk import SheratanClient
from typing import Optional


def get_client(api_base: Optional[str] = None) -> SheratanClient:
    """
    Factory for SDK Client with Core-specific defaults.
    
    Args:
        api_base: Optional API base URL. Defaults to http://localhost:6060
        
    Returns:
        Configured SheratanClient instance
    """
    return SheratanClient(api_base=api_base or "http://localhost:6060")
