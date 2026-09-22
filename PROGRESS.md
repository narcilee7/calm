# calm 实现进度

> 目标：DESIGN.md M2 里程碑（D1 Brave 搜索 + D2 holehe + D3 HIBP + D4 maigret + D5 EXIF + Linker 规则 + Markdown/HTML 报告 + 双评分 CutScore 排序）。
> 最后更新：2026-09-22

## ✅ 已完成

```
calm/
├── pyproject.toml / .gitignore / assets.yaml.example
├── calm.py                  # Typer CLI：init / scan / report(--format) / diff / task
├── collectors/
│   ├── base.py              # Finding dataclass、Collector ABC、编排器、OwnershipError、去重
│   ├── d1_search.py         # Brave Search API，查询 nickname/realname
│   ├── d2_holehe.py         # holehe 编程式接入，单 probe 5s 超时
│   ├── d3_hibp.py           # HIBP breachedaccount API
│   ├── d4_maigret.py        # maigret CLI 调用，Top N 站点，跳过非 ASCII 昵称
│   └── d5_exif.py           # piexif 解析 GPS/Make/Model/序列号
├── linker/
│   ├── rules.py             # same_email / same_nickname / same_avatar / text_hit / same_device / same_gps
│   └── graph.py             # networkx 连通分量 → Chain
├── scorer/
│   ├── exposure.py          # §6 暴露分
│   └── cutscore.py          # §6 断链分与修复排序
├── kb/remediation.yaml      # 修复知识库（含 D2/D4 account_registration）
└── report/
    ├── markdown.py          # §7 Markdown 版式
    ├── html.py              # §7 HTML 版式
    ├── diff.py / task.py    # M3 占位
```

## ✅ 已验证

- 全部文件语法通过（py_compile）
- CLI 正常加载，`calm report --format html` 可用
- 端到端 `scan` 跑通：D1/D2/D3/D4/D5 全部注册并产出 finding
- D4 maigret 真实命中：testuser123 → YouTube/Twitter
- `report` 同时输出 Markdown 与 HTML，链 2 条、可断点 9 个
- CutScore 排序生效：链 #1 第一条修复动作是"关闭相机 App 的位置记录"

## 🔧 M2 相对于 M1 的改动

- 新增 `collectors/d1_search.py`：Brave Search API 查询 nickname/realname
- 新增 `collectors/d4_maigret.py`：subprocess 调用 maigret，解析 simple JSON 报告，按 `maigret_top_sites` 限制站点数
- 新增 `report/html.py`：Jinja2 模板生成响应式 HTML 报告
- `calm.py`：
  - `scan` 注册 D1/D4
  - `report` 增加 `--format markdown|html` 选项
- `pyproject.toml`：新增 `jinja2` 依赖与 `maigret` optional dependency
- `assets.yaml.example`：新增 `keys.brave` 与 `settings.maigret_top_sites`
- `kb/remediation.yaml`：所有 account_registration 修复项 applies_to 加入 D4
- `collectors/d4_maigret.py`：自动检测 venv 内的 maigret 可执行文件；非 ASCII 昵称跳过

## ▶️ 续作步骤

M2 已收工，下一里程碑是 **M3（diff 复扫 + 人工任务卡片 + kb 扩至 30 平台）**。

如需继续 M3，可从以下开始：

1. 实现 `report/diff.py`：对比两次 `chains.json`，输出修复前后链的变化
2. 实现 `report/task.py`：接收并持久化人工任务结果（`calm task --submit`）
3. 扩展 `kb/remediation.yaml` 到 30 条平台指引
4. 添加 `calm diff` 子命令的真实逻辑
