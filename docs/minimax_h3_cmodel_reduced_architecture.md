# MiniMax-H3 CModel 减层架构与运行验证报告

## 1. 结论

### 1.1 MiniMax-H3模型构成

|组件|存储大小|作用|
|:---:|:---:|:---:|
|Qwen3-VL 条件器|62.13 GiB|解读文本和视觉上下文|
|H3-Omni Transformer|61.73 GiB|联合音视频去噪|
|Visual VAE|9.70 GiB|编码和解码视频隐空间|
|Audio VAE|0.56 GiB|编码和解码立体声音频隐空间|
|合计|134.13 GiB|仅权重文件，不含运行时开销|

其中Qwen3-VL使用的是32B模型，DiT部分使用的是33.1B的稠密模型，其中约 13B 在 AdaLN 分支中。

## 1.2 cmodel模型裁剪策略

当前 `MiniMax-H3-CModel` 是面向 BR200 cmodel 功能通路验证的真实权重裁剪模型。模型保留了 MiniMax-H3 的 `MiniMaxH3Pipeline` 顶层结构、FL2VA 分区、Qwen3-VL 文本编码器、联合音视频 DiT、Video VAE、Audio VAE、tokenizer 和 processor，没有改写模型类型或张量命名空间。

本次裁剪将四个主要权重组件从约 **134.13 GiB** 缩减到约 **5.97 GiB**，权重字节数减少 **95.55%**。2026-09-07 至 2026-09-08 的 BR200 cmodel 实测已经成功完成一条 `64x64 / 4 秒 / 2 sigma 点` 的 T2VA 请求，生成了包含 H.264 视频和 AAC 双声道音频的 MP4 文件。

模型裁剪结论为：
> MiniMax-H3 的 T2VA 代表执行路径已经在 BR200 cmodel 上端到端跑通，覆盖 SUPA 平台插件、Qwen3-VL 文本编码、联合音视频 DiT、Video VAE 解码、Audio VAE 解码以及 MP4 封装。该结论属于功能通路验证，不属于原始全层模型的精度、画质或性能验收。

## 2. 路径约定与证据

本文使用以下路径变量，避免在后续命令中重复依赖具体部署位置：

```bash
export REPO_ROOT="<vllm-omni-supa checkout>"
export MODEL_ROOT="<MiniMax-H3-CModel checkpoint>"
export SOURCE_MODEL_ROOT="<original MiniMax-H3 checkpoint>"
```

当前证据文件：

- 模型裁剪清单：`${MODEL_ROOT}/crop_manifest.json`
- 当前运行脚本：`${REPO_ROOT}/scripts/check_minimax_h3_supa.py`
- 成功运行日志：`${REPO_ROOT}/logs/test_server.log`
- 成功输出文件：`${REPO_ROOT}/minimax_h3_supa.mp4`
- 可复现裁剪工具：`${REPO_ROOT}/../run_training_job/prepare_minimax_h3_cmodel.py`
- 原 Audio VAE 备份：`${MODEL_ROOT}/.crop-backup-audio-vae-20260907`

证据哈希：

| 文件 | SHA-256 |
| --- | --- |
| `logs/test_server.log` | `be31434b2fdef6934845a82a727f30ea962b9b5fa26236321b9e53123ea247f2` |
| `minimax_h3_supa.mp4` | `fe2b1f5c333cdb323cb30e99e708f8c83643d648400163e6aee6e9faa15dc844` |

## 3. 当前端到端架构

```text
文本 Prompt
  |
  v
Qwen2TokenizerFast / Qwen3VLProcessor
  |
  v
Qwen3-VL Text Encoder
  - Text Decoder Layer: 1 层
  - Vision Block: 1 层（T2VA 纯文本请求不执行）
  |
  v
MiniMax-H3 Token Refiner: 1 层
  |
  v
MiniMax-H3 Joint Audio-Video DiT: 1 层
  |                         |
  | video latent            | audio latent
  v                         v
Video VAE                Audio VAE / BigVGAN
  - 3D CNN encoder          - DAC encoder（T2VA 不执行）
    （T2VA 不执行）          - 7 级 BigVGAN decoder
  - ViT3D decoder 1 层      - 每级 3 个 kernel 分支
  |                         - 每个 AMP block 1 个 dilation 残差对
  v                         v
107 帧 RGB 视频           32 kHz 双声道 PCM
  |                         |
  +-----------+-------------+
              v
       H.264 + AAC MP4
```

顶层组件保持如下：

