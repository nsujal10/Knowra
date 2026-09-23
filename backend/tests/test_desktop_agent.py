import http.client
import json
import threading
import time
import urllib.request
import pytest

from scripts.desktop_meeting_companion import (
    DesktopAgentController,
    make_agent_handler,
    http,
)


def test_desktop_agent_controller_lifecycle():
    controller = DesktopAgentController(host_name="Sujal Nage", server_base="http://127.0.0.1:8000")
    
    # Initial status
    status = controller.get_status()
    assert status["status"] == "READY"
    assert status["activeMeetingId"] is None
    assert status["hostName"] == "Sujal Nage"

    # Stop when idle
    assert controller.stop_capture() is False


def test_desktop_agent_http_server_endpoints():
    test_port = 9897
    controller = DesktopAgentController(host_name="Sujal Nage", server_base="http://127.0.0.1:8000")
    handler = make_agent_handler(controller)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", test_port), handler)

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.1)

    try:
        # 1. Test GET /status
        req = urllib.request.Request(f"http://127.0.0.1:{test_port}/status")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            assert resp.headers.get("Access-Control-Allow-Origin") == "*"
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "READY"
            assert data["hostName"] == "Sujal Nage"

        # 2. Test OPTIONS (CORS preflight)
        conn = http.client.HTTPConnection("127.0.0.1", test_port)
        conn.request("OPTIONS", "/start")
        opt_resp = conn.getresponse()
        assert opt_resp.status == 204
        assert opt_resp.headers.get("Access-Control-Allow-Origin") == "*"
        conn.close()

        # 3. Test POST /stop
        stop_req = urllib.request.Request(
            f"http://127.0.0.1:{test_port}/stop",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(stop_req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "STOPPED"

    finally:
        server.shutdown()
        server.server_close()
