# calm — 个人公网隐私安全检测器

> 定期给自己做一次「数字体检」，发现公开网络上能被别人利用的隐私碎片，优先处理最便宜的断点。

`calm` 是一款面向普通人的**自我隐私安全审计 CLI**。它只查你自己的信息，把分散在公开网络、数据泄露库、社交平台、照片元数据里的数字足迹拼成「关联链」，告诉你：

- 哪些碎片可能被陌生人串成你的画像
- 哪一条链风险最高
- 修哪个动作花的力气最小、断的链最多
- 修复一周后复扫，确认链真的断了

**核心承诺**：不查别人、不抓内容、不绕风控、不留云端。所有扫描和报告都在本地完成。

## 一句话

`calm` = 自动发现「公开网络上关于你的可关联信息」→ 排序修复优先级 → 验证修复效果。

## 它解决什么问题

普通人很难系统性地知道自己在网上暴露了哪些可被利用的信息：

- 同一个昵称在多个平台出现，容易被横向定位
- 照片 EXIF 里带 GPS 和设备序列号，发原图等于发定位
- 邮箱/手机号 historic 泄露，成为定向钓鱼的素材
- 早期注册的账号资料没清理，成为社工拼图的入口

`calm` 不做监控，不做威胁情报，只做一件事：**帮你把已经公开、但你自己没注意到的隐私碎片找出来，并给出可执行的修复清单**。

## 核心能力

| 能力 | 说明 | 数据源 |
|---|---|---|
| 邮箱注册态探测 | 你的邮箱在哪些网站注册过 | holehe |
| 泄露记录查询 | 你的邮箱出现在哪些数据泄露事件里 | Have I Been Pwned |
| 昵称跨平台探测 | 你的昵称在哪些平台有账号 | maigret |
| 搜索引擎快照 | 你的昵称/真名在搜索引擎里的结果 | Brave Search |
| 照片元数据审计 | 照片里是否残留 GPS、设备序列号 | 本地 EXIF |
| 关联链生成 | 把碎片拼成可被利用的链路 | 本地规则 + 简单聚类 |
| 修复优先级排序 | 按「断链效果 / 操作成本」排序 | 内置知识库 |
| 复扫对比 | 修复后再扫描，看哪些链真的断了 | 本地 diff |
| 人工任务卡片 | 工具不爬的部分，给你搜索关键词和 URL | 本地 tasks |

## 设计原则

1. **只查自己**：输入即声明所有权，不扫描他人
2. **被动源优先**：只查询公开 API 和本地文件，不抓取、不绕过风控
3. **本地优先**：扫描日志、报告、资产文件全部存在本地
4. **诚实边界**：断不了的链路会在报告里明确标注"不可修复"
5. **断链 > 暴露**：报告围绕"链"和"修复动作"输出，而不是堆砌发现数量

## 快速开始

```bash
# 安装（推荐带上所有可选数据源）
pip install "calm-privacy[holehe,maigret,embedding]"

# 初始化资产清单
calm init
# 编辑 assets.yaml，填入你的邮箱、昵称、照片目录、API keys

# 扫描
calm scan

# 看报告
calm report                    # Markdown
calm report --format html      # HTML

# 按报告修复后，复扫验证
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
    value: "你的昵称"
    verified: false
  - type: realname
    value: "你的真名"
    verified: false
  - type: avatar
    value: "/Users/you/Pictures/avatar.jpg"
    verified: false

keys:
  hibp: "your-hibp-api-key"      # ~$3.5/月，没有则跳过
  brave: "your-brave-token"      # 免费档 2000 次/月，没有则跳过

settings:
  exif_dirs: ["/Users/you/Pictures"]
  polite: true
  maigret_top_sites: 10
```

## 命令参考

| 命令 | 说明 |
|---|---|
| `calm init` | 创建 `assets.yaml` 模板 |
| `calm scan` | 全量扫描，结果追加到 `findings.jsonl` |
| `calm report [--format markdown\|html]` | 生成本地报告 |
| `calm diff [--before FILE] [--after FILE]` | 对比两次扫描，看修复效果 |
| `calm task --list` | 列出需要人工复核的任务 |
| `calm task --type nickname --value xxx --note "..."` | 提交人工复核结果 |

## 数据源与成本

| 源 | 用途 | 成本 |
|---|---|---|
| D1 Brave Search | 昵称/真名搜索快照 | 免费档 2000 次/月 |
| D2 holehe | 邮箱注册态探测 | 免费 |
| D3 HIBP | 泄露库查询 | ~$3.5/月 |
| D4 maigret | 昵称跨平台探测 | 免费 |
| D5 EXIF | 本地照片元数据 | 免费 |

## 报告长什么样

```markdown
# calm 报告 — 2026-09-22
暴露面: ███████░░░ 7.2/10 关联链: 2 条 可断点: 5 个

## 🔴 链 #1 — iPhone 15 Pro → 3 张照片 GPS
涉及资产：photo_home.jpg, photo_trip.jpg, photo_nodevice.jpg
- [D5] exif_device「iPhone 15 Pro」（3 处）
- [D5] exif_gps「(39.90, 116.41)」
- [D5] exif_gps「(31.23, 121.47)」

修复优先级：
1. 关闭相机 App 的位置记录 CutScore 25.5 成本 2min
2. 分享照片前剥离 EXIF 元数据 CutScore 10.2 成本 5min

## 🟡 不可修复项（诚实区）
- 历史泄露不可删除，接受并加固相关账号

## 📋 人工任务
- 去 Bing 搜 "你的昵称"，检查前 3 页是否有暴露真实身份的内容
```

## 它不是

- ❌ 不是社工库查询工具
- ❌ 不是爬虫/反爬工具
- ❌ 不是监控他人的工具
- ❌ 不是云端账号体系或报告托管服务
- ❌ 不是 ML 驱动的精准画像工具（v1 用规则 + 简单聚类降低误报）

## 许可

MIT
