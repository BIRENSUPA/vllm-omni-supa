# Copyright (C) 2020-2026 Shanghai Biren Technology Co., Ltd.
"""Wire Omni's standard FlashAttention backend to BR200 kernels."""

from __future__ import annotations

from vllm.logger import init_logger

# Keep the bridge logger under vLLM's configured logger hierarchy so INFO
# records use the same handler and format as the rest of the server.
logger = init_logger(f"vllm.{__name__}")
_PATCH_MARKER = "_vllm_omni_supa_br_flash_attention_patch"


def install_supa_flash_attention() -> bool:
    """Use the BR FlashAttention package for Omni ``FLASH_ATTN`` calls.

    Omni's CUDA import chain does not look for Biren's ``flashattn_infer``
    package and otherwise falls through to vLLM-SUPA's FA2 compatibility
    wrapper, whose varlen entry point is intentionally unimplemented. This
    only rebinds Omni's Python function references; no new Omni backend or
    torch operator is registered.
    """

    from vllm_omni.diffusion import envs
    from vllm_omni.diffusion.attention.backends.utils import fa

    if getattr(fa, _PATCH_MARKER, False):
        return False

    try:
        import flashattn_infer as flash_attention

        backend_name = "flashattn_infer"
    except ImportError:
        try:
            import suattention as flash_attention

            backend_name = "suattention"
        except ImportError as exc:
            logger.warning("No BR FlashAttention package is available: %s", exc)
            return False

    fa.flash_attn_func = flash_attention.flash_attn_func
    fa.flash_attn_varlen_func = flash_attention.flash_attn_varlen_func
    fa.HAS_FLASH_ATTN = True
    fa.is_flash_attn_installed.cache_clear()
    setattr(fa, _PATCH_MARKER, True)

    package_checker = getattr(envs, "PACKAGES_CHECKER", None)
    if package_checker is not None:
        package_checker.packages_info["has_flash_attn"] = True

    logger.info("vllm-omni-supa mapped Omni FLASH_ATTN to %s", backend_name)
    return True


__all__ = ["install_supa_flash_attention"]
