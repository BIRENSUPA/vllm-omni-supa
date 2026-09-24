# Copyright (C) 2020-2026 Shanghai Biren Technology Co., Ltd.
"""SUPA CPU-first patches for vLLM-Omni diffusion loading."""

from __future__ import annotations

from functools import wraps
from typing import Any

import torch
from vllm.logger import init_logger
from vllm_omni.diffusion.model_loader.diffusers_loader import DiffusersPipelineLoader
from vllm_supa import envs
from vllm_supa.patch_to_with_log import patch_to_with_log

logger = init_logger(__name__)
_MARKER = "_vllm_omni_supa_cpu_patch"


def _offload(config: Any) -> bool:
    return any(
        getattr(config, name, False)
        for name in (
            "enable_cpu_offload",
            "enable_layerwise_offload",
            "enable_distributed_layerwise_offload",
        )
    )


@patch_to_with_log(DiffusersPipelineLoader)
def load_model(self, load_device, load_format="default", custom_pipeline_name=None, device=None):
    target = torch.device(device) if device is not None else None
    cpu_first = (
        bool(envs.VLLM_SUPA_LOAD_MODEL_ON_CPU) and target is not None and target.type != "cpu"
    )
    if cpu_first and torch.device(load_device).type != "cpu":
        load_device = "cpu"
        logger.info("Loading diffusion model on CPU before moving it to %s", target)
    model = self._orig_load_model(self, load_device, load_format, custom_pipeline_name, device)
    if cpu_first and not _offload(self.od_config):
        model = model.to(target)
    return model


def install_cpu_model_loader_patch() -> None:
    """Patch MiniMax-H3 VAE constructors for CPU-first loading."""
    from vllm_omni.diffusion.models.minimax_h3 import vae

    for name in ("MiniMaxH3VideoVAE", "MiniMaxH3AudioVAE"):
        cls = getattr(vae, name, None)
        if cls is None or getattr(cls.__init__, _MARKER, False):
            continue
        original = cls.__init__

        @wraps(original)
        def init(self, *args, _original=original, **kwargs):
            if (
                envs.VLLM_SUPA_LOAD_MODEL_ON_CPU
                and torch.device(kwargs.get("load_device", "cpu")).type != "cpu"
            ):
                kwargs["load_device"] = torch.device("cpu")
            return _original(self, *args, **kwargs)

        setattr(init, _MARKER, True)
        cls.__init__ = init


__all__ = ["install_cpu_model_loader_patch"]
