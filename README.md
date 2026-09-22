# calm

> 用红方技术打自己，拿回平静。
> 人肉攻击者视角的自我隐私审计 CLI。

## 一句话

自动完成 OSINT 自查 → 身份关联图谱 → 断链优先级 → 复扫验证闭环。

## 能做什么

- **扫描**：从邮箱注册态（holehe）、泄露库（HIBP）、照片 EXIF、昵称跨平台（maigret）、搜索引擎（Brave）多源收集你的数字足迹
- **关联**：把不同来源的碎片拼成"链"，告诉你哪些信息会被攻击者串起来
- **评分**：暴露分 + 断链分，按"修一个动作断多少链、链有多重、操作多便宜"排序
- **报告**：Markdown / HTML 双格式，诚实标注"不可修复项"，并生成人工任务卡片
- **复扫**：`calm diff` 对比两次扫描，验证修复真的把链断了
- **聚类**：简单 TF-IDF + DBSCAN 对相似 finding 聚类，辅助降低误报

## 快速开始

```bash
# 1. 安装
pip install -e ".[holehe,maigret,embedding]"

# 2. 初始化资产清单
calm init
# 编辑 assets.yaml，填入你的 email、nickname、照片目录、API keys

# 3. 扫描
calm scan

# 4. 生成报告
calm report                    # Markdown
calm report --format html      # HTML

# 5. 修复一周后复扫
calm scan
calm diff
```

## 资产清单示例

```yaml
profile:
  name: "你的名字"

assets:
  - type: email
    value: "you@example.com"
    verified: false
  - type: nickname
    value: "your_nickname"
    verified: false
  - type: avatar
    value: "/Users/you/Pictures/avatar.jpg"
    verified: false

keys:
  hibp: "your-hibp-api-key"
  brave: "your-brave-search-token"

settings:
  exif_dirs: ["/Users/you/Pictures"]
  polite: true
  maigret_top_sites: 10
```

## 命令

| 命令 | 说明 |
|---|---|
| `calm init` | 从模板创建 `assets.yaml` |
| `calm scan` | 执行全量扫描，结果追加到 `findings.jsonl` |
| `calm report [--format markdown\|html]` | 生成关联链报告 |
| `calm diff [--before FILE] [--after FILE] [--output FILE]` | 对比两次扫描的链变化 |
| `calm task --list` | 列出人工搜索任务 |
| `calm task --type nickname --value xxx --note "..."` | 提交人工任务结果 |

## 数据来源

| 源 | 说明 | 成本 |
|---|---|---|
| D1 Brave Search | 昵称/真名搜索引擎快照 | 免费档 2000 次/月 |
| D2 holehe | 邮箱注册态探测 | 免费 |
| D3 HIBP | 泄露库查询 | ~$3.5/月 |
| D4 maigret | 昵称跨平台探针 | 免费 |
| D5 EXIF | 本地照片元数据 | 免费 |

## 设计原则

1. **先为自己造**：每个 feature 过一票"上周的我会为此付钱吗"
2. **被动源优先**：只查询、不抓取、不绕风控
3. **诚实边界**：断不了的链报告里明说"不可修复"
4. **断链 > 暴露**：输出围绕"链"，告诉你最便宜的断点

## 许可

MIT
