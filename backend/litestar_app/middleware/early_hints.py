"""
HTTP 103 Early Hints Middleware

Sends preload hints for critical resources while the server processes the request.
This allows the browser to start fetching resources before the full response arrives.

Requirements:
- HTTP/2 or HTTP/3 connection
- Cloudflare or nginx 1.25+ configured to pass 103 responses
"""

from litestar.middleware import AbstractMiddleware
from litestar.types import ASGIApp, Receive, Scope, Send, Message
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class EarlyHintsMiddleware(AbstractMiddleware):
    """
    Middleware that sends HTTP 103 Early Hints for critical resources.
    
    The browser can start fetching these resources while waiting for
    the main response, reducing LCP by 50-200ms.
    """
    
    # Critical resources to preload - customize based on your app
    CRITICAL_RESOURCES: List[Tuple[str, str, str]] = [
        # (url, as_type, mime_type)
        ('/fonts/Roobert-Regular.woff2', 'font', 'font/woff2'),
        ('/fonts/Roobert-Medium.woff2', 'font', 'font/woff2'),
    ]
    
    # Routes that benefit from early hints (heavy pages)
    ENABLED_ROUTES = {
        '/',
        '/dashboard',
        '/threads',
        '/projects',
        '/agents',
    }
    
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._hints_header = self._build_link_header()
    
    def _build_link_header(self) -> bytes:
        """Build the Link header value for early hints."""
        links = []
        for url, as_type, mime_type in self.CRITICAL_RESOURCES:
            if as_type == 'font':
                links.append(f'<{url}>; rel=preload; as={as_type}; type={mime_type}; crossorigin')
            else:
                links.append(f'<{url}>; rel=preload; as={as_type}; type={mime_type}')
        return ', '.join(links).encode()
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        path = scope.get("path", "")
        
        # Only send early hints for enabled routes
        if path not in self.ENABLED_ROUTES:
            await self.app(scope, receive, send)
            return
        
        # Check if client supports HTTP/2+
        http_version = scope.get("http_version", "1.1")
        if http_version < "2":
            await self.app(scope, receive, send)
            return
        
        hints_sent = False
        
        async def send_with_hints(message: Message) -> None:
            nonlocal hints_sent
            
            # Send 103 Early Hints before the actual response
            if message["type"] == "http.response.start" and not hints_sent:
                hints_sent = True
                try:
                    # Send 103 Early Hints
                    await send({
                        "type": "http.response.start",
                        "status": 103,
                        "headers": [(b"link", self._hints_header)],
                    })
                    logger.debug(f"Sent 103 Early Hints for {path}")
                except Exception as e:
                    # Some ASGI servers don't support 1xx responses
                    logger.debug(f"Early hints not supported: {e}")
            
            await send(message)
        
        await self.app(scope, receive, send_with_hints)


class EarlyHintsConfig:
    """Configuration for early hints based on route patterns."""
    
    # Add dynamic hints based on route
    ROUTE_HINTS = {
        '/dashboard': [
            ('/api/v2/threads', 'fetch', 'application/json'),
            ('/api/v2/projects', 'fetch', 'application/json'),
        ],
        '/threads': [
            ('/api/v2/agents', 'fetch', 'application/json'),
        ],
    }
