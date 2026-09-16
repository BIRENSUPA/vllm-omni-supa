安装
====

基础要求
--------

* Ubuntu 22.04、Ubuntu 24.04 或兼容的 Linux 环境。
* Python 3.10 及以上。
* BR2XX 硬件、SUPA SDK。
* Docker >= 20.10.7（使用 Docker 镜像安装时）。

版本依赖
--------

当前仓库插件及其运行时依赖版本如下：

.. list-table:: 依赖版本
   :header-rows: 1
   :widths: 40 60

   * - 依赖
     - 版本
   * - vLLM-Omni / vLLM-Omni SUPA
     - 0.27.0rc1
   * - vLLM / vLLM SUPA
     - 0.27.1
   * - PyTorch / TorchSUPA
     - 2.12.0

环境准备
--------

安装 vLLM-Omni-SUPA 有以下三种方式，请根据部署和开发需求选择。

* **方式一：官方 Docker 镜像**

  使用已预装 vLLM-Omni、vLLM-SUPA、TorchSUPA 和运行时依赖的官方镜像。

  .. attention::

     当前暂未发镜像，可关注官方发布动态。

* **方式二：wheel 包安装**

  适用于已有 BIRENSUPA 环境的用户。先安装 SDK 并设置环境：

  .. code-block:: shell

     sudo bash birensupa-sdk-xxxx.run
     source /usr/local/birensupa/all/latest/scripts/brsw_set_env.sh
     suda init
     . "$HOME/.gstub/suda.sh"
     suda load

  安装匹配的 upstream vLLM、vLLM-Omni 及 SUPA 依赖 wheel 后，安装本插件：

  .. code-block:: shell

     python3 -m pip install --no-deps vllm_omni_supa-*.whl

  .. code-block:: shell

     python3 -m pip install \
         flashattn_infer-*.whl \
         suattention-*.whl \
         deep_ep-*.whl \
         flash_mla-*.whl \
         triton-*.whl \
         tilelang-*.whl \
         torch_supa-*.whl \
         vllm_supa-*.whl

  .. attention::

     当前暂未发布配套算子及相关软件包，可关注官方发布动态。

* **方式三：源码构建**

  适用于开发或需要修改插件代码的场景：

  .. code-block:: shell

     python3 -m pip install -e . --no-build-isolation
