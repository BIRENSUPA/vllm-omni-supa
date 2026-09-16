# Copyright (C) 2025-2026 Shanghai Biren Technology Co., Ltd.
import os
import subprocess
from datetime import datetime, timezone

from setuptools import find_packages, setup

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))


def get_build_metadata() -> str:
    """Return build metadata in commit-count.build-id.revision.timestamp format."""
    try:
        commit_count = subprocess.check_output(["git", "rev-list", "--count", "HEAD"], cwd=ROOT_DIR, text=True, stderr=subprocess.DEVNULL).strip()
        git_revision = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT_DIR, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        commit_count, git_revision = "0", "unknown"
    build_id = os.environ.get("BUILD_ID", "0")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{commit_count}.{build_id}.{git_revision}.{timestamp}"


def read_upstream_versions():
    versions = {}
    version_file = os.path.join(ROOT_DIR, "upstream_version.txt")
    with open(version_file, encoding="utf-8") as file:
        for line in file:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                versions[key] = value.strip()
    return versions


VERSIONS = read_upstream_versions()
VLLM_OMNI_SUPA_VERSION = f"{VERSIONS['VLLM_OMNI_VERSION']}+br2xx"


def get_requirements() -> list:
    """Get Python package dependencies from requirements.txt."""

    def _read_requirements(filename: str) -> list:
        with open(os.path.join(ROOT_DIR, filename), encoding="utf-8") as file:
            requirements = file.read().strip().splitlines()
        resolved_requirements = []
        for line in requirements:
            line = line.strip()
            if line.startswith("-r "):
                resolved_requirements += _read_requirements(line.split(maxsplit=1)[1])
            elif line and not line.startswith("--") and not line.startswith("#"):
                resolved_requirements.append(line)
        return resolved_requirements

    return _read_requirements("requirements.txt")


setup(
    name="vllm-omni-supa",
    version=VLLM_OMNI_SUPA_VERSION,
    description=f"Biren SUPA platform bridge for vLLM-Omni (build metadata: {get_build_metadata()})",
    python_requires=">=3.10",
    packages=find_packages(include=("vllm_omni_supa", "vllm_omni_supa.*")),
    install_requires=get_requirements(),
    entry_points={
        "vllm_omni.platform_plugins": [
            "biren_supa = vllm_omni_supa:register_omni_platform",
        ],
        "vllm.general_plugins": [
            "biren_omni_patch = vllm_omni_supa:register_patch",
        ],
    },
)