| 组件名 | 类或类型 | 当前用途 |
| --- | --- | --- |
| Pipeline | `MiniMaxH3Pipeline` | 保留原始联合音视频生成 wrapper |
| Partition | `FL2VA` | 支持 `t2va` 和 `fl2va` |
| Text encoder | `Qwen3VLForConditionalGeneration` 配置 | 生成文本条件向量 |
| Transformer | `MiniMaxH3DiTModel` | 对视频和音频 latent 联合去噪 |
| Video VAE | `MiniMaxH3VideoVAE` / `AutoencoderKLLegacy` | 视频编码和解码 |
| Audio VAE | `MiniMaxH3AudioVAE` / DAC + BigVGAN | 音频编码和波形解码 |

## 4. 减层方案总览

| 组件 | 原始结构 | 当前结构 | 裁剪策略 |
| --- | ---: | ---: | --- |
| Qwen3-VL text decoder | 64 层 | 1 层，保留 layer 0 | 同构重复层保留一个代表层 |
| Qwen3-VL vision encoder | 27 层 | 1 层，保留 block 0 | 同构重复层保留一个代表层 |
| Vision deep-stack merger | 索引 `[8,16,24]` | 空列表 | 删除依赖已裁掉中间层的 deep-stack 路径 |
| MiniMax-H3 DiT | 50 层 | 1 层，保留 block 0 | 联合音视频 DiT 代表层 |
| Token refiner | 2 层 | 1 层，保留 block 0 | 文本条件细化代表层 |
| Video VAE 3D CNN encoder | 6 个 level，每级 2 个 ResBlock | 不变 | 保留视频输入编码结构；T2VA 不执行 |
| Video VAE ViT3D decoder | 36 层 | 1 层，保留 block 0 | 保留 VAE attention、FFN、norm 和输出投影路径 |
| Audio VAE encoder | 5 个下采样 block + attention projection | 不变 | 保留参考音频编码结构；T2VA 不执行 |
| Audio VAE upsample stages | 7 级 | 7 级 | 必须保留，维持 40 Hz latent 到 32 kHz 波形的 800 倍上采样 |
| Audio VAE kernel branches | 每级 kernel `3/7/11` | 不变 | 保留三类卷积核执行路径 |
| 每个 Audio AMP block 的 dilation pairs | `[1,3,5]`，3 对 | `[1]`，1 对 | 删除重复 dilation 3 和 5，保留 dilation 1 |
| Audio VAE residual convs | 126 个 | 42 个 | `7 stages x 3 branches x 1 pair x 2 conv` |

所有保留下来的层和参数均来自原 checkpoint 的真实权重，没有使用 dummy 权重或随机初始化。

## 5. 权重规模变化

下表统计 safetensors 中的 tensor data bytes，不包含 tokenizer、配置文件、Python remote code 和 safetensors header：

| 组件 | 原始 tensor 数 | 当前 tensor 数 | 原始权重 | 当前权重 | 字节缩减 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Transformer | 535 | 37 | 61.73 GiB | 2.09 GiB | 96.61% |
| Text encoder | 1058 | 33 | 62.13 GiB | 2.48 GiB | 96.01% |
| Video VAE | 560 | 140 | 9.70 GiB | 0.95 GiB | 90.25% |
| Audio VAE | 1087 | 499 | 0.56 GiB | 0.45 GiB | 19.43% |
| **合计** | **3240** | **709** | **134.13 GiB** | **5.97 GiB** | **95.55%** |

当前权重文件及哈希：

| 组件 | 文件大小 | SHA-256 |
| --- | ---: | --- |
| Transformer | 2,243,668,304 bytes | `b09a28db70d0e02695a7289e550724b267b0f87d43d5e4e3527bad9b187dc52b` |
| Text encoder | 2,660,031,232 bytes | `0dd9de21a6b83a3f14bc49813114a07516d79736809ce7fc98b1b058b5a582db` |
| Video VAE | 1,015,383,832 bytes | `ff9d92cfa1040afb81e0e0ec73711a23ab50478f2eedb6e27539b40d6e479f39` |
| Audio VAE | 487,724,972 bytes | `fd62df1594abdfb91473becff5ee32c52d78654408a7259d69b034b8c784d4db` |

## 6. 各组件当前配置

### 6.1 Qwen3-VL text encoder

文本分支保留完整 embedding、RoPE 和一个 decoder layer：

| 参数 | 当前值 |
| --- | ---: |
| Decoder layers | 1 |
| Hidden size | 5120 |
| FFN intermediate size | 25600 |
| Attention heads | 64 |
| KV heads | 8 |
| Head dimension | 128 |
| Vocabulary size | 151936 |
| Dtype | BF16 |

Vision 分支仍位于同一个 Qwen3-VL wrapper 中：

| 参数 | 当前值 |
| --- | ---: |
| Vision blocks | 1 |
| Hidden size | 1152 |
| FFN intermediate size | 4304 |
| Attention heads | 16 |
| Patch size | 16 |
| Temporal patch size | 2 |
| Deep-stack indexes | `[]` |

