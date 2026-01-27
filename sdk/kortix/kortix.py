from .api import agents, threads
from .agent import KortixAgent
from .thread import KortixThread
from .tools import AgentPressTools, MCPTools


class Kortix:
    """
    Kortix SDK client with V2 API support.
    
    The SDK automatically uses V2 endpoints when available and falls back
    to V1 if V2 encounters errors.
    
    Args:
        api_key: Kortix API key
        api_url: Base API URL (default: https://api.kortix.com/v1)
        use_v2: Whether to use V2 endpoints with V1 fallback (default: True)
    """
    
    def __init__(
        self,
        api_key: str,
        api_url: str = "https://api.kortix.com/v1",
        use_v2: bool = True,
    ):
        # Derive V2 URL from V1 URL
        self._api_url_v1 = api_url
        self._api_url_v2 = api_url.replace("/v1", "/v2") if "/v1" in api_url else f"{api_url.rstrip('/')}/v2"
        self._use_v2 = use_v2
        
        # Use V2 URL if enabled, clients handle fallback internally
        active_url = self._api_url_v2 if use_v2 else self._api_url_v1
        
        self._agents_client = agents.create_agents_client(
            active_url, 
            api_key,
            fallback_url=self._api_url_v1 if use_v2 else None,
        )
        self._threads_client = threads.create_threads_client(
            active_url, 
            api_key,
            fallback_url=self._api_url_v1 if use_v2 else None,
        )

        self.Agent = KortixAgent(self._agents_client)
        self.Thread = KortixThread(self._threads_client)
    
    @property
    def is_using_v2(self) -> bool:
        """Check if SDK is configured to use V2 endpoints."""
        return self._use_v2
    
    @property
    def api_url(self) -> str:
        """Get the active API URL."""
        return self._api_url_v2 if self._use_v2 else self._api_url_v1
