# Copyright (C) 2020-2026 Shanghai Biren Technology Co., Ltd.
"""Basic function guards for the vLLM-Omni-SUPA platform plugin."""

import pytest

# These guards exercise the real plugin, which needs the SUPA stack installed.
# Skip cleanly (instead of erroring) when it is not present.
pytest.importorskip("vllm_omni")
pytest.importorskip("vllm_supa")

import vllm_omni_supa  # noqa: E402
from vllm_omni_supa.platform import SupaOmniPlatform  # noqa: E402


@pytest.mark.sanity
@pytest.mark.regression
def test_register_omni_platform_path():
    """The platform plugin advertises the SupaOmniPlatform dotted path."""
    assert vllm_omni_supa.register_omni_platform() == "vllm_omni_supa.platform.SupaOmniPlatform"


@pytest.mark.sanity
@pytest.mark.regression
def test_platform_class_contract():
    """SupaOmniPlatform bridges the SUPA base and CUDA Omni platform."""
    from vllm_omni.platforms.cuda.platform import CudaOmniPlatform
    from vllm_supa.platform import SUPAPlatformBase

    assert issubclass(SupaOmniPlatform, SUPAPlatformBase)
    assert issubclass(SupaOmniPlatform, CudaOmniPlatform)
    assert SupaOmniPlatform.device_control_env_var == "SUPA_VISIBLE_DEVICES"
    assert SupaOmniPlatform.dist_backend == "bccl"


@pytest.mark.sanity
@pytest.mark.regression
def test_register_patch_applies():
    """register_patch installs the runtime patches without error."""
    vllm_omni_supa.register_patch()

    from vllm_omni_supa import patch

    assert patch._APPLIED is True
