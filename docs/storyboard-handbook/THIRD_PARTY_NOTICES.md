# 第三方来源与声明

本文件记录手册分析对象的来源、许可证和审计中发现的声明缺口。它是工程与编辑治理记录，**不构成法律意见**。准备公开发行、商业发行或拆分手册单独分发时，应由发行者复核当时版本的许可证义务。

## Narrative Forge

- 上游仓库：<https://github.com/Zafer-Liu/Narrative-Forge>
- 本手册审计的上游提交：`abebc29fd98ff8c9153f8b566c85c7a0e7b1e7a9`
- 用户 fork：<https://github.com/Wenjun-Mao/Narrative-Forge>
- 本地分析提交：`24c3c47a6fb1e3fcd5a060d705f11bbffb9dbde9`
- 仓库许可证：Apache License 2.0；许可证全文位于 Narrative Forge 仓库根目录的 `LICENSE`。

审计版本的 Narrative Forge 根目录没有独立 `NOTICE` 文件。本手册会把原项目行为、本地 fork 修改和本手册提出的重构设计分开标注。若直接修改或再分发第三方源文件，应按 Apache-2.0 要求保留适用声明，并在修改文件中留下显著的修改说明。

## shuohao-skills

- 仓库：<https://github.com/eternityspring/shuohao-skills>
- 审计提交：`4322897e6d2bdaf66365534fd40194360c75a85f`
- 仓库许可证：Apache License 2.0
- 审计版本 `NOTICE` 中的归属信息：

> shuohao-skills
> Copyright 2026 烁皓

若手册或其发行包包含来自 shuohao-skills 的可版权化内容，而不只是事实性分析、接口描述或链接，应同时复核 Apache-2.0 第 4 节的再分发条件，并在适用位置保留该 NOTICE 归属信息。

### NOTICE 中的样本路径不一致

审计版本的 `NOTICE` 将原创样本《渡口》写为：

```text
skills/storycast/examples/渡口.txt
```

同一固定提交中的实际路径是：

```text
skills/novel-characters/examples/渡口.txt
```

本手册把它记录为第三方仓库内部的陈旧路径，不静默改写上游 NOTICE，也不据此否定样本的版权归属。正文引用该样本时应使用实际路径，并注明 NOTICE 使用了旧路径。

### 私有 shot-recipes 缺口

shuohao-skills 的迁移设计文档说明，完整 `shot-recipes` 镜头语汇卡库迁往 `eternityspring/shuohao-video-skills`，并在迁移时保持为私有仓库。公开的 `novel-storyboard` 仍支持可选的 `--shots <cards-dir>` 接口，并带有最小测试夹具，但这些材料不能替代完整卡库。

因此，本手册可以分析：

- 外部卡库的挂载接口；
- 第 17 道可选质量门；
- 公开解析器、测试夹具和偏差报告行为；
- 迁移设计中公开陈述的目标与边界。

本手册不能声称已经获得或审计：

- 私有仓库中的完整配方卡；
- 私有仓库后续版本；
- 未在公开提交中出现的创作方法、样例或质量结论。

这一缺口应在涉及“镜头配方库完整能力”的章节中明确提示，而不是用公开测试夹具推断私有内容。

## 手册自己的内容

本手册的原创讲解、统一领域模型、比较框架、《月城失物局》案例、重新绘制的流程图和新制作的故事板不应被标记为第三方仓库原文。若某个图、表或代码片段改编自具体第三方文件，应在该内容附近注明项目、固定提交和文件路径。

手册采用链接或概括性描述并不意味着原作者认可本手册的分析或重构建议。项目名称仅用于说明来源，不表示赞助、合作或商标授权。

## 发行前检查

1. 确认发行包带有适用的 Apache-2.0 许可证全文。
2. 确认直接修改的第三方文件带有显著修改说明。
3. 确认适用的版权、专利、商标和归属声明没有被删除。
4. 若包含 shuohao-skills 的可版权化材料，确认 NOTICE 归属信息出现在许可证允许的位置。
5. 逐一复核图片、截图、示例故事和长代码摘录的来源与授权。
6. 重新检查私有或未取得材料没有被误写为已审计事实。
