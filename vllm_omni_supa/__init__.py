# Copyright (C) 2020-2026 Shanghai Biren Technology Co., Ltd.
"""vLLM-Omni platform plugin for Biren SUPA."""

from __future__ import annotations


def register_omni_platform() -> str:
    # Platform discovery must not import diffusion modules: they resolve the
    # platform again and can cache CUDA during this plugin's partial import.
    # Patches are loaded separately through the general plugin entry point.
    return "vllm_omni_supa.platform.SupaOmniPlatform"


def register_patch() -> None:
    """Load SUPA patches through vLLM's general plugin mechanism."""
    from vllm_omni_supa.patch import apply_patches

    apply_patches()


__all__ = ["register_omni_platform", "register_patch"]

# Omni initializes its rotary-embedding patches at package import and resolves
# the platform in that process. Initialize it before an explicit import of our
# platform submodule, so resolution never sees a half-defined platform class.
# The registration callbacks above must already exist for plugin discovery.
import vllm_omni  # noqa: E402,F401
