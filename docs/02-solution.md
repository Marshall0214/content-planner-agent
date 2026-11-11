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

同键重放先走只读绑定分支；Store.read_record在一个SELECT中联读requests快照和STARTED/UNKNOWN操作身份。reporting.project_read_snapshot据此生成内存视图，run重放与inspect共用，export也使用该视图拒绝未确认方案。未确认保存投影save_state=UNKNOWN，任务INCOMPLETE/RESULT_UNKNOWN，当前总额null；不把旧RUNNING快照中的7当作当前已确认总额。STARTED尝试登记时同步保存admitted_liability（操作身份、费用和模拟时间上界）；已有旧记录可从尝试引用的不可变报价提取责任，缺资料就保留null，不套用当前费表猜测。

投影包含unconfirmed_operations、pending_liabilities及兼容单项pending_liability。它们是未确认责任，不是收费记录；成功脚本与既有账本均保留。仅在终态已经持久化时termination_persisted才可为true；本轮回归中的旧RUNNING快照投影标false，read_projection.persisted=false并列原任务/保存状态。只读路径不创建模型、不执行工具、不新增账本、不写入投影；同键正常完成则返回原方案/回执和零增量。此修复没有增加表、迁移、回执查证、恢复或续跑。

## 费用与时间

默认unit：检索1、basic6、premium10、保存1、估价0。已开始的明确失败不收费但消耗名义模拟时间；拒绝和成功复用均0增量。总预计=所有成功收费历史+剩余必需费用，未采用的旧脚本也算沉没成本。

有效时钟=真实UTC+累计模拟秒。不会把网络等待再加一次。预算/截止检查发生在新执行前和本地结果提交前；时钟倒退停止。单次模型、工具与运行有超时/提交前检查，工具为受控本地函数，不承诺强杀任意阻塞代码。

## 循环和可信报告

真实模型适配器使用OpenAI Responses，关闭并行工具及SDK自动重试。每次出站只有一份最新完整状态快照，原生工具调用/观察及provider continuation对象完整保留且相对顺序不变；call_id对应function_call_output再进入下一轮。一次返回多工具时都不执行，逐个回传协议拒绝。停止只接受stop/need_input结构；文字finish不能改状态。

离线适配器是显式脚本化状态机，独立标offline_mock；其中预算调整和失败重试分支只用于L2。真实适配器没有“超预算选basic/失败就重试”代码。真实模式缺配置或额度明确报错，不回退。

报告含五个必要里程碑计划（含未执行PENDING）、实际操作步骤/依赖、逐次尝试、全部工具结果、正文/引用、费用与回执。保存失败仍显示成功脚本；输入冲突报告额外记录existing_task_status，证据同时保存实际提交input与原bound_input，不篡改原任务。

## 本地Qwen接入与证据边界

MODEL_PROVIDER=ollama选择已部署服务的无状态Responses协议；MODEL_NAME和本机OPENAI_BASE_URL显式配置，不自动选择模型或端点。SDK占位密钥不是云端密钥，本地HTTP忽略代理环境且重试0。MODEL_TEMPERATURE可选，须为0到2有限数；本轮显式0.2。普通openai云端分支保留，真实失败不回退离线。

Agent只新增模型配置元数据，报告导出服务类型、端点、协议和配置的推理参数；业务工具、报价、三表和UNKNOWN规则不变。scripts/validate_qwen.py只收集真实本地实验，发出的Responses请求正文与匹配的call_id/实际工具结果进入证据索引，鉴权头与内部思维不导出。冒烟最多3次，包括错误/超时；验收另限30次，每请求10次，冒烟不通过就禁止验收。没有预写动作或自动重试实验。

2026-11-10实际服务支持原生Responses，因而未增加Chat或JSON动作适配器。但协议路由存在、原生调用返回，不等于业务兼容验收：3次冒烟均未取得成功业务工具执行，具体失败见03-evaluation.md，不能宣称本地Qwen验收通过。

## 与设计基线的局部差异

- 开发环境使用uv.lock安装，requirements.lock为实际导出；合成费表实际路径为data/cost-v1.json。
- 输入由make-input生成到var；examples只含实际运行产物，没有静态输入模板。
- 为沙箱设项目内缓存/临时目录；pytest用.cache/pytest。JSON和终端回执保留带offset的UTC，不依赖宿主时区；时间计算仍按设计口径，未另做时区界面。
- 增加只做离线CLI证据收集的scripts/collect_examples.py；不自动运行在线实验。
- P0硬需求采用有限文本语法“必用素材:ID”“必含原文:文字”，不支持的原文保留并请求澄清。
- 增加报价sequence、确认费用快照、pending_liability与当前调用/原任务区分，保证序列、未知费用和冲突证据清晰。