运行日志中的 `50 retained decoder layers` 是运行时代码使用固定选层上限打印的文本，不是当前 checkpoint 的真实层数。当前 `config.json`、权重键和严格加载结果均为 1 层。

### 6.2 联合音视频 DiT

| 参数 | 当前值 |
| --- | ---: |
| DiT blocks | 1 |
| Token refiner blocks | 1 |
| Hidden size | 5376 |
| FFN hidden size | 14336 |
| Attention heads | 56 |
| Attention head dimension | 128 |
| Text condition dimension | 5120 |
| Video latent channels | 24 |
| Audio latent channels | 32 |
| Video latent patch | `[1,2,2]` |

DiT 仍走 MiniMax-H3 的 packed audio/video token 路径。当前运行指定 `FLASH_ATTN`，由 `vllm-omni-supa` 映射到 BR200 `flashattn_infer`。

### 6.3 Video VAE

Video VAE 保持 `AutoencoderKLLegacy` 顶层结构：3D CNN encoder + ViT3D decoder。

Encoder 没有减层：

| 参数 | 当前值 |
| --- | --- |
| Base channels | 128 |
| Channel multipliers | `[1,2,2,4,4,8]` |
| ResBlocks per level | 2 |
| Spatial downsample schedule | `[2,2,2,2,1,1]` |
| Temporal downsample schedule | `[1,2,2,1,1,1]` |
| Spatial compression ratio | 16 |
| Temporal compression ratio | 4 |
| Latent channels | 24 |

Decoder 保留一个完整 ViT block：

| 参数 | 当前值 |
| --- | ---: |
| ViT blocks | 1（原始 36） |
| Heads | 32 |
| Head dimension | 64 |
| Hidden dimension | 2048 |
| FFN activation | SiLU gated |
| Norm | RMSNorm |
| Tiling | 开启 |
| Tile size / minimum overlap | 256 / 64 |
| Temporal clip length / token drop | 17 / 3 |

对于本次 64x64、107 帧输出，Video VAE 接收 `[1,24,32,4,4]` latent。空间尺寸小于单个 256x256 tile，因此没有空间拆 tile；时间维被组织为 6 次重叠 decode，最终拼接为 107 帧。

### 6.4 Audio VAE

Audio VAE 保留 DAC encoder、attention projection、latent projection 和 BigVGAN decoder。T2VA 只执行 decoder；encoder 用于包含参考音频的任务。

| 参数 | 当前值 |
| --- | --- |
| Sample rate | 32000 Hz |
| Latent channels | 32 |
| Internal latent dimension | 2048 |
| Decoder initial channels | 1024 |
| Upsample rates | `[5,5,2,2,2,2,2]` |
| Total upsample ratio | 800 |
| Stage output channels | `[512,256,128,64,32,16,8]` |
| Kernel branches per stage | `3/7/11` |
| Retained dilation per branch | `[1]` |
| AMP blocks | 21 |
| Residual Conv1d operations | 42 |

当前 4 秒请求按 MiniMax-H3 的时间对齐规则变为 107 帧，即 `107 / 24 = 4.4583` 秒。Audio latent 时间长度为 `round(4.4583 x 40) = 178`，双声道 latent 形状为 `[2,32,178]`。经过 800 倍上采样后得到每声道 142400 个采样点，对应 4.45 秒音频。

## 7. 本次 cmodel 请求的数据规模

| 项目 | 数值 |
| --- | --- |
| 入口 | `vllm serve --omni`，API server 模式 |
| Device count | 1 |
| Execution | eager |
| CPU offload | 开启 |
| Attention backend | `FLASH_ATTN -> flashattn_infer` |
| Prompt tokens | 19 |
| Requested canvas | 64x64 |
| Requested duration | 4 秒 |
| Aligned video output | 107 帧，24 FPS，4.458 秒 |
| Video latent | `[1,24,32,4,4]` |
| Packed video rows | `[128,96]` |
| Audio latent | `[2,32,178]` |
| Packed audio rows | `[356,32]` |
| Sampling setting | 2 sigma 点，对应 1 次 denoise transition |

64x64 是 cmodel 功能 smoke 尺寸。它显著减少 DiT 和 Video VAE 的 token 规模，但仍执行真实的 attention、FFN、卷积、上采样和音视频后处理路径。

## 8. cmodel 实测结果

运行环境和关键配置：

| 项目 | 实测值 |
| --- | --- |
| vLLM | 0.27.1 |
| SUPA Omni plugin | `biren_supa` 已激活 |
| Server health | HTTP 200 |
| Generation API | `POST /v1/videos/sync` 返回 HTTP 200 |
| 最终状态 | `[H3] saved` |

阶段耗时：

