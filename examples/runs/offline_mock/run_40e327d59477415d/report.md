# 毕业季：用旧照片做一支回忆短片：内容活动方案

模式：offline_mock。offline_mock为脚本化流程验证，不是真实模型决策证据。

任务：COMPLETED；保存：CONFIRMED；原因：SAVED
营销活动执行：NOT_STARTED。

## 目标

形成可审阅的内容草案，围绕主题邀请观众分享个人记忆；效果目标待业务确认。

## 受众

对毕业回忆和照片叙事感兴趣的受众，具体人群由运营审阅确认。

## 核心信息

毕业季：用旧照片做一支回忆短片

## 建议渠道

短视频账号（建议渠道，未发布）

## 脚本正文

开场：围绕「毕业季：用旧照片做一支回忆短片」，邀请观众找出一张旧照片。
核心表达：用旧照片的细节串联毕业回忆。
素材事实（合成演示）：
- 虚构演示工具影记可导入本地照片并添加文字（mat-001）
- 建议以今昔对照开场，结尾邀请观众选择一张旧照片；这不是已验证增长结论（mat-003）
叙事：以照片中的细节串起校园记忆，使用今昔对照，避免未经证实的效果承诺。
结尾：邀请观众选择一张照片，写下一句想留给毕业时自己的话。

## 素材引用（合成演示）

- mat-001：影记照片演示；synthetic://materials-v1/mat-001；demo_only
- mat-003：今昔对照创意；synthetic://materials-v1/mat-003；demo_only

## 活动任务建议（均未执行）

- review：核对素材事实、使用范围与脚本；依赖[]；内容运营；审批前
- produce：按获批脚本准备拍摄和剪辑；依赖['review']；制作人员；审批后T日
- publish：确认发布日期后发布并记录反馈；依赖['produce']；内容运营；待确认

## 风险和假设

- 合成素材只限演示；真实制作、版权和投放费用未计入模拟预算。
- 活动执行尚未开始；指标和发布日期待审阅；本次预算只覆盖方案准备。

## 本次准备工作的实际步骤

- 必需里程碑 retrieve：SUCCEEDED；依赖[]
- 必需里程碑 estimate_pre：SUCCEEDED；依赖['retrieve']
- 必需里程碑 generate：SUCCEEDED；依赖['estimate_pre']
- 必需里程碑 estimate_post：SUCCEEDED；依赖['generate']
- 必需里程碑 save：SUCCEEDED；依赖['estimate_post']
- step_044361a9285ede99：search_materials / SUCCEEDED；依赖[]
- step_338104fec0db4ce8：estimate_plan / SUCCEEDED；依赖['step_044361a9285ede99']
- step_61fdc21c697f1556：generate_script / SUCCEEDED；依赖['step_338104fec0db4ce8']
- step_65a672cd2d4dfe1e：save_plan / SUCCEEDED；依赖['step_61fdc21c697f1556', 'step_a166ad6e4c7864d4']
- step_a166ad6e4c7864d4：estimate_plan / SUCCEEDED；依赖['step_044361a9285ede99', 'step_61fdc21c697f1556']

## 费用（模拟unit，非API账单）

- search_materials：1；操作044361a9285e
- generate_script：6；操作61fdc21c697f
- save_plan：1；操作65a672cd2d4d

已确认总额：8；最后可信累计：8；本次增量：8。
剩余预计：0；预计总额：8。
保存回执：plan_81bce0f7f38b47fa；有效完成时间：2026-11-10T08:45:07.431040+00:00。
