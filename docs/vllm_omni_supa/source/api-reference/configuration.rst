配置参考
========

vllm-omni-supa 复用 vLLM-Omni 和 SUPA 依赖提供的配置对象。平台插件负责平台选择，
SUPA 设备策略和算子由 SUPA 平台依赖提供。

安装后可检查插件入口点：

.. code-block:: python

   from importlib.metadata import distribution
   for entry in distribution("vllm-omni-supa").entry_points:
       print(entry.group, entry.name, entry.value)

启动前设置设备：

.. code-block:: bash

   export SUPA_VISIBLE_DEVICES=0