| 阶段 | 耗时 | 占 forward 比例 |
| --- | ---: | ---: |
| Text encode | 780.16 秒，约 13 分钟 | 1.03% |
| DiT diffuse | 9315.82 秒，约 2 小时 35 分钟 | 12.25% |
| Video + Audio VAE decode | 65963.54 秒，约 18 小时 19 分钟 | 86.72% |
| Pipeline forward | 76063.79 秒，约 21 小时 7 分钟 | 100% |
| HTTP 请求端到端 | 76067.81 秒，约 21 小时 7 分 48 秒 | - |
| MP4 编码 | 426.30 ms | - |

当前 profiler 只记录联合 `decode`，无法从这份日志进一步拆分 Video VAE 和 Audio VAE 的单独耗时。

输出文件经 `ffprobe` 检查：

| Stream | 结果 |
| --- | --- |
| Video | H.264，64x64，24 FPS，107 帧，4.458333 秒 |
| Audio | AAC，32 kHz，双声道，4.450000 秒 |
| Container | MP4，312674 bytes，4.459000 秒 |

退出阶段出现的 ZMQ `Unclosed socket/context` 是进程关闭时的资源清理警告。请求已经返回 HTTP 200、MP4 已落盘、worker 和 FastAPI 均完成关闭，因此这些警告不影响本次功能通过结论。

## 9. 本次验证覆盖范围

### 已验证

- `vllm_supa` 和 `vllm_omni_supa` 插件加载。
- MiniMax-H3 FL2VA/T2VA pipeline 识别与初始化。
- CPU-first model loading 和 model-level CPU offload。
- Qwen3-VL 纯文本 encoder 的一层真实权重执行。
- 一层 token refiner 和一层联合音视频 DiT。
- `FLASH_ATTN` 到 BR200 `flashattn_infer` 的映射路径。
- 24-channel Video latent 的 Video VAE 解码。
- 32-channel Audio latent 的裁剪 BigVGAN 解码。
- 107 帧视频与 32 kHz 双声道音频的同步输出。
- H.264/AAC MP4 编码、HTTP 返回和文件落盘。

### 未验证

- 原始 50 层 DiT、64 层 text decoder、36 层 Video VAE decoder 的完整执行。
- 原始全尺寸 checkpoint 的输出精度和内容质量。
- 448x256、768p、2K 等生产尺寸。
- FL2VA 图像条件输入以及 vision encoder 的实际 forward。
- Ref2VA 视频/音频条件输入以及 Video/Audio VAE encoder 的实际 forward。
- 与 NVIDIA H200 golden output 的数值一致性。
- BR200 真卡性能；cmodel 时间不能直接外推为硅上性能。
- Video VAE 与 Audio VAE 各自的独立耗时。

## 10. 汇报口径建议

建议使用：

> 已完成 MiniMax-H3 真实权重裁剪模型在 BR200 cmodel 上的 T2VA 端到端功能验证。模型保持原始 pipeline 和各模态主结构，每类重复 block 至少保留一个代表层，并成功生成 107 帧 H.264 视频和 32 kHz 双声道 AAC 音频。当前主要耗时集中在 VAE 联合解码阶段，后续工作是细分 Video/Audio VAE 耗时并开展算子性能优化。

不建议使用：

- “MiniMax-H3 全量模型已经适配完成”。
- “MiniMax-H3 精度已经验证”。
- “MiniMax-H3 在 BR200 上性能达标”。
- “Video VAE 或 Audio VAE 单独耗时为 18 小时”。现有 profiler 只提供二者合计。

## 11. 复现命令

```bash
cd "${REPO_ROOT}"

python3 -u scripts/check_minimax_h3_supa.py \
  --model "${MODEL_ROOT}" \
  --width 64 \
  --height 64 \
  --steps 2 \
  --duration 4 \
  --output minimax_h3_supa.mp4 \
  2>&1 | tee logs/test_server.log
```

成功判据：

1. 日志包含 `OmniPlatform plugin biren_supa is activated`。
2. 日志包含 `vllm-omni-supa mapped Omni FLASH_ATTN to flashattn_infer`。
3. `POST /v1/videos/sync` 返回 HTTP 200。
4. 日志包含 `[H3] saved:`。
5. `ffprobe` 能识别 107 帧 H.264 视频和 32 kHz 双声道 AAC 音频。

## 12. 后续工作

1. 在 pipeline 的 Video VAE 和 Audio VAE 调用边界分别添加同步计时，拆分当前 18 小时 19 分钟的联合 decode 耗时。
2. 分别建立 Video VAE 与 Audio VAE 的单组件 cmodel smoke，记录每个 temporal chunk、BigVGAN stage 和 AMP block 的耗时。
3. 功能路径稳定后，再逐级提高画布尺寸和 diffusion steps；不要直接用 cmodel 运行生产分辨率作为第一道验证门槛。
4. 如需精度结论，使用同一裁剪模型、相同 prompt/seed/shape 在 H200 上生成 golden，并进入 SUPA 与 H200 的 tensor/output 对比流程。
