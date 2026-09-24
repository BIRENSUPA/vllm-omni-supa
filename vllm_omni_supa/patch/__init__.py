# Copyright (C) 2020-2026 Shanghai Biren Technology Co., Ltd.
"""vLLM-Omni patches for the SUPA backend."""

_APPLIED = False


def apply_patches() -> None:
    global _APPLIED
    if _APPLIED:
        return
    from vllm_omni_supa.patch.diffusion.attention.backends.utils.fa import (
        install_supa_flash_attention,
    )
    from vllm_omni_supa.patch.diffusion.model_loader.diffusers_loader import (
        install_cpu_model_loader_patch,
    )
    from vllm_omni_supa.patch.diffusion.models.minimax_h3 import install_minimax_h3_patches

    install_supa_flash_attention()
    install_cpu_model_loader_patch()
    install_minimax_h3_patches()
    _APPLIED = True
