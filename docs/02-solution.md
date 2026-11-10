# 实际实现与局部取舍

架构采用Python原生单Agent、SQLite三表与CLI；实现入口在src/content_planner。当前只支持从源码目录可编辑安装，合成目录位于项目data；独立wheel的数据部署未验证。

## 四工具与不可变引用

| 工具 | 实际输入重点 | 结果与身份 |
| --- | --- | --- |
| search_materials | query、filters、limit、decision_summary | 原始合成素材/摘要；规范化查询和目录内容决定操作键。 |
| estimate_plan | new_spec与quote_id二选一；stage；script_artifact_id；decision_summary | 新规格登记不可变快照；引用旧报价只读取规格。每次新quote_id、sequence，读新账本与时钟；免费。 |
| generate_script | quote_id、decision_summary | 先按有效规格摘要查成功结果；可复用时返回原artifact、0增量。新执行才核对前置报价、依赖与费用时间。 |
| save_plan | quote_id、script_artifact_id、draft、decision_summary | 必须post_generation报价，展开真实脚本正文、来源和费用保存；正常确认立即终结。 |

quote_id、模型call_id和展示revision不进入生成计费身份。估价引用旧账本版本可重新生成新报价；用旧报价做新收费执行则受版本守卫。候选规格由material_ids、mode、creative_brief和服务端绑定的主题/硬需求/资料摘要组成。真正改规格要重新报价并保留沉没成本。

报价显式sequence决定先后，不能依赖JSON字典顺序。输出保留历史latest_projection，并另用current_cost_projection表示保存确认后的I=实际总额、R=0；不会改写历史报价使它伪装成新报价。

## 三表与状态

- requests：请求键唯一、输入摘要和JSON快照；含逻辑步骤、尝试、产物、报价、事件、方案、回执、模拟时间。
- operations：操作键唯一、状态、实际执行计数和确认结果；估价使用新invocation身份，不缓存总价。
- ledger_entries：已确认成功收费、操作键唯一。操作成功、费用和快照更新同事务；失败只记尝试和时间。

四层状态逻辑分开，仍只建三表。生成/保存重试不清空既有产物。请求绑定规范化输入、资料摘要、模式、故障夹具和契约版本，防止离线结果冒充在线；同键异输入/资料/模式/夹具冲突。同键已存在不启动新执行；活动或中断请求只读返回，不自动接管。

保存正常事务写完整正文、回执、费用和COMPLETED；确认后程序直接输出，无模型finish。UNKNOWN分支不查询回执、不用旧快照整体回写；最后可信费用、未确认操作最大费用和当前未知总额分开。后续普通读到已确认事实可展示，但不是自动恢复。复杂提交后丢确认仅用存储层故障钩子测试“不旧写覆盖”，没有实现P1查证。

## 费用与时间

默认unit：检索1、basic6、premium10、保存1、估价0。已开始的明确失败不收费但消耗名义模拟时间；拒绝和成功复用均0增量。总预计=所有成功收费历史+剩余必需费用，未采用的旧脚本也算沉没成本。

有效时钟=真实UTC+累计模拟秒。不会把网络等待再加一次。预算/截止检查发生在新执行前和本地结果提交前；时钟倒退停止。单次模型、工具与运行有超时/提交前检查，工具为受控本地函数，不承诺强杀任意阻塞代码。

## 循环和可信报告

真实模型适配器使用OpenAI Responses，关闭并行工具及SDK自动重试，保存provider continuation对象于内存但不导出内部思维；call_id对应function_call_output再进入下一轮。一次返回多工具时都不执行，逐个回传协议拒绝。停止只接受stop/need_input结构；文字finish不能改状态。

离线适配器是显式脚本化状态机，独立标offline_mock；其中预算调整和失败重试分支只用于L2。真实适配器没有“超预算选basic/失败就重试”代码。真实模式缺配置或额度明确报错，不回退。

报告含五个必要里程碑计划（含未执行PENDING）、实际操作步骤/依赖、逐次尝试、全部工具结果、正文/引用、费用与回执。保存失败仍显示成功脚本；输入冲突报告额外记录existing_task_status，证据同时保存实际提交input与原bound_input，不篡改原任务。

## 与设计基线的局部差异

- 开发环境使用uv.lock安装，requirements.lock为实际导出；合成费表实际路径为data/cost-v1.json。
- 输入由make-input生成到var；examples只含实际运行产物，没有静态输入模板。
- 为沙箱设项目内缓存/临时目录；pytest用.cache/pytest。JSON和终端回执保留带offset的UTC，不依赖宿主时区；时间计算仍按设计口径，未另做时区界面。
- 增加只做离线CLI证据收集的scripts/collect_examples.py；不自动运行在线实验。
- P0硬需求采用有限文本语法“必用素材:ID”“必含原文:文字”，不支持的原文保留并请求澄清。
- 增加报价sequence、确认费用快照、pending_liability与当前调用/原任务区分，保证序列、未知费用和冲突证据清晰。

参考协议：[OpenAI官方Function calling](https://developers.openai.com/api/docs/guides/function-calling)。本次仅查文档并用安装的SDK做本地HTTP替身序列化测试；提供方实际模型兼容性尚未验证。其他官方技术路线调研保留在plan.md第2章。
