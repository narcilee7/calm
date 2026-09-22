# calm 实现进度

> 目标：DESIGN.md M1 里程碑（D2 holehe + D3 HIBP + D5 EXIF + Linker 基础规则 + Markdown 报告）。
> 最后更新：2026-09-22

## ✅ 已完成（代码全部落盘，854 行 / 16 个文件）

```
calm/
├── pyproject.toml / .gitignore / assets.yaml.example
├── calm.py                  # Typer CLI：init / scan / report / diff / task，--data-dir 全局选项
├── collectors/
│   ├── base.py              # Finding dataclass、Collector ABC、编排器、OwnershipError 合规闸门
│   ├── d2_holehe.py         # 编程式接入 holehe.modules，polite 模式并发 1 + 1s 间隔
│   ├── d3_hibp.py           # breachedaccount API，带 key/User-Agent；无 key 优雅跳过
│   └── d5_exif.py           # piexif 解析 GPS/Make/Model/序列号/时间
├── linker/
│   ├── rules.py             # same_email / same_nickname / text_hit（头像 hash 规则留接口）
│   └── graph.py             # networkx 连通分量 → Chain
├── scorer/
│   ├── exposure.py          # §6 公式：Σ(sensitivity × reach × conf)，归一化 0-10
│   └── cutscore.py          # broken_chains × chain_weight / op_cost
├── kb/remediation.yaml      # 修复知识库
└── report/
    ├── markdown.py          # §7 版式（暴露条/链/修复优先级/诚实区/人工任务）
    └── html.py / diff.py / task.py   # M2/M3 诚实占位
```

工程环境：仓库内 `.venv`（Python 3.14）已装好全部依赖含 holehe。
测试环境：`/tmp/calm-e2e/` 已备好测试 assets.yaml（email + nickname）和带 GPS EXIF 的测试照片。

## ✅ 已验证

- 全部文件语法通过（py_compile）
- CLI 正常加载，`--help` 输出五个子命令

## ⬜ 未验证（子代理在此步骤前被停止）

1. **端到端 `scan` 未跑过**：D2 真实网络探测、D3 无 key 降级提示、D5 GPS 抓取都未实机确认
2. **`report` 未跑过**：report.md 是否符合 DESIGN §7 版式、chains.json 是否合法未确认
3. **去重未验证**：scan 重复跑是否产生重复 Finding id
4. **holehe 接入方式未确认**：编程式调用是否适应当前 holehe 版本 API，跑起来才知道；不行就退 subprocess 解析

## ▶️ 续作步骤（按序执行）

```bash
cd /Users/bytedance/open_source/calm
.venv/bin/python calm.py --data-dir /tmp/calm-e2e scan      # holehe 全量约 2 分钟（120 站 × 1s）
.venv/bin/python calm.py --data-dir /tmp/calm-e2e report
cat /tmp/calm-e2e/report.md                                  # 对照 DESIGN §7 版式检查
.venv/bin/python calm.py --data-dir /tmp/calm-e2e scan       # 再跑一次验证去重
```

跑通后 M1 收工，下一里程碑是 M2（D1 Brave 搜索 + D4 maigret + HTML 报告）。

## 备注

- 所有改动未 commit（工作区全是 untracked 文件，验证通过后再由用户决定提交）
- holehe 真实扫描只查注册态、并发 1 + 1s 间隔，符合设计公理 2（被动源优先）
