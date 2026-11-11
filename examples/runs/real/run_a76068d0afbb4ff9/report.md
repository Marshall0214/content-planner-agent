# 毕业季：用旧照片做一支回忆短片

模式：real。真实模式记录需人工检查反馈与动作关联；当前不自动判定合格动态路径。

任务：COMPLETED；保存：CONFIRMED；原因：SAVED
营销活动执行：NOT_STARTED。

## 目标

通过旧照片串联校园记忆，激发毕业季情感共鸣，演示影记工具功能

## 受众

即将毕业的大学生及怀念校园时光的群体

## 核心信息

每一张旧照片都承载着珍贵的校园记忆，用今昔对照的方式重温青春时光

## 建议渠道

短视频平台、社交媒体

## 脚本正文

开场：围绕「毕业季：用旧照片做一支回忆短片」，邀请观众找出一张旧照片。
核心表达：创作一支毕业季主题回忆短片，以旧照片为线索串联校园记忆。开场采用今昔对照手法展示同一场景的变迁，中段穿插影记工具演示（导入本地照片并添加文字），结尾邀请观众选择一张自己的旧照片参与互动。所有素材均为demo_only用途，仅用于演示效果，不涉及真实个人数据或已验证增长结论。。
素材事实（合成演示）：
- 虚构演示工具影记可导入本地照片并添加文字（mat-001）
- 校园空镜清单含教学楼、操场和毕业合照占位图，不含真实个人数据（mat-002）
- 建议以今昔对照开场，结尾邀请观众选择一张旧照片；这不是已验证增长结论（mat-003）
叙事：以照片中的细节串起校园记忆，使用今昔对照，避免未经证实的效果承诺。
结尾：邀请观众选择一张照片，写下一句想留给毕业时自己的话。

## 素材引用（合成演示）

- mat-001：影记照片演示；synthetic://materials-v1/mat-001；demo_only
- mat-002：合成校园空镜；synthetic://materials-v1/mat-002；demo_only
- mat-003：今昔对照创意；synthetic://materials-v1/mat-003；demo_only

## 活动任务建议（均未执行）

- task_001：脚本审阅与确认，确保素材使用符合demo_only用途说明；依赖[]；内容审核；T+0
- task_002：根据脚本准备合成素材（影记工具演示、校园空镜、今昔对照画面）；依赖['task_001']；制作团队；T+1
- task_003：视频剪辑与后期制作，添加文字说明和互动引导；依赖['task_002']；后期制作；T+2
- task_004：发布前最终审核，确认无真实个人数据泄露风险；依赖['task_003']；内容审核；T+3

## 风险和假设

- 素材为合成演示，需明确标注demo_only用途
- 未执行真实拍摄或发布，效果未经实际验证
- 需避免观众误认为真实功能或已验证增长结论
- 目标受众对毕业季主题有情感共鸣
- 影记工具演示功能可被清晰理解
- 今昔对照手法能有效唤起回忆

## 本次准备工作的实际步骤

- 必需里程碑 retrieve：SUCCEEDED；依赖[]
- 必需里程碑 estimate_pre：SUCCEEDED；依赖['retrieve']
- 必需里程碑 generate：SUCCEEDED；依赖['estimate_pre']
- 必需里程碑 estimate_post：SUCCEEDED；依赖['generate']
- 必需里程碑 save：SUCCEEDED；依赖['estimate_post']
- step_19e716dcffbf5133：estimate_plan / SUCCEEDED；依赖['step_6f978ec2e71abfae', 'step_a4e69cd95bf03bcb']
- step_3ff8eb2d996c1e6d：estimate_plan / SUCCEEDED；依赖['step_a4e69cd95bf03bcb']
- step_6f978ec2e71abfae：generate_script / SUCCEEDED；依赖['step_3ff8eb2d996c1e6d']
- step_75eb11100e9f37a0：search_materials / FAILED；依赖[]
- step_8977fd6fb5b81b1f：save_plan / SUCCEEDED；依赖['step_19e716dcffbf5133', 'step_6f978ec2e71abfae']
- step_a4e69cd95bf03bcb：search_materials / SUCCEEDED；依赖[]
- step_f500bda73b2b39c0：save_plan / FAILED；依赖[]

## 费用（模拟unit，非API账单）

- search_materials：1；操作a4e69cd95bf0
- generate_script：6；操作6f978ec2e71a
- save_plan：1；操作8977fd6fb5b8

已确认总额：8；最后可信累计：8；本次增量：0。
剩余预计：0；预计总额：8。
保存回执：plan_a9e605003b944a3d；有效完成时间：2026-11-10T10:36:07.102025+00:00。