参考协议：[OpenAI官方Function calling](https://developers.openai.com/api/docs/guides/function-calling)。初期只查文档并用安装的SDK做本地HTTP替身序列化测试；后续本地Ollama的实际兼容结果见03-evaluation.md，云端/其他提供方兼容性仍未实测。其他官方技术路线调研保留在plan.md第2章。

27B复测新增MODEL_THINK可选true/false，仅用于Ollama Responses的think扩展；不设置采用服务默认。实验脚本--no-think显式发送false并记录该差异。证据导出将历史中的reasoning项标为省略，实际发送给模型的历史不改动；工具调用、ID和观察完整保留。新增4项离线测试验证开关/配置拒绝及脱敏不改原始上下文，完整91项通过。27B三次仍因filters字符串而拒绝，该轮尚未实施Schema内联，后续受限对照见03-evaluation.md。

## Ollama出站Schema内联修复

schema_compat.py对Ollama工具定义深拷贝，递归解析本地JSON Pointer；覆盖filters、nullable anyOf、draft和数组items，定义本体在检查后展开并去掉根定义注册表。保留required、null分支、enum、长度/数值/数组限制和additionalProperties；引用与同层约束冲突时用allOf同时保留，enum等实例值不按Schema引用解释。缺失、外部、非法或循环引用明确报错。

模型构造期完成转换，先于SDK请求和请求额度计数；云端仍使用原定义。元数据记录策略及原始/出站Schema摘要。未改变Pydantic校验或任何业务工具，没有二次json.loads(filters)和参数代填。实际SDK测试验证结构和云端/原模型不变；非法字符串被拒绝不收费，合法对象执行收费1，实际结果按原call_id回传。

本轮固定27B、Ollama0.40.9、think=false、temperature0.2、4000输出和20/180秒上限，只改变出站Schema，业务输入仅新请求键/新期限及实时时钟变化。3次实际对照中filters对象校验与成功检索观察回传成立，估价仍被空素材列表拒绝。仅满足本轮Schema条件，不是正式业务验收；详情见评估文档。

## 检索契约与空结果反馈

本轮只补清检索契约/反馈及对应模型说明，不改变query的空白分词OR子串匹配或tags的AND精确匹配。tags=[]不作标签过滤，allowed_usage仅null不限；非null包括空字符串均精确匹配，修正旧truthy判断把空串误当不限的边界。Field只增加描述，Pydantic校验类型、上限、空material_ids拒绝和原收费规则保留；Ollama内联保持，云端使用当前原始契约。

search_materials.data.feedback总是报告applied_filters、keyword_match_count、filtered_match_count（截断前）和returned_count。catalog_available_tags/usage_scopes及unrecognized_tags/allowed_usage来自实际目录，不承诺可用标签一定命中当前query；empty_reason区分无关键词命中与过滤排空。next_action_hint仅解释事实与可选后续，不执行补检索或自动清空过滤。

用户硬要求保持；现有P0有限硬需求语法不支持的硬过滤在调用模型前NEEDS_INPUT澄清。没有匹配素材不能用空列表估价。新反馈只存在于新执行结果，旧成功缓存/历史请求不回写升级；同操作成功复用仍0增量，新的收费检索包括空结果均1 unit/60模拟秒。

实验脚本新增normal阶段：只跑一条正常请求、硬上限10次真实请求；确认保存时才用原输入/原键重放，检查同方案/回执、零推理/工具请求/实际执行/费用和数据库不变。既有smoke3/acceptance30阶段保留，本轮未运行acceptance。实际正常链路在最新复估后第6次推理读超时，未进入draft/保存；没有失败续跑或自动换请求。相关46项、完整119项通过，真实部分结果见03-evaluation.md。

## 最新快照与原生历史分离

本轮核心只修改model.py：适配器私有_state_message保存自己创建消息的对象身份；下一次choose先只移除该对象，再把新context原样序列化为输入首位消息。其他消息即使角色为user、文本完全相同或包含state关键词，也不按内容删除。供应商输出对象（含所需不透明续接数据）、实际调用/参数/call_id和function_call_output按原顺序保留；不生成摘要、不改观察、不代填draft或选择保存。

完整最新context保留原需求/硬约束、当前已发生费用与账本版本、候选、全部报价与成功产物、工具观察和剩余额度。Agent、数据库完整账本、累计快照及Trace记录不变；只减少模型出站冗余，不回写审计历史。模型、Schema、提示词、工具业务规则和额度/终态处理均未改。

新增3项SDK MockTransport测试（openai/ollama两种配置及非适配器消息保护），相关64项、完整122项通过。compare_model_context.py只重放录制的供应商输出/观察并捕获六次MockTransport请求，完全不调用Planner/业务工具或模型服务；末轮异常也是录制超时的离线替身，不是新模型失败。原始状态/文件哈希保持。

第6次统一重序列化后16→11消息、104487→46581 UTF-8字节，不能当token或性能结果。修复阶段只做离线验证；后续新授权轮实际7次真实推理后draft修正/保存确认及原样重放通过，详见03-evaluation.md，未改实现。保留20秒单次/180秒运行上限。validate_qwen.py仍自行Limits()，后续超时调整需看构造值、记录值及实际SDK请求，不依赖环境变量猜测。正常一次通过不代表两类动态路径或整体P0达标。

## 冻结实现后的专项实验入口

最新轮只增加validate_qwen.py的specialties场景选择、20次批次/10次单场景门禁及正常证据引用。引用先核对非空同方案/回执、零增量与业务摘要，未通过即不创建任务/客户端；新阶段不含normal推理或重放执行，先记录信息不足入口，再尝试预算与save_fail_once。失败/超时均计入，终止条件或不变量失败时不扩场景；没有改Planner、模型适配器、工具、账本或持久化。

门禁22项、完整140项通过，实际11次专项推理后结束。预算有真实反馈与最终有依据停止，但中间被拒动作保留；save_fail_once未进入实际保存，未取得SAVE_TEMPORARY，不能判该专项通过。冻结业务摘要与正常证据一致，实际脚本摘要及后验核对见03-evaluation.md和specialties-evaluation.json。用户审阅建议单列06-content-review.md，不覆盖任何原始保存版本。

独立生成专项新增generate_failure入口（一个请求，批次/场景各6次）及门禁，运行时和配置不改。实际6次链路在生成失败后由模型重试成功，但模型可见请求键包含场景标签，故盲测不合格。该轮执行脚本摘要f1f30f...及快照保留；现已仅对该入口用随机UUID键隔离场景元数据，新增实际SDK MockTransport验证首个请求状态不含夹具/故障类别，修复后没有再做真实推理。前后脚本摘要和测试结果分列03-evaluation.md，不修改旧轨迹或保存故障结论。
