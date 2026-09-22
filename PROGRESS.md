# calm 实现进度

> 目标：DESIGN.md M3 里程碑（diff 复扫 + 人工任务卡片 + kb 扩至 30 平台）。
> 最后更新：2026-09-22

## ✅ 已完成

```
calm/
├── pyproject.toml / .gitignore / assets.yaml.example
├── calm.py                  # Typer CLI：init / scan / report(--format) / diff / task
├── collectors/
│   ├── base.py              # Finding dataclass、Collector ABC、编排器、OwnershipError、去重
│   ├── d1_search.py         # Brave Search API
│   ├── d2_holehe.py         # holehe 编程式接入
│   ├── d3_hibp.py           # HIBP API
│   ├── d4_maigret.py        # maigret CLI 调用
│   └── d5_exif.py           # piexif 解析 GPS/设备
├── linker/
│   ├── rules.py             # same_email / same_nickname / same_avatar / text_hit / same_device / same_gps
│   └── graph.py             # networkx 连通分量 → Chain
├── scorer/
│   ├── exposure.py          # §6 暴露分
│   └── cutscore.py          # §6 断链分与修复排序
├── kb/remediation.yaml      # 修复知识库（30 条平台指引）
└── report/
    ├── markdown.py          # Markdown 报告
    ├── html.py              # HTML 报告
    ├── diff.py              # 两次扫描链变化对比
    └── task.py              # 人工任务列表演示与提交
```

## ✅ 已验证

- 全部文件语法通过（py_compile）
- `calm diff` 默认对比 `chains-prev.json` 与 `chains.json`
- 模拟修复（移除一个 avatar 资产）后，`diff` 正确输出：1 条链已断、1 条链新增
- `calm task --list` 列出 nickname/realname/phone 人工任务
- `calm task --type nickname --value <value> --note <result>` 持久化到 `tasks.jsonl`
- `kb/remediation.yaml` 已扩展到 30 条

## 🔧 M3 相对于 M2 的改动

- 新增 `report/diff.py`：基于链节点集合 key 对比前后两次扫描，输出 broken/weakened/new/strengthened 变化
- `calm.py`：
  - `report` 生成 `chains.json` 前自动备份旧文件为 `chains-prev.json`
  - `diff` 子命令支持 `--before`、`--after`、`--output`
- 新增 `report/task.py`：
  - `task --list` 生成 `tasks.md`
  - `task --type <type> --value <value> --note <note>` 提交结果到 `tasks.jsonl`
- `kb/remediation.yaml`：从 18 条扩展到 30 条，新增 Twitter/X、YouTube、Instagram、Facebook、LinkedIn、Reddit、TikTok、Telegram、Snapchat、Pinterest、Twitch、Discord 平台修复指引

## ▶️ 续作步骤

MVP（M1+M2+M3）已跑通。后续演进方向（DESIGN §12）：

1. **误报治理**：用 embedding 聚类降低 D1/D4 的误报
2. **定期复扫提醒**：Telegram bot 或本地 cron 形态
3. **kb 社区化**：平台设置变更众包更新
4. **能力化输出**：让 calm 作为 phus 生态的一个能力被编排调用
