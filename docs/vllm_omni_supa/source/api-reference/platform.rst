SupaOmniPlatform
================

``SupaOmniPlatform`` 是 vllm-omni-supa 提供的平台实现，将 vLLM-Omni 的 CUDA-like
执行路径连接到壁仞 BR2XX/SUPA 设备栈。平台类位于
``vllm_omni_supa.platform``，通过 ``biren_supa`` 入口点自动发现。

平台属性
--------

.. list-table:: 平台属性
   :header-rows: 1
   :widths: 35 65

   * - 属性
     - 值
   * - 设备可见性变量
     - ``SUPA_VISIBLE_DEVICES``
   * - Dispatch key
     - ``PrivateUse1`` （由 SUPA 平台依赖提供）。
   * - 分布式后端
     - ``bccl``
   * - 平台类
     - ``vllm_omni_supa.platform.SupaOmniPlatform``

设备可见性
----------

可通过 ``SupaOmniPlatform.set_device_control_env_var`` 和
``unset_device_control_env_var`` 设置或清除 ``SUPA_VISIBLE_DEVICES``。通常直接在
启动进程前设置环境变量即可，例如 ``SUPA_VISIBLE_DEVICES=0,1``。
