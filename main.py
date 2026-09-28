"""Root execution entrypoint for Voice AI Agent server."""

import os

import uvicorn


def main():
    """Start Uvicorn ASGI server hosting the Voice AI Agent."""
    # The frontend is normally opened by a Windows browser while the API runs
    # in WSL. Binding only to WSL loopback makes every browser request hang.
    # Keep this aligned with Settings.server_host without importing the app
    # package before Uvicorn adds ``voice-agent`` to its import path.
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8000"))
    # File watching is opt-in. On Windows-mounted workspaces it can crash the
    # launcher when it reaches an unreadable tool cache, taking the API down.
    reload_enabled = os.getenv("SERVER_RELOAD", "false").lower() in {"1", "true", "yes"}
    print("=" * 60)
    print("  Starting Voice AI Platform...")
    print(f"  Frontend UI:      http://localhost:{port}/")
    print(f"  Swagger Docs:     http://localhost:{port}/docs")
    print(f"  Voice Playground: http://localhost:{port}/playground")
    print("=" * 60)
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload_enabled,
        app_dir="voice-agent",
    )


if __name__ == "__main__":
    main()
