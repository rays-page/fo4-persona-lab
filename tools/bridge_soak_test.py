from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import os

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def pick_free_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((host, 0))
        probe.listen(1)
        return probe.getsockname()[1]


def http_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    timeout: float = 10.0,
) -> tuple[int, dict]:
    data: bytes | None = None
    headers: dict[str, str] = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
        return response.status, body


def wait_for_server(base_url: str, timeout_seconds: float) -> dict:
    deadline = time.time() + timeout_seconds
    last_error: str | None = None
    while time.time() < deadline:
        try:
            health_status, health = http_json(f"{base_url}/api/health")
            if health_status != 200 or health.get("status") != "ok":
                last_error = f"Health check failed: {health_status} {health}"
                time.sleep(0.1)
                continue

            status, body = http_json(f"{base_url}/api/personas")
            if status == 200 and isinstance(body.get("personas"), list):
                return body
            last_error = f"Unexpected personas status/body: {status} {body}"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
        time.sleep(0.1)
    raise RuntimeError(f"Server did not become ready in time. Last error: {last_error}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a short multithreaded /api/bridge/chat soak test."
    )
    parser.add_argument(
        "--persona-id",
        default="steve-jobs",
        help="Persona id to use (falls back to first available persona).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Number of parallel worker threads (default: 8).",
    )
    parser.add_argument(
        "--requests-per-worker",
        type=int,
        default=12,
        help="Requests per worker thread (default: 12).",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=10.0,
        help="Per-request timeout in seconds (default: 10).",
    )
    parser.add_argument(
        "--startup-timeout",
        type=float,
        default=20.0,
        help="Server startup timeout in seconds (default: 20).",
    )
    return parser.parse_args()


def validate_positive(name: str, value: int) -> None:
    if value <= 0:
        raise SystemExit(f"{name} must be > 0.")


def main() -> None:
    args = parse_args()
    validate_positive("workers", args.workers)
    validate_positive("requests-per-worker", args.requests_per_worker)
    if args.request_timeout <= 0 or args.startup_timeout <= 0:
        raise SystemExit("Timeout values must be > 0.")

    host = "127.0.0.1"
    port = pick_free_port(host)
    base_url = f"http://{host}:{port}"
    total_requests = args.workers * args.requests_per_worker

    env = os.environ.copy()
    env["FO4_PERSONA_HOST"] = host
    env["FO4_PERSONA_PORT"] = str(port)
    env["FO4_PERSONA_BACKEND"] = "rules"
    env["FO4_PERSONA_TTS_BACKEND"] = "none"

    process = subprocess.Popen(
        [sys.executable, "-m", "fo4_persona_lab.server"],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    started = time.perf_counter()
    try:
        personas_payload = wait_for_server(base_url, args.startup_timeout)
        personas = personas_payload["personas"]
        if not personas:
            raise SystemExit("Soak failed: no personas loaded.")

        requested_id = args.persona_id
        persona_ids = {item["persona_id"] for item in personas}
        persona_id = requested_id if requested_id in persona_ids else personas[0]["persona_id"]
        print(f"Using persona: {persona_id}")

        _, session_payload = http_json(
            f"{base_url}/api/sessions",
            method="POST",
            payload={"persona_id": persona_id},
            timeout=args.request_timeout,
        )
        session_id = session_payload["session_id"]
        print(f"Session: {session_id}")

        expected_messages: list[str] = []
        for worker_id in range(args.workers):
            for request_index in range(args.requests_per_worker):
                expected_messages.append(
                    f"soak worker={worker_id} request={request_index} total={total_requests}"
                )

        def run_one(job_index: int) -> tuple[int, str]:
            message = expected_messages[job_index]
            payload = {
                "request_id": job_index + 1,
                "persona_id": persona_id,
                "session_id": session_id,
                "message": message,
                "player_name": "Load Tester",
                "location": "Bridge Soak Lab",
                "speak": False,
            }
            status, body = http_json(
                f"{base_url}/api/bridge/chat",
                method="POST",
                payload=payload,
                timeout=args.request_timeout,
            )
            if status != 200:
                raise RuntimeError(f"HTTP {status}: {body}")
            if not body.get("accepted", False):
                raise RuntimeError(f"Request not accepted: {body}")
            if body.get("error"):
                raise RuntimeError(f"Bridge error returned: {body['error']}")
            if body.get("session_id") != session_id:
                raise RuntimeError(
                    f"Session mismatch: expected {session_id}, got {body.get('session_id')}"
                )
            reply = str(body.get("reply", "")).strip()
            if not reply:
                raise RuntimeError("Empty reply returned.")
            return job_index, reply

        failures: list[str] = []
        replies = 0
        soak_start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(run_one, job_index) for job_index in range(total_requests)]
            for future in as_completed(futures):
                try:
                    _job_index, _reply = future.result()
                    replies += 1
                except Exception as exc:  # noqa: BLE001
                    failures.append(str(exc))

        soak_seconds = time.perf_counter() - soak_start
        if failures:
            preview = "\n".join(f"- {item}" for item in failures[:10])
            extra_count = len(failures) - min(len(failures), 10)
            if extra_count > 0:
                preview += f"\n- ... {extra_count} more failures"
            raise SystemExit(f"Soak failed with {len(failures)} request errors:\n{preview}")

        encoded_session_id = urllib.parse.quote(session_id, safe="")
        _, session_state = http_json(
            f"{base_url}/api/sessions/{encoded_session_id}",
            timeout=args.request_timeout,
        )
        session = session_state["session"]
        turns = session.get("turns", [])
        user_turns = [turn.get("text", "") for turn in turns if turn.get("role") == "user"]
        assistant_turns = [turn.get("text", "") for turn in turns if turn.get("role") == "assistant"]
        expected_turn_count = total_requests * 2

        problems: list[str] = []
        if len(turns) != expected_turn_count:
            problems.append(
                f"Expected {expected_turn_count} turns, found {len(turns)}."
            )
        if len(assistant_turns) != total_requests:
            problems.append(
                f"Expected {total_requests} assistant turns, found {len(assistant_turns)}."
            )
        if any(not text.strip() for text in assistant_turns):
            problems.append("Detected one or more empty assistant turns.")

        expected_counter = Counter(expected_messages)
        actual_counter = Counter(user_turns)
        missing = expected_counter - actual_counter
        extra = actual_counter - expected_counter
        if missing:
            sample = next(iter(missing.elements()))
            problems.append(f"Missing expected user turn(s), sample: {sample}")
        if extra:
            sample = next(iter(extra.elements()))
            problems.append(f"Unexpected extra user turn(s), sample: {sample}")

        session_path = PROJECT_ROOT / "data" / "sessions" / f"{session_id}.json"
        if not session_path.exists():
            problems.append(f"Session file missing on disk: {session_path}")
        else:
            try:
                disk_session = json.loads(session_path.read_text(encoding="utf-8"))
                if disk_session.get("session_id") != session_id:
                    problems.append("Session file JSON parsed but session_id mismatched.")
            except json.JSONDecodeError as exc:
                problems.append(f"Session file is invalid JSON: {exc}")

        if problems:
            raise SystemExit("Soak failed due to session integrity issues:\n- " + "\n- ".join(problems))

        total_elapsed = time.perf_counter() - started
        rps = total_requests / soak_seconds if soak_seconds > 0 else 0.0
        print(
            "Soak passed. "
            f"requests={total_requests}, workers={args.workers}, "
            f"duration={soak_seconds:.2f}s, throughput={rps:.2f} req/s, replies={replies}, "
            f"total_elapsed={total_elapsed:.2f}s"
        )
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
