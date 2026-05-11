# 大语言模型是如何工作的

一个可视化、交互式的指南，讲解大语言模型是如何构建的——从原始互联网文本到对话助手。

**在线站点：** https://ynarwal.github.io/how-llms-work/

基于 Andrej Karpathy 的 [大语言模型入门](https://www.youtube.com/watch?v=zjkBMFhNj_g) 讲座。

---

## 内容概览

- **数据采集** — 网络如何被爬取并过滤成训练数据（Common Crawl、FineWeb）
- **分词** — 文本如何通过字节对编码（BPE）拆分为子词 token
- **神经网络训练** — 损失函数、梯度下降，以及前向传播的过程
- **推理与采样** — 模型如何逐 token 生成文本，以及 temperature 的工作原理
- **基础模型** — 预训练后模型知道什么，还不能做什么
- **后训练** — RLHF、指令微调，以及基础模型如何变成助手
- **LLM 心理** — 幻觉、上下文窗口，以及如何理解模型"知道"什么
- **RAG** — 检索增强生成：嵌入、向量搜索和上下文注入
- **完整流程总结** — 每个阶段的端到端可视化

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `index.html` | 主站（v2 重设计版） |
| `v1.html` | 原始暗色主题版本 |
| `transcript.txt` | Karpathy 讲座完整转录 |
| `council.py` | LLM 委员会事实核查工具（通过 `uv run council.py` 运行） |
| `report.html` | 最新委员会事实核查报告 |

---

## HN 讨论

[发布到 Hacker News](https://news.ycombinator.com/item?id=47886517) 后引发了激烈讨论，主要是关于内容由 LLM 生成这一点。说得对——但内容不是 AI 的。每一个论断、数据和框架都直接追溯自 Karpathy 的讲座，而非模型幻觉。

## 说明

本仓库的代码和内容主要由 LLM 生成（通过 Claude Code 使用 Claude）。想法和方向是我的——实现主要由 AI 完成。委员会事实核查工具正是为此而存在：自动化内容需要自动化验证。
