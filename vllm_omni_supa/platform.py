# Copyright (C) 2025-2026 Shanghai Biren Technology Co., Ltd.
"""Biren SUPA implementation of the vLLM-Omni platform contract.

The SUPA backend intentionally reuses vLLM-Omni's CUDA-like worker and
diffusion implementation.  Device discovery, memory, kernel registration,
and configuration policy are delegated to the already-installed vllm-supa
platform so the two packages keep one source of truth for BR200 behavior.
"""

from __future__ import annotations

import os

from vllm_omni.platforms.cuda.platform import CudaOmniPlatform
from vllm_supa.platform import SUPAPlatformBase


class SupaOmniPlatform(SUPAPlatformBase, CudaOmniPlatform):
    """Run vLLM-Omni CUDA-like stages on the SUPA PrivateUse1 backend."""

    device_control_env_var = "SUPA_VISIBLE_DEVICES"
    dist_backend = "bccl"

    @classmethod
    def set_device_control_env_var(cls, devices: str | int | None) -> None:
        os.environ[cls.device_control_env_var] = "" if devices is None else str(devices)

    @classmethod
    def unset_device_control_env_var(cls) -> None:
        os.environ.pop(cls.device_control_env_var, None)


__all__ = ["SupaOmniPlatform"]
