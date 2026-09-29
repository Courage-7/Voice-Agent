"""Verify installed release artifacts with fake providers and no real credentials.

Usage: python scripts/verify_release.py wheel dist/voice_agent-0.1.0-py3-none-any.whl
       python scripts/verify_release.py image voice-agent:ci
"""

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


SMOKE = r'''
import hashlib
import os
from pathlib import Path
import re
import sys
from unittest.mock import AsyncMock, patch

os.environ["ENVIRONMENT"] = "testing"
os.environ["VOICE_PIPELINE_MODE"] = "deepgram_agent"
for name in ("DEEPGRAM_API_KEY", "GROQ_API_KEY", "COMPOSIO_API_KEY", "DATABASE_URL", "NEON_DATABASE_URL"):
    os.environ[name] = ""
if len(sys.argv) > 1:
    installed_root = Path(sys.argv[1]).resolve()
    sys.path.insert(0, str(installed_root))
    os.environ["FRONTEND_DIST_PATH"] = sys.argv[2]
else:
    installed_root = Path("/opt/venv")
    assert os.getuid() != 0, "Release image must run as a non-root user"

import app
from app.auth.clerk import create_test_token
from app.core.config import settings
from app.integrations.deepgram.agent_session import DeepgramVoiceAgentSession
from app.main import app as application
from starlette.testclient import TestClient

app_path = Path(app.__file__).resolve()
assert app_path.is_relative_to(installed_root), f"Imported checkout instead of installed artifact: {app_path}"
installed_modules = {
    path.relative_to(app_path.parent).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in app_path.parent.rglob("*.py")
}
assert installed_modules == EXPECTED_RUNTIME, "Installed backend does not match the source snapshot; rebuild the artifact"
assert (app_path.parent / "realtime/playground.html").is_file()
assert not (app_path.parent / "graphify-out").exists()
for directory in (app_path.parent, settings.frontend_dist_path):
    assert not any(p.name.startswith(".env") for p in directory.rglob("*")), "Environment file in release artifact"

with patch.object(DeepgramVoiceAgentSession, "connect", new=AsyncMock(return_value=True)), \
     patch.object(DeepgramVoiceAgentSession, "close", new=AsyncMock()) as close, \
     patch.object(DeepgramVoiceAgentSession, "send_audio", new=AsyncMock()) as audio, \
     TestClient(application) as client:
    health = client.get("/api/health")
    assert health.status_code == 200
    assert not any(health.json()["providers"].values())
    page = client.get("/")
    assert page.status_code == 200
    assets = re.findall(r'(?:src|href)=["\'](/assets/[^"\']+)', page.text)
    assert assets, "Frontend index did not reference built assets"
    for asset in assets:
        response = client.get(asset)
        assert response.status_code == 200 and response.content, f"Missing frontend asset: {asset}"
    assert client.get("/playground").status_code == 200
    token = create_test_token(user_id="release_test", email="release@example.invalid")
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post("/api/voice/sessions", json={}, headers=headers)
    assert created.status_code == 200
    session_id = created.json()["session_id"]
    with client.websocket_connect(f"/api/voice/ws/{session_id}", headers=headers) as ws:
        assert ws.receive_json() == {"type": "SessionStateChange", "state": "connected"}
        assert ws.receive_json() == {"type": "SessionStateChange", "state": "listening"}
        ws.send_bytes(b"\0\0" * 80)
    audio.assert_awaited_once()
    close.assert_awaited_once()
print("PASS: installed backend, packaged HTML, frontend assets, API and fake-provider WebSocket")
'''


def smoke_script() -> str:
    source = Path(__file__).resolve().parents[1] / "voice-agent" / "app"
    expected = {
        path.relative_to(source).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source.rglob("*.py") if "graphify-out" not in path.parts
    }
    return f"EXPECTED_RUNTIME = {expected!r}\n" + SMOKE


def verify_wheel(wheel: Path) -> None:
    wheel = wheel.resolve(strict=True)
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
    required = {"app/__init__.py", "app/main.py", "app/realtime/playground.html"}
    if not required <= names:
        raise RuntimeError(f"Wheel is missing runtime files: {sorted(required - names)}")
    source = Path(__file__).resolve().parents[1] / "voice-agent" / "app"
    expected_modules = {
        "app/" + path.relative_to(source).as_posix()
        for path in source.rglob("*.py") if "graphify-out" not in path.parts
    }
    packaged_modules = {name for name in names if name.startswith("app/") and name.endswith(".py")}
    if packaged_modules != expected_modules:
        raise RuntimeError(
            "Wheel does not match runtime source modules; build from a fresh source archive with uv build. "
            f"Missing: {sorted(expected_modules - packaged_modules)}; "
            f"obsolete: {sorted(packaged_modules - expected_modules)}"
        )
    if any("graphify-out" in name or any(part.startswith(".env") for part in Path(name).parts) for name in names):
        raise RuntimeError("Wheel contains local graph data or environment files")
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("uv is required to install the wheel for verification")
    with tempfile.TemporaryDirectory(prefix="voice-agent-release-") as folder:
        temporary = Path(folder)
        installed = temporary / "installed"
        subprocess.run([
            uv, "pip", "install", "--no-cache", "--no-index", "--no-deps",
            "--python", sys.executable, "--target", str(installed), str(wheel),
        ], check=True)
        frontend = temporary / "frontend"
        (frontend / "assets").mkdir(parents=True)
        (frontend / "index.html").write_text('<!doctype html><script src="/assets/smoke.js"></script>', encoding="utf-8")
        (frontend / "assets/smoke.js").write_text('console.log("release fixture")', encoding="utf-8")
        subprocess.run([
            sys.executable, "-I", "-c", smoke_script(), str(installed), str(frontend),
        ], cwd=temporary, check=True, timeout=60)


def verify_image(tag: str) -> None:
    # Exercise the actual installed image under its non-root user, without
    # attaching a network or supplying provider credentials. TestClient runs
    # the application lifespan, HTTP routes and WebSocket inside the container.
    subprocess.run([
        "docker", "run", "--rm", "--network", "none", "-i",
        "--env", "ENVIRONMENT=testing", tag, "python", "-",
    ], input=smoke_script(), text=True, check=True, timeout=60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("wheel", "image"))
    parser.add_argument("artifact")
    args = parser.parse_args()
    if args.kind == "wheel":
        verify_wheel(Path(args.artifact))
    else:
        verify_image(args.artifact)
