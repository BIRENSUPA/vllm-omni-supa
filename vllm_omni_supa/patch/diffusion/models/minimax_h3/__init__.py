# Copyright (C) 2025-2026 Shanghai Biren Technology Co., Ltd.
"""SUPA patches for vllm_omni.diffusion.models.minimax_h3."""

from __future__ import annotations

import torch
from vllm_omni.diffusion.models.minimax_h3 import packed_sequence, pipeline_minimax_h3
from vllm_supa.patch_to_with_log import patch_to_with_log


def _fp32(packed):
    ids = packed.get("img_position_ids")
    if ids is not None and ids.dtype == torch.float64:
        packed = dict(packed)
        packed["img_position_ids"] = ids.to(torch.float32)
    return packed


@patch_to_with_log(packed_sequence)
def minimax_h3_packed_sequence(*args, **kwargs):
    return _fp32(packed_sequence._orig_minimax_h3_packed_sequence(*args, **kwargs))


@patch_to_with_log(packed_sequence)
def minimax_h3_packed_sequence_ref2va_blocks(*args, **kwargs):
    return _fp32(packed_sequence._orig_minimax_h3_packed_sequence_ref2va_blocks(*args, **kwargs))


# The pipeline module keeps its own imported references.
@patch_to_with_log(pipeline_minimax_h3, nm="minimax_h3_packed_sequence")
def pipeline_packed_sequence(*args, **kwargs):
    return _fp32(pipeline_minimax_h3._orig_minimax_h3_packed_sequence(*args, **kwargs))


@patch_to_with_log(pipeline_minimax_h3, nm="minimax_h3_packed_sequence_ref2va_blocks")
def pipeline_packed_sequence_ref2va_blocks(*args, **kwargs):
    return _fp32(
        pipeline_minimax_h3._orig_minimax_h3_packed_sequence_ref2va_blocks(*args, **kwargs)
    )


def install_minimax_h3_patches() -> None:
    """Compatibility entry point; decorators apply patches at import time."""


__all__ = ["install_minimax_h3_patches"]
