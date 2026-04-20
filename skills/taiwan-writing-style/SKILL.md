---
name: taiwan-writing-style
description: Use when writing, replying, or generating any Traditional Chinese content — ensures Taiwan tech industry vocabulary and tone.
allowed-tools:
  - Read
---

# Taiwan Writing Style

## Core Rule

所有中文輸出請使用台灣常用的用語與科技業慣用語風格。

- 語氣專業、簡潔
- 技術名詞優先使用原文（API, PR, CI/CD, Debug, Build, Sprint...）
- 中英夾雜自然風格，不硬翻技術術語

## 高頻替換清單（LLM 最容易帶出的中國用語）

| ❌ 避免 | ✅ 使用 |
| :--- | :--- |
| 用戶 | 使用者 |
| 支持 | 支援 |
| 配置 | 設定 / 組態 |
| 優化 | 最佳化 |
| 場景 | 情境 |
| 交互 | 互動 |
| 調用 | 呼叫 |
| 返回 | 回傳（API）/ 返回上一頁（UI）|
| 接口 | 介面 / API |
| 實例 | 執行個體 |
| 緩存 | 快取 |
| 推理 | 推論 |
| 大模型 | 大型語言模型 / 大型模型 |
| 提示詞 | 提示 |
| 賦能 | 強化 / 支援 / 提供能力 |
| 落地 | 導入 / 實作 / 上線 |
| 去重 | 移除重複 / 去除重複 |

## 嚴格詞彙校對模式

當使用者要求「逐字校對」、「嚴格檢查用詞」、「正式文件審查」時：

1. 使用 Read tool 載入同目錄的 `vocabulary.md`
2. 對照 17 個分類的完整詞彙表逐字比對輸出內容
