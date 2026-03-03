"""Amplifier Runtime HTTP Server.

Creates the Starlette ASGI application with CORS and all routes.

Routes:
  /health          - Health check
  /v1/session/*    - Session CRUD + prompt execution (SSE)
  /v1/event        - Global SSE event stream
  /v1/modules      - Module discovery
"""

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount

from .routes import routes


def create_app() -> Starlette:
    """Create the Amplifier HTTP server application."""
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        ),
    ]

    app = Starlette(
        routes=[Mount("/v1", routes=routes)],
        middleware=middleware,
    )
    return app
