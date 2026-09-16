# Copyright (C) 2025-2026 Shanghai Biren Technology Co., Ltd.
#!/usr/bin/env python3
"""Start a local MiniMax-H3 server, send one T2VA prompt, and save the MP4."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_MODEL = "/ceph/teamFPA/Pt_Framework/users/E01833/models/MiniMax-H3-CModel"
DEFAULT_PROMPT = "A quiet night beside a lake, with a small fire crackling and wind in the trees."
# The Omni CLI rejects zero/negative lifecycle timeouts. This large positive
# value is effectively unlimited for a model smoke test, without relying on
# overflow-prone infinity values in integer CLI/config fields.
UNLIMITED_TIMEOUT_SECONDS = 2_147_483_647

# Set these before vLLM starts so the server uses the SUPA bridge in eager mode.
for _key, _value in {
    "SUPA_LAUNCH_BLOCKING": "1",
    "VLLM_ENABLE_V1_MULTIPROCESSING": "0",
    "VLLM_SUPA_SKIP_PROFILE_RUN": "1",
    "VLLM_SUPA_LOAD_MODEL_ON_CPU": "1",
    "VLLM_WORKER_MULTIPROC_METHOD": "spawn",
    # Disable Omni's full-payload input safety timeout (<= 0 disables it).
    "VLLM_OMNI_INPUT_WAIT_TIMEOUT_S": "0",
    # Keep distributed diffusion waves from expiring if enabled by a deploy config.
    "VLLM_OMNI_DLO_DP_WAVE_TIMEOUT": str(UNLIMITED_TIMEOUT_SECONDS),
    # H3 on cmodel can take much longer than Omni's default request limit.
    "VLLM_OMNI_VIDEO_SYNC_TIMEOUT": str(UNLIMITED_TIMEOUT_SECONDS),
}.items():
    os.environ.setdefault(_key, _value)
# Do not inherit a shorter request timeout from the caller: this smoke test is
# specifically intended to wait for the cmodel to finish.
os.environ["VLLM_OMNI_VIDEO_SYNC_TIMEOUT"] = str(UNLIMITED_TIMEOUT_SECONDS)
os.environ["VLLM_OMNI_INPUT_WAIT_TIMEOUT_S"] = "0"
os.environ["VLLM_OMNI_DLO_DP_WAVE_TIMEOUT"] = str(UNLIMITED_TIMEOUT_SECONDS)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL, help="H3 root or FL2VA directory")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8091)
    parser.add_argument("--gpu-ids", help="Set SUPA_VISIBLE_DEVICES, for example 0")
    parser.add_argument("--num-gpus", type=int, default=1)
    parser.add_argument("--steps", type=int, default=2)
    parser.add_argument("--duration", type=float, default=4.0)
    parser.add_argument("--width", type=int, default=64)
    parser.add_argument("--height", type=int, default=64)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--attention-backend",
        "--diffusion-attention-backend",
        dest="attention_backend",
        default="FLASH_ATTN",
        help="Omni diffusion attention backend (default: FLASH_ATTN)",
    )
    parser.add_argument("--output", type=Path, default=Path("minimax_h3_supa.mp4"))
    return parser.parse_args()


def fl2va_path(model: str) -> Path:
    path = Path(model).expanduser().resolve()
    if (path / "FL2VA").is_dir():
        return path / "FL2VA"
    if path.name == "FL2VA" and path.is_dir():
        return path
    if (path / "model_index.json").is_file():
        return path
    raise FileNotFoundError(f"cannot find FL2VA under {path}")


def server_command(args: argparse.Namespace, model: Path) -> list[str]:
    executable = "vllm"
    return [
        executable,
        "serve",
        str(model),
        "--omni",
        "--trust-remote-code",
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--num-gpus",
        str(args.num_gpus),
        "--enable-cpu-offload",
        "--enforce-eager",
        "--no-enable-prefix-caching",
        "--no-enable-chunked-prefill",
        "--stage-init-timeout",
        str(UNLIMITED_TIMEOUT_SECONDS),
        "--init-timeout",
        str(UNLIMITED_TIMEOUT_SECONDS),
        "--batch-timeout",
        str(UNLIMITED_TIMEOUT_SECONDS),
        "--omni-heartbeat-timeout",
        str(UNLIMITED_TIMEOUT_SECONDS),
        "--diffusion-attention-backend",
        args.attention_backend.upper(),
        "--enable-diffusion-pipeline-profiler",
    ]


def wait_for_server(process: subprocess.Popen[bytes], url: str) -> None:
    """Wait without imposing a timeout; model loading may be slow on cmodel."""

    health_url = url.rsplit("/v1/", 1)[0] + "/health"
    while True:
        if process.poll() is not None:
            raise RuntimeError(f"vllm serve exited during startup with code {process.returncode}")
        try:
            with urllib.request.urlopen(health_url) as response:
                if response.status < 400:
                    return
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(2)


def send_prompt(url: str, args: argparse.Namespace) -> bytes:
    import requests

    response = requests.post(
        url,
        data={
            "prompt": args.prompt,
            "width": str(args.width),
            "height": str(args.height),
            "fps": "24",
            "num_inference_steps": str(args.steps),
            "flow_shift": "12",
            "aspect_ratio": "16:9",
            "seed": str(args.seed),
            "extra_params": json.dumps(
                {
                    "task": "t2va",
                    "duration": args.duration,
                    "aspect_ratio": "16:9",
                    "audio_flow_shift": 3.0,
                }
            ),
        },
    )
    response.raise_for_status()
    return response.content


def stop_server(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.terminate()
        process.wait()


def main() -> int:
    args = parse_args()
    if args.gpu_ids:
        os.environ["SUPA_VISIBLE_DEVICES"] = args.gpu_ids
    model = fl2va_path(args.model)
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    url = f"http://{args.host}:{args.port}/v1/videos/sync"
    command = server_command(args, model)

    print("[H3] starting:", " ".join(command), flush=True)
    process = subprocess.Popen(command, env=os.environ.copy())
    try:
        wait_for_server(process, url)
        print("[H3] server ready; sending prompt", flush=True)
        output.write_bytes(send_prompt(url, args))
        print(f"[H3] saved: {output}", flush=True)
        return 0
    except Exception as exc:  # noqa: BLE001 - print the server/request failure
        print(f"[H3] failed: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 1
    finally:
        stop_server(process)


if __name__ == "__main__":
    raise SystemExit(main())
