# vLLM-Omni-SUPA

vLLM-Omni-SUPA 是面向壁仞 BR200 硬件的 [vLLM-Omni](https://github.com/vllm-project/vllm-omni) 平台插件，提供平台注册、运行时兼容补丁以及 SUPA 后端集成，支持在线服务和离线推理。

## 系统要求

- Ubuntu 22.04、Ubuntu 24.04 或兼容 Linux
- Python 3.10+
- BR2XX 硬件和 BIRENSUPA SDK
- 已安装匹配版本的 vLLM、vLLM-Omni、[vLLM-SUPA](https://github.com/BIRENSUPA/vllm-supa)、[TorchSUPA](https://github.com/BIRENSUPA/torch-supa)
- 使用 Docker 时需要 Docker 20.10.7+

版本统一定义在 [`upstream_version.txt`](upstream_version.txt)：

```bash
cat upstream_version.txt
```

```text
VLLM_OMNI_VERSION=0.27.0rc1
VLLM_VERSION=0.27.1
TORCH_VERSION=2.12.0
```

## 安装方式

### Docker 镜像

使用预装 vLLM-SUPA、TorchSUPA 及运行时依赖的镜像。(镜像发布情况以交付说明为准)

### Wheel 安装

在已安装 BIRENSUPA SDK 的环境中：

```bash
# 初始化 BIRENSUPA 软件栈
source /usr/local/birensupa/all/latest/scripts/brsw_set_env.sh
suda init
. "$HOME/.gstub/suda.sh"
suda load

# 安装 torch_supa。该操作会同步安装 Torch 等基础软件包，需手动选择版本。
python3 -m pip install flashattn_infer-*.whl suattention-*.whl deep_ep-*.whl \
  flash_mla-*.whl triton-*.whl tilelang*.whl torch_supa-*.whl

# 安装 vLLM 和 vLLM-Omni（依赖需与 upstream_version.txt 中的版本匹配）。
python3 -m pip install "vllm==<VLLM_VERSION>" --no-deps
python3 -m pip install "vllm-omni==<VLLM_OMNI_VERSION>" --no-deps

# 安装 vLLM-SUPA 依赖，需手动指定版本。
python3 -m pip install vllm_supa-*.whl

# 安装 vLLM-Omni-SUPA 及其依赖，需手动指定版本。
python3 -m pip install vllm_omni_supa-*.whl
```

### 源码安装

```bash
python3 -m pip install --no-deps -e . --no-build-isolation  # 开发环境
```

安装后插件会通过入口自动加载。启动 vLLM-Omni 时，日志中应出现 `OmniPlatform plugin biren_supa is activated`。


## 文档编译

### HTML

```bash
cd docs/vllm_omni_supa
make html  # HTML 输出目录：build/html/
```

### PDF

```bash
# PDF 编译依赖（Ubuntu/Debian）
sudo apt-get update
sudo apt-get install -y latexmk texlive-xetex texlive-lang-chinese

make latexpdf  # PDF 输出目录：build/latex/
```

更多内容请参阅 [vLLM-Omni 文档](https://vllm-omni.readthedocs.io/) 和 [docs](./docs/) 目录。

## 许可证

许可证信息请参阅仓库中的 [`LICENSE`](LICENSE) 文件。
