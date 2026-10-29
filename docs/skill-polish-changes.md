# skill 打磨改动说明（2026-10-29）

## 改动目标

把 `voiceover-video-edit` 从“长文档 + 多套历史脚本”整理为“薄壳 skill + 独立 Python 包”，同时清除已删除模型、废弃参数和相互矛盾的操作规则。

## 文件改动

### 1. `~/.claude/skills/voiceover-video-edit/SKILL.md`

- 从完整脚本说明书改为执行层薄壳。
- 触发描述只保留口播剪辑、字幕、HDR、封面和质检，移除发布文案、账号诊断和限流分析，减少与其他 skill 的触发重叠。
- 实际入口统一为 `voiceover-edit` 或 `py -3.12 -I -m voiceover_edit` 的 9 个子命令。
- 旧 `scripts/` 保留作历史追查，不再作为工作流入口。
- ASR 改为显式使用现存 large-v3-turbo；不再有 medium/small 回退，不静默下载。
- HDR 规则改为由包内实现执行：HLG 默认 npl=200，tonemap 在 concat 后一次完成。
- 结构检查明确区分“实际比较”与“coverage skipped”，禁止把跳过当成通过。
- `verify` 明确标为整片字符覆盖粗查，不再冒充逐条时间轴验证。
- 封面拆成两层：干净 SDR 母版抽帧；HTML 排版复用 xuanfa 的 Edge→Playwright 渲染器，不新增截图实现。

### 2. `references/pitfalls.md`

- 重写为当前有效的 17 类核心坑及额外交付边界。
- 修正 HLG `npl=100`、词界中点下刀、已删除模型回退等旧规则。
- 增加“自动检查不等于最终验收”和 xuanfa 渲染复用规则。

### 3. `references/pitfalls-legacy.md`

- 保留旧版详细事故记录，避免丢失历史上下文。
- 仅用于追查旧事故；与当前规则冲突时，以新版 SKILL、当前踩坑清单和包实现为准。

### 4. `docs/skill-operation-review.md`

- 新增实际运行状况完整复盘。
- 记录 12 个项目、14 次自动触发和 3 次未经过 skill 的外部执行。
- 用“问题节点—根因—修复—验证”四列表逐项标明已验证与待复验。
- 单列当前仍不好用或未覆盖的边界。

### 5. `HANDOVER.md`

- 更新本轮交接日期、文档入口和剩余复验项。
- 移除已经完成的触发描述与踩坑修复待办。

## 没有做的事

- 没有删除旧脚本或历史踩坑档案。
- 没有另写 HTML→PNG 渲染器。
- 没有把 51 项自检通过包装成真实 4K HDR、iPhone 或跨平台验收通过。
- 没有改动用户原视频、逐字稿或发布数据。
- 没有把账号流量规则写进通用剪辑引擎。

## 验证结果

- `voiceover-edit --help` 及 9 个子命令入口可用。
- `run_tests.py`：51 项通过、0 项失败。
- 本机 large-v3-turbo 的模型目录、`config.json`、`model.bin` 均存在。
- xuanfa 渲染器已确认支持 Edge 优先和 Playwright 回退。

## 下一轮真实验收建议

选一条包含中英混排和多个切点的 4K HLG 素材，完整执行剪辑、字幕、渲染、结构检查、媒体 QC、字幕复核和封面渲染；记录实际内存、耗时、画面、字幕、手机播放与封面结果，再关闭对应待复验项。
