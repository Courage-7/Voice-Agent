"""Public Composio integration API.

Keep one gateway implementation and one singleton.  The package used to copy
``client.py`` verbatim, which created two independently cached gateway
instances and duplicated every static diagnostic.
"""

from app.integrations.composio.client import (
    BASELINE_PROJECT_APPS,
    ComposioGateway,
    composio_gateway,
)

__all__ = ["BASELINE_PROJECT_APPS", "ComposioGateway", "composio_gateway"]
