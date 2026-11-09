"""Scene-count limits for storyboards and render jobs."""

import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from fastapi.testclient import TestClient

from app.api.main import app
from app.config import MAX_SCENES
from app.models import Prompt
from app.storyboard import storyboard

TWELVE_SENTENCES = " ".join(
    f"Milo {verb} in the garden." for verb in
    ["wakes up", "walks", "jumps", "waves", "dances", "runs", "spins", "sits", "looks around", "naps", "nods", "laughs"]
)


def scene(i):
    return {"narration": f"Scene {i}.", "action": "idle", "duration": 3}


class FakeOllama(BaseHTTPRequestHandler):
    scenes = 12
    last_request = None

    def do_POST(self):
        FakeOllama.last_request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        story = {"title": "Fake", "scenes": [scene(i) for i in range(FakeOllama.scenes)]}
        body = json.dumps({"message": {"content": json.dumps(story)}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class SceneLimitTests(unittest.TestCase):
    def test_limit_is_ten(self):
        self.assertEqual(MAX_SCENES, 10)

    def test_demo_makes_one_scene_per_sentence_up_to_the_limit(self):
        self.assertEqual(len(storyboard(Prompt(prompt=TWELVE_SENTENCES)).scenes), MAX_SCENES)
        five = "Milo wakes up. He walks. He jumps. He waves. He sleeps."
        self.assertEqual(len(storyboard(Prompt(prompt=five)).scenes), 5)

    def test_api_accepts_ten_scenes_and_rejects_eleven(self):
        with TestClient(app) as client:
            ok = client.post("/api/storyboard", json={"prompt": TWELVE_SENTENCES, "provider": "demo"})
            self.assertEqual(len(ok.json()["scenes"]), MAX_SCENES)
            too_many = client.post("/api/jobs", json={"scenes": [scene(i) for i in range(MAX_SCENES + 1)]})
            self.assertEqual(too_many.status_code, 422)

    def test_ollama_is_asked_for_up_to_ten_scenes_and_extra_are_trimmed(self):
        server = HTTPServer(("127.0.0.1", 0), FakeOllama)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        old = os.environ.get("OLLAMA_URL")
        os.environ["OLLAMA_URL"] = f"http://127.0.0.1:{server.server_port}"
        try:
            result = storyboard(Prompt(prompt=TWELVE_SENTENCES, provider="ollama"))
        finally:
            server.shutdown()
            server.server_close()
            if old is None:
                os.environ.pop("OLLAMA_URL")
            else:
                os.environ["OLLAMA_URL"] = old
        self.assertEqual(len(result.scenes), MAX_SCENES)
        system = FakeOllama.last_request["messages"][0]["content"]
        self.assertIn(f"up to {MAX_SCENES} scenes", system)
        self.assertIn(f'"maxItems": {MAX_SCENES}', system)


if __name__ == "__main__":
    unittest.main()
