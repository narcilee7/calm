# calm 实现进度

> 目标：MVP 完成，产品定位为「个人公网隐私安全检测器」。
> 最后更新：2026-09-22

## ✅ 已完成

```
calm/
├── pyproject.toml / .gitignore / MANIFEST.in
├── README.md / DESIGN.md / LICENSE
├── calm/
│   ├── __init__.py          # Typer CLI：init / scan / report(--format) / diff / task
│   ├── assets.yaml.example  # 资产清单模板
│   ├── kb/remediation.yaml  # 30 条平台修复/加固知识库
│   ├── collectors/          # D1-D5 数据采集器
│   ├── linker/              # 实体对齐规则 + 简单 embedding 聚类
│   ├── scorer/              # 暴露分 + 断链分
│   └── report/              # Markdown/HTML/diff/task
└── .github/workflows/       # CI + 发布到 PyPI
```

## ✅ 已验证

- 全部文件语法通过（py_compile）
- 可编辑安装：`pip install -e ".[holehe,maigret,embedding]"`
- wheel 安装后 `calm` 命令可用，`assets.yaml.example` 与 `kb/remediation.yaml` 正常加载
- `calm report` / `calm diff` / `calm task` 功能正常

## 🔧 本次打磨

- README.md 重写：
  - 标题改为「个人公网隐私安全检测器」
  - 强调"只查自己、被动源优先、本地优先、诚实边界"
  - 增加「它解决什么问题」「核心能力」「它不是」章节
- DESIGN.md：
  - 去掉"红方技术打自己""人肉攻击者视角"等攻击性表述
  - 重新定位为「和体检一样：不是攻击别人，而是定期自查、早发现早处理」
- CLI help：改为「calm：个人公网隐私安全检测器」
- 恢复误删的 DESIGN.md 和 PROGRESS.md

## ▶️ 后续可继续打磨的方向

1. **更友好的首次体验**：`calm init` 交互式问卷生成 assets.yaml
2. **更丰富的自我审计源**：
   - 反向图片搜索（检查头像/照片是否被滥用）
   - 公开 WHOIS/域名历史（检查个人域名暴露）
   - GitHub commit 邮箱泄露扫描
3. **修复知识库细化**：按平台给出"最小化公开资料"的具体路径
4. **报告可读性**：链的可视化图、风险等级颜色、导出 PDF
5. **定期体检提醒**：本地 cron / 系统通知集成
