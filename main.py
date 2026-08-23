"""Root execution entrypoint for Voice AI Agent server."""

import uvicorn


def main():
    """Start Uvicorn ASGI server hosting the Voice AI Agent."""
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        app_dir="voice-agent",
    )


if __name__ == "__main__":
    main()
