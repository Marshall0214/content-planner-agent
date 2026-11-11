# 评估、实际证据与未完成项

最终复核日期：2026-11-11（Asia/Shanghai）。**按原题最低要求，当前场景材料及两条真实反馈调整记录具备，建议带限制说明提交。** 生成故障实际返回后模型同报价重试成功，可作为有限制的工具失败/调整证据；请求键类别提示使当轮附加盲测条件不通过，该历史结论和原始记录不改。预算停止保留中途不合理动作及质量缺陷；旧保存故障仍未触发SAVE_TEMPORARY、场景未通过。内容审阅C1–C4已由用户接受，编辑附录不冒充原模型输出。没有判定所有附加实验或所有能力通过。[最终交付核对](07-final-delivery.md)、[最终机器评估](../examples/test-results/final-delivery-assessment.json)、[最新材料索引](../examples/test-results/p0-acceptance-materials-index.json)。

## 最终口径：最低要求、附加条件与质量分开

原题要求实际工具反馈进入下一次真实模型请求并影响后续动作；允许本地工具/Mock、真实模型停止，以及有界未完成。原题没有把无预提示盲测、必须触发SAVE_TEMPORARY、所有失败场景最终保存或三小时完成列为硬门槛。它们分别属于实验条件、选定故障夹具或工时建议，不应扩成新的否决条件。

现有两类路径：①预算工具OVER_BUDGET→真实上下文→被拒生成→模型据实际8/预算3/缺口5停止；②实际GENERATION_TEMPORARY→原call_id完整回传→模型同报价重试成功，前置搜索、失败尝试、账本和540模拟秒保留。第二条有请求键提示，不能证明盲测或排除预期影响，但API动作由真实模型产生，实际失败/观察/恢复没有因此消失；可按原题作为带局限的证据。此为2026-11-11的交付适用性判断，不把历史`qualified=false`改成盲测通过。

正常及同输入零增量重放、缺预算/期限入口、超预算和生成故障材料已覆盖，至少三组材料齐备；用户接受C1–C4。最低要求核对支持提交，技术结论不代替外部考官打分，也不声称模型每一步都正确。预算后错误生成、无效降本建议、参数遗漏、保存恢复未验证和随机键修正版未在线验证均保留，详见07-final-delivery.md。

本轮只读材料复核与文档收尾，未新增模型、业务运行或测试。历史累计39次，最新150项JUnit记录18.391秒；实际用时已由用户于2026-11-11确认：不到6小时；未提供精确分钟/分项计时，不能把HTTP计时277.502秒或日志跨度当开发用时。旧实验章节的日期、待审状态、未达标结论按当时条件保留；当前内容确认以06-content-review.md为准，当前提交适用性以本节/07为准。原始输出和实验JSON不覆盖，聚合材料索引的本轮判断另列，并保存修改前版本。

此前上下文修复相关回归 **64通过**：[JUnit](../examples/test-results/context-latest-targeted-final.xml)、[控制台](../examples/test-results/context-latest-targeted-final.txt)；全套 **122通过、0失败、0错误、0跳过**：[JUnit](../examples/test-results/context-latest-full.xml)、[控制台](../examples/test-results/context-latest-full.txt)。新增3项SDK协议测试，覆盖两种provider配置及非适配器消息保护，均无模型推理。此前检索契约轮相关46项记录：[JUnit](../examples/test-results/retrieval-contract-targeted.xml)、[控制台](../examples/test-results/retrieval-contract-targeted.txt)；此前完整套件 **119通过、0失败、0错误、0跳过**：[JUnit](../examples/test-results/retrieval-contract-full.xml)、[控制台](../examples/test-results/retrieval-contract-full.txt)。该轮新增13项检索/硬要求测试及1项10次请求上限测试，无真实推理。实际Python/锁定依赖沿用：[环境](../examples/test-results/environment.json)。

历史阶段记录均保留：初版[65项](../examples/test-results/final.xml)，UNKNOWN修复[73项](../examples/test-results/unknown-replay-full.xml)，7B接入[87项](../examples/test-results/qwen-full-retry.xml)，27B尝试[91项](../examples/test-results/qwen27-full.xml)，Schema内联[105项](../examples/test-results/schema-inline-full.xml)。失败历史另见下文，不覆盖旧记录。

L1/L2和SDK HTTP替身不属于L3。本地真实请求累计39次（7B3、27B基线3、Schema对照3、旧正常6、新正常7、双专项11、独立生成故障6）。第15次未返回usage，完整累计token/实际模型费用未知。最新6次usage均取得；新轨迹确有GENERATION_TEMPORARY及合理重试，但盲测条件不满足，不能判第二类路径的全部验收条件已通过。

## 12组P0逐项状态

“通过”限于自动断言和实际离线入口，语义质量及真实决策另列。

| 用例 | 工程/离线结果 | 验证重点 | 在线材料与限制（截至最终复核） |
| --- | --- | --- | --- |
| C01 | 通过（2项关联测试；[JUnit](../examples/test-results/context-latest-full.xml)） | 正文、引用、三表保存与立即终结 | 已有真实draft修正/保存证据；用户接受C1–C4，原模型产物与编辑附录分列 |
| C02 | 通过（3项关联测试；[JUnit](../examples/test-results/context-latest-full.xml)） | 缺预算、零模型/业务调用 | 最新真实模式入口已记录NEEDS_INPUT，推理/工具/费用0，模型未初始化 |
| C03 | 通过（2项关联测试；[JUnit](../examples/test-results/context-latest-full.xml)） | 缺期限、零模型/业务调用 | 最新真实模式入口已记录NEEDS_INPUT，推理/工具/费用0，模型未初始化 |
| C04 | 通过（2项关联测试；[JUnit](../examples/test-results/context-latest-full.xml)） | 超限观察进入下一离线轮；可调整或停止 | 真实OVER_BUDGET→被拒生成→有依据停止可支持原题最低要求；中间错误动作和无效降本建议保留 |
| C05 | 通过（3项关联测试；[JUnit](../examples/test-results/context-latest-full.xml)） | 失败保留产物、复用与费用、失败尝试不抹掉 | 生成错误回传/模型重试可带限制说明用于原题；历史附加盲测仍不合格，原保存故障场景仍未通过 |
| C06 | 通过（2项关联测试；[JUnit](../examples/test-results/context-latest-full.xml)） | 跨CLI进程重放与冲突；真实提交输入与原绑定输入分开 | 已有真实完成请求同输入重放通过；在线冲突未另安排，离线断言保留 |
| C07 | 通过（1项关联测试；[JUnit](../examples/test-results/context-latest-full.xml)） | 新报价读最新账本时钟；同规格复用0增量 | 真实会话对应交叉核对（如适用）；不另伪造模型调用 |
| C08 | 通过（1项关联测试；[JUnit](../examples/test-results/context-latest-full.xml)） | 已花11+新basic6+保存1=18 | 真实会话对应交叉核对（如适用）；不另伪造模型调用 |
| C09 | 通过（3项关联测试；[JUnit](../examples/test-results/context-latest-full.xml)） | 360模拟+60真实推进=420；复用不加时；最新期限守卫 | 真实会话对应交叉核对（如适用）；不另伪造模型调用 |
| C10 | 通过（10项关联测试；[JUnit](../examples/test-results/context-latest-full.xml)） | 最后合法调用成功/失败/UNKNOWN与调用上限 | 真实会话对应交叉核对（如适用）；不另伪造模型调用 |
| C11 | 通过（12项关联测试；[JUnit](../examples/test-results/context-latest-full.xml)） | 假finish不成功；UNKNOWN冻结/重放/inspect一致、只读投影、责任保留及无旧写覆盖 | 真实会话对应交叉核对（如适用）；不另伪造模型调用 |
| C12 | 通过（18项关联测试；[JUnit](../examples/test-results/context-latest-full.xml)） | 输入、引用、有限硬需求和空正文/依赖校验 | 真实会话对应交叉核对（如适用）；不另伪造模型调用 |

全部测试名称、实际值失败信息见JUnit；测试源码位于tests/。其中时间/费用/事务用L1，循环/反馈与额度用L2。OpenAI适配器还通过实际已安装SDK加httpx.MockTransport的本地序列化与call_id回传测试；该测试不是在线模型验收。

README示例入口另有实际核对：[readme-commands.json](../examples/test-results/readme-commands.json)。

## 实际CLI材料

最新离线批次：[batch_cff97e13a98e.json](../examples/test-results/batch_cff97e13a98e.json)，14次实际offline_mock CLI执行，无真实模型调用；不与旧正常请求共用数据库，不把这些记录当L3。

| Case | 状态/保存 | 确认总额或最后可信 | 本次离线轮数 | 证据 |
| --- | --- | --- | --- | --- |
| C01 | COMPLETED/CONFIRMED | 8 | 5 | [output](../examples/runs/offline_mock/run_132a15beef1e44b3/output.json)、[Trace](../examples/runs/offline_mock/run_132a15beef1e44b3/trace.jsonl)、[报告](../examples/runs/offline_mock/run_132a15beef1e44b3/report.md) |
| C06 | COMPLETED/CONFIRMED | 8 | 0 | [output](../examples/runs/offline_mock/run_9e7dd85b0e9c4920/output.json)、[Trace](../examples/runs/offline_mock/run_9e7dd85b0e9c4920/trace.jsonl)、[报告](../examples/runs/offline_mock/run_9e7dd85b0e9c4920/report.md) |
| C06-conflict | FAILED/CONFIRMED | 8 | 0 | [output](../examples/runs/offline_mock/run_2cbb1a17dc4d4e52/output.json)、[Trace](../examples/runs/offline_mock/run_2cbb1a17dc4d4e52/trace.jsonl)、[报告](../examples/runs/offline_mock/run_2cbb1a17dc4d4e52/report.md) |
| C02 | NEEDS_INPUT/NOT_ATTEMPTED | 0 | 0 | [output](../examples/runs/offline_mock/run_2859fa01178946ca/output.json)、[Trace](../examples/runs/offline_mock/run_2859fa01178946ca/trace.jsonl)、[报告](../examples/runs/offline_mock/run_2859fa01178946ca/report.md) |
| C03 | NEEDS_INPUT/NOT_ATTEMPTED | 0 | 0 | [output](../examples/runs/offline_mock/run_78e02b5b87a345ab/output.json)、[Trace](../examples/runs/offline_mock/run_78e02b5b87a345ab/trace.jsonl)、[报告](../examples/runs/offline_mock/run_78e02b5b87a345ab/report.md) |
| C04 | INCOMPLETE/NOT_ATTEMPTED | 1 | 3 | [output](../examples/runs/offline_mock/run_363f35298a514995/output.json)、[Trace](../examples/runs/offline_mock/run_363f35298a514995/trace.jsonl)、[报告](../examples/runs/offline_mock/run_363f35298a514995/report.md) |
| C04-adjust | COMPLETED/CONFIRMED | 8 | 6 | [output](../examples/runs/offline_mock/run_4895d0ce0850442c/output.json)、[Trace](../examples/runs/offline_mock/run_4895d0ce0850442c/trace.jsonl)、[报告](../examples/runs/offline_mock/run_4895d0ce0850442c/report.md) |
| C05 | COMPLETED/CONFIRMED | 8 | 6 | [output](../examples/runs/offline_mock/run_a23eabdaad7d4b7b/output.json)、[Trace](../examples/runs/offline_mock/run_a23eabdaad7d4b7b/trace.jsonl)、[报告](../examples/runs/offline_mock/run_a23eabdaad7d4b7b/report.md) |
| C05-permanent | INCOMPLETE/FAILED | 7 | 6 | [output](../examples/runs/offline_mock/run_dbd9afc34b7a4d91/output.json)、[Trace](../examples/runs/offline_mock/run_dbd9afc34b7a4d91/trace.jsonl)、[报告](../examples/runs/offline_mock/run_dbd9afc34b7a4d91/report.md) |
| C10-success | COMPLETED/CONFIRMED | 8 | 5 | [output](../examples/runs/offline_mock/run_6dd4c2da3bb848a2/output.json)、[Trace](../examples/runs/offline_mock/run_6dd4c2da3bb848a2/trace.jsonl)、[报告](../examples/runs/offline_mock/run_6dd4c2da3bb848a2/report.md) |
| C10-failed | INCOMPLETE/FAILED | 7 | 5 | [output](../examples/runs/offline_mock/run_10b583ef067a4128/output.json)、[Trace](../examples/runs/offline_mock/run_10b583ef067a4128/trace.jsonl)、[报告](../examples/runs/offline_mock/run_10b583ef067a4128/report.md) |
| C10-unknown | INCOMPLETE/UNKNOWN | 未知（最后可信7） | 5 | [output](../examples/runs/offline_mock/run_0a40072535e448b2/output.json)、[Trace](../examples/runs/offline_mock/run_0a40072535e448b2/trace.jsonl)、[报告](../examples/runs/offline_mock/run_0a40072535e448b2/report.md) |
| C11-storage-first | INCOMPLETE/UNKNOWN | 未知（最后可信7） | 5 | [output](../examples/runs/offline_mock/run_fc09bf8565c0436e/output.json)、[Trace](../examples/runs/offline_mock/run_fc09bf8565c0436e/trace.jsonl)、[报告](../examples/runs/offline_mock/run_fc09bf8565c0436e/report.md) |
| C11-storage-replay | INCOMPLETE/UNKNOWN | 未知（最后可信7） | 0 | [output](../examples/runs/offline_mock/run_cba626fe44f74c27/output.json)、[Trace](../examples/runs/offline_mock/run_cba626fe44f74c27/trace.jsonl)、[报告](../examples/runs/offline_mock/run_cba626fe44f74c27/report.md) |

UNKNOWN重放与inspect仍保持null总额/最后可信7/待确认最高1 unit及60模拟秒/termination_persisted=false，数据库未改：[inspect](../examples/test-results/batch_cff97e13a98e_unknown_inspect.json)。

当前14份离线metadata和SDK录制比较的source_digest核对为 `1157ad49e78e8b80330e9c918fd20eaa9c7b3ab88a42359986be1ab6e384bee5`，覆盖src/content_planner/*.py、data/*.json、pyproject.toml、uv.lock。旧[检索契约批次](../examples/test-results/batch_c03aafe8d9f8.json)、旧真实正常Trace及更早记录保留，不能将其旧实现摘要覆盖为当前摘要。
## UNKNOWN重放回归

根因：首次保存结果事务失败时，应用只返回内存UNKNOWN；数据库中可仍是RUNNING/NOT_ATTEMPTED快照及STARTED操作。旧的已有请求分支只读快照，没有读取未确认操作，报告将最后可信7误当当前确定总额，并丢失待确认保存责任。

修复：已有请求绑定走只读分支；Store联读快照及STARTED/UNKNOWN操作身份，Agent重放、inspect和export共用保守内存投影。保存未确认继续UNKNOWN、当前金额null，保留成功脚本与最后可信账本。责任来自持久化的接纳元数据或旧尝试所引用的不可变报价，信息缺失就为null。仅投影终态标明未持久化，不写旧快照，不查询回执、不启动恢复。

| 验证层级 | 实际结果 | 断言/证据 |
| --- | --- | --- |
| L1/L2修复前复现 | 6失败 | [JUnit](../examples/test-results/unknown-replay-before.xml)、[控制台](../examples/test-results/unknown-replay-before.txt)；错误表现为未识别UNKNOWN。后续新增非保存分支，新增回归总计8项。 |
| L1/L2修复后针对性 | 20通过 | tests/test_unknown_replay.py的8项，加原幂等/保存和CLI测试；临时独立SQLite注入真实写入异常，完整经过首次内存UNKNOWN再同键重放。 |
| L1/L2只读与责任 | 通过 | STARTED/UNKNOWN操作、接纳元数据与旧报价兼容、缺元数据不猜价、非保存未知不伪造保存UNKNOWN；SQL跟踪仅SELECT，total_changes及逻辑转储不变，模型工厂/工具入口禁止触发。 |
| L1/L2保留边界 | 通过 | 正常重放、请求冲突、事务回滚、保存COMMIT成功但确认丢失原测试保留；最后一种首次观察不追加查证，之后普通同键读到已确认提交时返回原方案/回执，总计8且新增调用/费用0。 |
| 离线CLI | 14次实际run，另inspect/export核对通过 | 本节新批次及unknown_replay_checks；正常重放仍同一方案/回执，UNKNOWN重放与inspect一致。 |
| UNKNOWN修复阶段L3 | 当时未运行 | 该阶段用户禁止真实调用；后续本地Qwen3次冒烟见下文，仍不以离线记录证明真实决策。 |

复现和修复结果均来自实际执行，不属于设计预期；P1自动对账、恢复、续跑继续未实现。
## 失败历史与修正

| 记录 | 当时结果 | 处理 |
| --- | --- | --- |
| [initial.xml](../examples/test-results/initial.xml) | 3通过、51启动错误 | 默认临时目录无写权限，改为项目.cache/pytest。 |
| [retry.xml](../examples/test-results/retry.xml) | 51通过、3失败 | 报价先后不能依赖JSON字典顺序，改sequence。 |
| [ordering-fix.xml](../examples/test-results/ordering-fix.xml) | 54通过 | 保留该阶段记录；后续增加关键边界和SDK序列化测试。 |
| [environment-initial.json](../examples/test-results/environment-initial.json) | 依赖检查退出2 | uv默认缓存不可写；设置项目内cache/temp后environment.json检查退出0。 |
| [qwen-full-final.xml](../examples/test-results/qwen-full-final.xml) | 86通过、1失败 | 一次CLI重放子进程stdout为空，原辅助函数未暴露stderr，根因未定位。补退出码/stderr诊断后，[针对性4项通过](../examples/test-results/qwen-cli-diagnostic.xml)，[完整87项通过](../examples/test-results/qwen-full-retry.xml)；不将复查通过写成根因已修复。 |

首轮接入的[44项协议回归](../examples/test-results/qwen-protocol.xml)和[85项完整测试](../examples/test-results/qwen-full.xml)保留为历史。

没有删除失败记录，也未将环境错误算业务通过。初始venv/依赖下载及重装临时目录错误的过程记录于复盘。最新122项完整测试通过；原UNKNOWN修复新增8项，7B轮新增14项本地配置/原生协议/实验门禁测试，27B轮另增4项thinking/脱敏测试，Schema轮另增14项Schema适配与参数回归，检索轮另增14项检索/上限回归，本轮另增3项状态所有权/原生续接SDK测试。修复前6项失败与此前批次仍保留，最新批次的source_digest已核对当前应用代码。完整业务效果仍未验证。

## 7B真实冒烟历史与未开展的验收

| 检查项 | 实际事实与证据 |
| --- | --- |
| 服务/地址 | Ollama 0.40.9，http://127.0.0.1:11434；匿名GET模型列表成功，Responses/Chat空请求返回400而不是404。无新增模型下载或部署。 |
| 实际选用模型 | qwen2.5:7b，7.6B、Q4_K_M，digest为845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e；能力completion/tools、非remote模型。这是首轮7B阶段记录；后续27B尝试见末节。 |
| 协议 | 原生无状态POST /v1/responses。沿用SDK完整历史回传、function_call/call_id/function_call_output；不使用previous_response_id，不采用JSON动作替代原生调用。 |
| 鉴权 | 本地无需云端密钥，实际SDK发送非秘密占位值且HTTP成功；请求头不入证据。 |
| 参数/上限 | temperature=0.2，max_output_tokens=4000，SDK自动重试0；实际推理最多3次、每次20秒、任务180秒，工具10次/模型12次保护保留。没有调整或取消超时。 |
| 运行环境 | 实查RTX 4090 D、24,564 MiB显存；冒烟后模型在GPU加载，context_length=32768。硬件/服务事实见[检查记录](../examples/test-results/qwen-service-check.json)。 |

官方查阅日期2026-11-10：[Ollama Responses/Chat协议](https://docs.ollama.com/api/openai-compatibility)、[原生工具往返](https://docs.ollama.com/capabilities/tool-calling)、[本地鉴权](https://docs.ollama.com/api/authentication)。官方资料说明API能力；本地实测只证明本轮记录中的行为，不据此宣称完整业务兼容。

启动脚本先发生Store不支持with的TypeError，**推理0次**，已改用contextlib.closing并保留[启动失败记录](../examples/test-results/qwen_smoke_36af94f620be.json)。随后正式冒烟只用了3次，全部HTTP 200：[实际请求与结果索引](../examples/test-results/qwen_smoke_7a495877ab1f.json)。

| 请求 | 实际输出/执行观察 | HTTP往返耗时 | usage输入/输出token |
| --- | --- | --- | --- |
| 1 | 无原生调用且assistant文本为空，记录PROTOCOL_ERROR；空文本在第二次实际发送的历史中可核对，不能凭usage推测被省略的内容。 | 9.187秒 | 1556 / 82 |
| 2 | 原生search_materials，call_v8zda8n5；缺decision_summary，执行器返回REJECTED/INVALID_ARGUMENT，未启动收费执行。 | 0.422秒 | 1911 / 62 |
| 3 | 请求中包含上轮原生function_call_output及其call_id，结果与实际拒绝完全一致；模型选择estimate_plan，但缺quote_id且decision_summary=null，再遭Schema拒绝。其mat_12345等ID也不在素材目录中，不过本次首先触发的是参数Schema错误。 | 0.765秒 | 3505 / 100 |

usage合计输入6972、输出244、总计7216 token，为服务实际返回值，不是性能基准。真实推理现金成本/电费未测，未知；模拟业务新增收费0。第三次合法请求结束后严格REAL_CALL_LIMIT退出，没有第四次调用。最终INCOMPLETE、保存NOT_ATTEMPTED、无方案回执；[实际输出](../examples/runs/real/run_cb8b87f85a2c4600/output.json)、[Trace](../examples/runs/real/run_cb8b87f85a2c4600/trace.jsonl)、[模型/端点/参数/源码摘要](../examples/runs/real/run_cb8b87f85a2c4600/metadata.json)、[报告](../examples/runs/real/run_cb8b87f85a2c4600/report.md)。

**判定：冒烟失败。** 已看到真实原生调用及实际拒绝观察回传；成功执行业务工具0次，反馈后也未给出有效下一步，不能算工具闭环通过。三次均无鉴权、连接或超时错误；模型上下文实查32768、最大输入3505，现有观察不支持上下文窗口不足的解释。服务端是否完整解释本项目Schema与模型是否遵循契约尚未隔离，不能靠推理文字断言根因。

7B阶段拟议验证（当时待运行，后续基线与Schema对照见后文）：固定同模型/同端点，先对一个原生search工具检查完整必填参数和call_id往返；再只改变Schema表示或提示说明之一作对照，保留实际返回。先用离线协议测试核对发送参数；新冒烟仍限3次。任一参数链路不通即停止，不直接扩大验收、不放宽校验、不替模型补参数、不自动换模型。保持成功/失败状态真实性。

| 真实验收项 | 当前结论 | 停止条件/后续必要证据 |
| --- | --- | --- |
| 正常生成并确认保存 | 未运行（本轮仅限Schema对照） | 本轮不开展正式验收；后续须有实际保存确认和可审阅产物。 |
| 第一类：超预算反馈后的调整或有依据停止 | 未取得，合格0条 | 本轮没有有效估价/超限反馈；不能将参数错误或离线12→8算证据。 |
| 第二类：工具失败/部分成功后的有效选择 | 未取得，合格0条 | 仅有参数拒绝回传且后续仍非法，无成功结果可保留，不能冒充已取得故障路径。 |
| 完成请求重放：零推理、零收费、同回执 | 在线未运行；L1/L2通过 | 必须先有真实完成请求；不能用两个null回执相同算通过。 |
| 缺预算/期限不调用模型 | 在线批次未运行；入口L1/L2通过 | 后续验收批次保留真实入口记录并核对实际POST增量0。 |
| 人工内容审阅 | 未进行、待审 | 未产生方案/脚本；AI仅核对技术参数与状态，不能冒充用户或运营人员已审阅。 |
| 整体P0 | **未达标** | 缺正常真实完成、两类合格动态路径及必要真实场景证据。 |

验收脚本已设独立批次上限30次、每请求至多10次，另受默认模型12/工具10/180秒约束；必须提供同模型/端点通过的冒烟索引。**到本次Schema对照结束仍未运行该分支，额度消耗0/30，不宣称验收脚本已在线验证。** 用户本轮要求对照结束停止，不能因窄Schema条件通过就自动扩大实验。所有已有尝试和历史记录保留，P1查证/恢复/续跑未增加，未推送远程仓库。

## 27B原始Schema基线（实际执行，保留）

用户授权尝试已安装的qwen3.5:27b。Ollama仍为0.40.9，本次选用27.8B/Q4_K_M；能力包含tools/thinking，实查thinking.values=[false,true]、默认true。显式请求think=false，温度0.2、输出上限4000，SDK重试0；单次20秒、总180秒及3次真实请求上限保持。关闭thinking是本次另一项配置差异，不宣称只比较模型规模。[服务/实际解析器检查](../examples/test-results/qwen27-service-20261110T074748Z.json)、[官方thinking说明](https://docs.ollama.com/capabilities/thinking)（2026-11-10查阅）。

| 请求 | 实际动作及观察 | HTTP耗时 | usage输入/输出token |
| --- | --- | --- | --- |
| 1 | 原生search_materials，字段含decision_summary；filters却是JSON字符串，INVALID_ARGUMENT拒绝。 | 13.688秒 | 2086 / 108 |
| 2 | 上轮真实拒绝通过function_call_output/call_id回传。模型选择修正后重试，filters仍为字符串，再次拒绝。 | 3.000秒 | 3743 / 108 |
| 3 | 再次看到实际反馈，模型选择再试；filters类型仍未纠正，第三次拒绝。 | 3.188秒 | 6304 / 102 |

三次HTTP均200、reasoning_tokens均0；usage合计输入12133、输出318、总计12451 token。加载后context_length=32768、size_vram=18254670067字节，无超时，因此未放宽上限。[批次/实际发出参数](../examples/test-results/qwen_smoke_6c1a2138f50b.json)、[实际输出](../examples/runs/real/run_82577c0b86c84fae/output.json)、[Trace](../examples/runs/real/run_82577c0b86c84fae/trace.jsonl)、[metadata](../examples/runs/real/run_82577c0b86c84fae/metadata.json)。

**27B冒烟仍失败。** 原生调用与简短依据比首轮完整，但三次都被参数校验拒绝，成功业务执行0、模拟收费0、保存NOT_ATTEMPTED。最终INCOMPLETE/REAL_CALL_LIMIT，无第四次调用、无自动换协议、无自动补参数、无后续验收；两类合格动态路径仍0条。没有方案供内容运营人员人工审阅，整体P0仍未达标。本项目累计真实推理6次，本次仅新增3次。

已收敛的兼容风险（区分事实与推断）：实际发出的filters Schema只有`$ref: #/$defs/SearchFilters`，未内联type。相同v0.40.9官方代码中，[Qwen35委托Qwen3Coder解析](https://github.com/ollama/ollama/blob/v0.40.9/model/parsers/qwen35.go)，[ToolProperty不包含$ref字段](https://github.com/ollama/ollama/blob/v0.40.9/api/types.go)，[解析器按type/anyOf转换参数，缺类型时保留字符串](https://github.com/ollama/ollama/blob/v0.40.9/model/parsers/qwen3coder.go)。本机实查启用qwen3.5解析器，这与观察一致，**是强兼容性嫌疑，尚无修复后在线对照，不能宣称已证实唯一根因**。不能仅据此判定27B本身不具备工具能力。

最小下一步：只在发送给Ollama的工具Schema中内联本地$ref，覆盖filters/new_spec/draft及嵌套数组；保留Pydantic业务校验、错误/预算/费用规则，不解码或代填非法参数。先做离线协议验证，再用新的最多3次真实请求检查filters对象和观察往返。这是基线阶段的待办；下节已实施出站适配和3次对照，仍未增加P1。

本轮仅新增MODEL_THINK布尔配置与脚本--no-think；证据省略reasoning项，实际发送历史不变，工具动作/ID/观察保持原样。相关27项、完整91项测试通过：[汇总](../examples/test-results/qwen27-evaluation.json)。历史失败记录保留，无远程推送。

## Schema内联受限真实对照（历史保留）

只改变Ollama出站工具Schema：深拷贝后递归内联本地JSON Pointer；filters、nullable new_spec、draft与campaign_tasks.items展开，required/nullable/enum/长度/数值/additionalProperties保留。根定义注册表检查后移除；引用同层约束冲突通过allOf保留，实例数据enum/const不当Schema解释。缺失、外部或循环引用在SDK请求和模型计数前报配置错误。原Pydantic、云端出站和业务规则未改，不解码字符串filters、不代填参数。

离线实际SDK测试证明：filters为object，new_spec保持object/null，draft及数组完整展开、无未解析Schema引用；云端和原定义不变；非法字符串拒绝且0费、合法对象可执行、原call_id观察回传。相关41项、全套105项实际通过；离线不作为Ollama兼容性通过证据。

[预检](../examples/test-results/schema-inline-20261110T083648Z-preflight.json)、[基线实际Schema](../examples/test-results/schema-inline-20261110T083648Z-before.json)、[转换后Schema](../examples/test-results/schema-inline-20261110T083648Z-after.json)、[自动生成diff](../examples/test-results/schema-inline-20261110T083648Z.diff)。原始Schema摘要 `71e67fbe7543deac679f8ae06c2c10d86fd3ab5d9f0c1b02f89ad1b6ad8eff0c`；内联后 `5a1a55e6488208826721abe03b3fddae296f78e0835f771340b505957516509f`，三次实际SDK出站均与预检一致。旧失败基线原样保留，没有重复消耗调用。

固定qwen3.5:27b及模型摘要、Ollama0.40.9、think=false、temperature0.2、4000输出、20秒单次/180秒总限、SDK重试0、原主题/预算10/偏好/资料/费用/工具/校验。比较实际首轮请求，除tools外所有推理字段一致，初始上下文仅request_key、deadline_at、clock_now_utc变化；精确前后值见[对照索引](../examples/test-results/schema-inline-comparison.json)。后续上下文按真实观察自然分化，没有预写动作。

| 请求 | 参数类型与实际结果 | HTTP耗时 | usage输入/输出token | 模拟收费 |
| --- | --- | --- | --- | --- |
| 1 | search_materials.filters=object，校验通过并实际成功；匹配0条。 | 7.937秒 | 1756 / 108 | 1 |
| 2 | 第一次SUCCESS完整观察以原call_s44y3r9r进入本次请求。estimate_plan.new_spec=object，quote_id/script_artifact_id=null；material_ids=[]违反minItems=1，被INVALID_ARGUMENT拒绝，无有效估价。 | 3.641秒 | 3491 / 142 | 0 |
| 3 | 看到真实估价拒绝，模型改查询；filters仍为object，检索实际成功、匹配0条。 | 3.016秒 | 6221 / 95 | 1 |

usage实际合计输入11468、输出345、总计11813 token，reasoning_tokens均0。新增推理3次、27B累计6次、项目累计9次；本请求模拟费用合计2。无现金/电费测量，不报价。[完整实际请求](../examples/test-results/qwen_smoke_ba6a52fb9947.json)、[输出](../examples/runs/real/run_aa39d02ee392400f/output.json)、[Trace](../examples/runs/real/run_aa39d02ee392400f/trace.jsonl)、[metadata](../examples/runs/real/run_aa39d02ee392400f/metadata.json)。最后一次检索结果保留在报告中，因3次额度耗尽未发第四次模型请求。

**本轮指定的Schema冒烟条件通过：** 嵌套filters对象通过校验；业务检索实际成功；成功观察进入下一轮实际请求且call_id一致。检索均无命中，不是活动方案成功。new_spec类型观察到改善，但有效候选/估价未通过；draft/campaign_tasks只完成离线出站验证，未在真实模型中调用。不能宣称全部复杂参数或两类业务动态路径通过。

最终任务INCOMPLETE/REAL_CALL_LIMIT、保存NOT_ATTEMPTED，未生成脚本或可审阅完整方案，人工内容审阅仍未进行，整体P0未达标。用户仅授权对照，结束后停止，正式验收未运行。结果支持“观察到改善”，不证明$ref处理是所有基线失败的唯一根因：只有一轮受限对照，绝对时钟/请求身份改变，模型采样与运行状态也未做重复控制。不得据耗时变化宣称性能提升。

## 检索契约完善与受限正常链路（历史真实记录保留）

query保持按空白分词、任一词作不区分大小写子串匹配；tags保持全部精确匹配（AND），[]不滤标签。allowed_usage只在null时不限，非null精确匹配，空字符串不再因旧truthy判断误作不限。语义词放query，不能假定为目录标签。仅新增Field/工具描述及模型规则，不放宽Pydantic、Schema内联、预算/时间/账本/幂等/UNKNOWN。

feedback包含applied_filters、filter_semantics、keyword_match_count、filtered_match_count（limit前）、returned_count、catalog_available_tags、unrecognized_tags、catalog_available_usage_scopes、unrecognized_allowed_usage、empty_reason与next_action_hint。可用值从实际目录计算，不伪造标签；空结果区分无关键词命中和过滤排空。后台不自动改query/清空tags/AND转OR，后续选择仍由模型作出；空material_ids估价仍拒绝。硬过滤不放宽，现有P0无法核验的硬要求保留原文并在模型前NEEDS_INPUT澄清，未增加通用配置能力。

| 离线核对 | 实际结果 | 证据/费用 |
| --- | --- | --- |
| 两条历史查询+原tags | 均关键词3、过滤0、返回0 | [实际直接工具审计](../examples/test-results/retrieval-filter-audit.json)，每次空结果实际收费1/60模拟秒。 |
| 同查询+空tags/null usage | 均3条 | 同审计，每次新动作收费1；不是后台自动重查。 |
| 有效标签/组合 | 照片2条、毕业季AND照片1条、校园AND创意0条 | JUnit断言AND未改OR；标签提示均来自当前目录。 |
| usage精确及资料外查询 | null/demo_only为3；DEMO_ONLY/空串为0；资料外关键词始终0 | 均执行检索并按费表收费，无自动兜底素材。 |
| 空素材估价/成功复用/硬要求 | 空估价拒绝0费，保留此前检索费用；成功检索复用0费/0模拟耗时；不支持硬过滤0模型调用并请求澄清 | 相关46项、完整119项通过；确定性工具/离线流程，不是L3。 |

本轮真实执行`validate_qwen.py normal`，只一条正常请求，上限10次，完成时才原样重放。实际模型/摘要、Ollama0.40.9保持，think=false、temperature0.2、输出4000、SDK重试0，单次20秒/总180秒/工具10次不变，新请求键与未来期限见[实际输入](../examples/runs/real/run_ed510c6504484805/input.json)。[预检](../examples/test-results/retrieval-normal-preflight.json)、[完整真实请求/错误](../examples/test-results/qwen_normal_0f1745fd4b32.json)。没有启动30次验收批次。

| 请求 | 真实模型动作/程序结果 | HTTP耗时 | usage输入/输出token | 实际工具费 |
| --- | --- | --- | --- | --- |
| 1 | 模型选tags=[]/usage=null，但limit=10超过原上限5；INVALID_ARGUMENT拒绝，未执行检索。 | 7.922秒 | 2031 / 115 | 0 |
| 2 | 看到拒绝后模型自行改limit=5；实际检索命中mat-001/002/003三份，反馈计数3/3/3。 | 2.844秒 | 3665 / 106 | 1 |
| 3 | 引用真实命中ID提交basic候选，有效pre_generation估价FEASIBLE。 | 6.703秒 | 8302 / 236 | 0 |
| 4 | 模型引用真实quote_id生成脚本，正文/素材引用已保留。 | 4.578秒 | 15840 / 81 | 6 |
| 5 | 模型引用原候选与真实脚本进行最新post_generation复估，I=7、R=1、预计总计8。 | 6.688秒 | 25330 / 127 | 0 |
| 6 | 最新复估后继续推理，20秒ReadTimeout，未收到响应/工具动作/draft。 | 20.000秒 | 未知 / 未知 | 未启动工具 |

新增真实请求6/10，剩余4次未使用；项目累计15次、27B累计12次真实请求。前5次已知usage输入55168、输出665、合计55833 token；第6次usage未知，**本轮完整总usage及完整累计usage不可确定**，不能以0补齐。HTTP请求耗时合计48.735秒，含失败20秒，不当作独立测量的整任务墙钟或吞吐基准。

已发生模拟费用7=实际成功检索1+生成6；首个动作属于参数拒绝，不是免费空检索。已有两份估价均0费，最新报价8=已花7+尚未执行保存1，不能把报价8记作已扣费。脚本和费用保留，不退款、不清零。真实模型部署现金/电费未知未测。

最终INCOMPLETE/MODEL_UNAVAILABLE（APITimeoutError），save_state=NOT_ATTEMPTED，未调用保存工具，故没有保存副作用不确定性，不误标RESULT_UNKNOWN。未取得在线draft，draft/campaign_tasks尚未验证；保存、正常完成及完成后重放均未通过/未运行。未为了用完额度重试、新建正常请求或续跑；本轮不安排两类正式动态验收，不把参数修正算作完成该验收。[实际输出](../examples/runs/real/run_ed510c6504484805/output.json)、[Trace](../examples/runs/real/run_ed510c6504484805/trace.jsonl)、[正文/费用报告](../examples/runs/real/run_ed510c6504484805/report.md)、[总索引](../examples/test-results/retrieval-normal-evaluation.json)。

已确认的直接故障是第6次HTTP读超时。第5次provider报告输入25330 token；失败请求没有输入token统计。该次服务启动日志出现32768上下文配置，[只读日志摘录](../examples/test-results/retrieval-normal-server-diagnostics.json)中的启动等待状态不是第6次根因证据；不能把上下文增长、截断或draft生成时长推断写成已证实原因。未修改20/180秒上限。后续需在新授权下隔离正常链路时延，再完成draft/保存/原样重放，之后才进行预算和工具故障两类业务验收。

技术核对确认脚本正文非空、引用来自实际目录；内容运营/用户人工审阅尚未进行。仍无完整可审阅活动方案，整体P0未达标。未加入P1、未推送远程仓库。

## 历史：最新状态快照修复（该轮仅离线）

直接缺陷是适配器把Agent每轮完整累计状态追加为新user消息，使第6次请求包含6份状态快照，前5份过时。本轮仅修改model.py的适配器组织方式：用私有对象引用记录自己创建的消息，后续按`is`身份移除该对象，创建最新消息放input首位。原生function_call、原参数/call_id、function_call_output及供应商续接对象相对顺序不变；不按角色/任意关键词/相似JSON筛历史，非适配器消息即便内容相同也保留。

最新context整份保留，包含原需求/硬约束、当前费用与账本版本、候选/报价/成功产物、实际观察及剩余额度。没有模型摘要替代观察、没有draft代填或代码选择保存。Agent数据库快照、完整Trace、模型/Schema/提示词/业务/费用/幂等/UNKNOWN及执行额度规则均未改；SDK每次20秒、脚本整次180秒未调整。

新增SDK MockTransport测试覆盖openai/ollama：六轮始终仅一份自身最新消息；费用/最新引用/硬约束仍可见；参数拒绝、失败以及脚本成功后保存失败的部分结果完整回传；原call_id和不透明供应商续接数据保留；输入对象和先前捕获请求不被改写；耗尽调用额度后不发请求/不更新状态。另验证相同JSON的非适配器user消息不被误删。相关64项、完整122项实际通过，均为离线协议/流程验证。

已实际执行离线命令：

```powershell
.\.venv\Scripts\python.exe scripts/compare_model_context.py --recording examples/test-results/qwen_normal_0f1745fd4b32.json
```

它只用已录制Trace中的六份context、前五次实际供应商输出和工具观察，构造SDK MockTransport回复并捕获新请求。末轮模拟录制的ReadTimeout，未向任何模型服务请求、未等待新的真实超时、未调用Planner或业务工具、未建立/续跑任务。SDK MockTransport的六次请求不算新增真实推理，录制usage不当成本轮新usage。

| 录制请求 | 状态消息前→后 | 全部消息前→后 | 重序列化字符数前→后 | UTF-8字节前→后 |
| --- | --- | --- | --- | --- |
| 1 | 1→1 | 1→1 | 7,243→7,243 | 8,447→8,447 |
| 2 | 2→1 | 4→3 | 11,803→10,714 | 13,319→12,178 |
| 3 | 3→1 | 7→5 | 24,230→19,717 | 27,264→22,517 |
| 4 | 4→1 | 10→7 | 42,443→27,856 | 47,477→31,524 |
| 5 | 5→1 | 13→9 | 64,224→33,510 | 73,862→40,114 |
| 6 | 6→1 | 16→11 | 90,927→39,889 | 104,487→46,581 |

[实际比较/指标定义](../examples/test-results/context_replay_1ddfc0adb7cd/comparison.json)、[第6次实际SDK离线请求体](../examples/test-results/context_replay_1ddfc0adb7cd/request_06_after.json)。前后都用canonical()的compact JSON、sorted keys、ensure_ascii=false、UTF-8重新序列化；历史原始网络字节未保存。**字符/字节只代表统一规则下的请求体积，不是token、时延或性能测量。** 没有新token或模型效果数据。

每一轮SDK请求除input外与对应录制请求逐项相等，Schema/推理参数/timeout未改；剔除明确来源的旧快照后，所有其他原生项逐项相等。最新第6轮费用7/账本版本2、候选1、报价2（最新post_generation预计总计8）、成功脚本引用及剩余模型/工具额度原样保留。真实观察仍完整存在于原生输出中，未用摘要替代；该处剩余重复事实也没有继续压缩。

旧请求保护：[事前哈希](../examples/test-results/context-history-preservation-before.json)、[事后只读核对](../examples/test-results/context-history-preservation-after.json)。旧正常录制索引、完整Trace/输入/输出/产物等和SQLite共11个文件哈希一致；数据库仍INCOMPLETE/NOT_ATTEMPTED，已发生费用7、脚本ID与正文保留，不退款、不重置，不移入新任务。历史第6次直接故障仍是20秒ReadTimeout；本次体积改善不证明旧上下文超限、超时已解决或唯一根因成立。

| 当前验收项 | 状态 |
| --- | --- |
| 本轮真实推理 | 0；累计仍15，未连接Ollama做推理 |
| 新版在线上下文/供应商兼容 | 未运行；不能用SDK MockTransport通过代替 |
| 正常draft/保存与完成后重放 | 未验证；旧任务保持未完成 |
| 两类正式动态业务路径 | 未安排；正常链路完成后再安排 |
| 内容运营人工审阅 | 未进行，尚无完整已保存方案 |
| 整体P0 | 未达标 |

下一轮在新的授权额度下，以新请求验证，以下命令**待运行，本轮未执行**；脚本自动生成新键/未来期限、最多10次真实请求、只一条normal链路，完成时才原样零新增重放：

```powershell
.\.venv\Scripts\python.exe scripts/validate_qwen.py normal --endpoint http://127.0.0.1:11434/v1 --model qwen3.5:27b --no-think
```

保留think=false、temperature0.2、输出4000。实验脚本自行构造Limits()，当前默认20秒单次/180秒整次；后续调整配置必须核对Limits构造、实际metadata/index.limits和request.timeout，不能只改MODEL_TIMEOUT_S/RUN_TIMEOUT_S环境变量就认为生效。旧未用额度不当作新授权，不续跑旧key、不免费复用旧任务产物。该轮停在离线结果，无P1或远程推送；此命令已在下面的新授权轮实际执行。

## 新授权正常真实链路（实际完成，2026-11-10 18:29–18:30 Asia/Shanghai）

用户新授权最多10次本地推理，失败和超时计入，项目起点15。实际只运行一次normal命令，没有修改提示词、Schema、工具、费用、模型参数、业务规则或超时，没有重试整条实验、续跑旧请求或运行acceptance阶段。实际预检Ollama **0.40.9**，模型 **qwen3.5:27b**，摘要`7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e`；原生无状态Responses端点为`http://127.0.0.1:11434/v1/responses`，不使用云端付费密钥。[事前实际预检](../examples/test-results/normal-latest-20261110T102828Z-preflight.json)。

实际执行的命令：

```powershell
.\.venv\Scripts\python.exe scripts/validate_qwen.py normal --endpoint http://127.0.0.1:11434/v1 --model qwen3.5:27b --no-think
```

新请求键`qwen_normal_5f38146a433d-normal`，开始记录2026-11-10T10:29:00.370284Z，期限2026-11-10T10:59:00.371285Z（开始时未来约30分钟）。除新键/期限外原始业务输入与旧基线一致；没有导入旧产物。模型参数think=false、temperature=0.2、max_output_tokens=4000；model/tool上限12/10，批次推理硬上限10，SDK重试0。metadata的20/180秒与7份实际SDK请求的connect/read/write/pool均20秒一致。本轮总索引的18项只读后验检查全部通过，不能替代内容或动态路径审阅。

| 推理 | 实际动作及结果 | HTTP耗时 | provider输入/输出token | 模拟新增费用 |
| --- | --- | --- | --- | --- |
| 1 | search_materials limit=10；INVALID_ARGUMENT/REJECTED，未执行。 | 8.000秒 | 2032 / 107 | 0 |
| 2 | 根据原call_id观察自行改limit=5，tags=[]/usage=null；实际命中mat-001/002/003，计数3/3/3。 | 2.938秒 | 3339 / 108 | 1 |
| 3 | 提交实际命中ID及basic候选，pre_generation FEASIBLE：I=1、R=7、预计8。 | 7.172秒 | 6705 / 253 | 0 |
| 4 | 引用真实报价生成script_11081981296d4284，正文/引用保留。 | 5.141秒 | 10493 / 87 | 6 |
| 5 | 同规格最新post_generation复估：I=7、R=1、预计8；没有重扣生成费。 | 7.156秒 | 13366 / 129 | 0 |
| 6 | 模型原生save_plan带draft对象及4个任务对象；缺draft.script_artifact_id，被校验拒绝，未执行保存。 | 17.516秒 | 16220 / 552 | 0 |
| 7 | 收到上次实际拒绝观察后，模型自行补齐该嵌套字段，再调用save_plan；SUCCESS/CONFIRMED，立即结束。 | 17.578秒 | 18346 / 506 | 1 |

每轮出站只有一份最新适配器状态，包含原始需求、当前账本/报价/产物/剩余额度；前6次工具观察在下一请求中以原call_id和完整原结果逐项核对一致。最后成功保存后不再请求模型。第6次非法参数没有代填，第7次draft来自实际模型响应；真实模式没有回退Mock。两次REJECTED尝试与5次实际业务执行均保留；参数纠正不是本轮额外安排的故障/部分成功专项验收。

最终 **COMPLETED / SAVED / CONFIRMED**，`plan_id=plan_a9e605003b944a3d`，保存回执非空，已持久化。费用8=检索1+生成6+保存1，三条账本记录；报价免费，成功脚本只生成一次。模拟工具时间360秒（60+240+60），与HTTP耗时分开。活动准备READY_FOR_REVIEW，实际营销活动NOT_STARTED。

确认保存后，脚本原样重放同一输入/键；原方案与非空回执逐项一致。新增推理0、工具请求0、实际业务执行0、模拟费用0，数据库逻辑转储未变。没有用两个空回执判断通过。[保存输出](../examples/runs/real/run_b307abb73de84313/output.json)、[可审阅报告/脚本](../examples/runs/real/run_b307abb73de84313/report.md)、[Trace](../examples/runs/real/run_b307abb73de84313/trace.jsonl)、[账本](../examples/runs/real/run_b307abb73de84313/ledger.json)、[回执](../examples/runs/real/run_b307abb73de84313/receipt.json)、[原样重放输出](../examples/runs/real/run_a76068d0afbb4ff9/output.json)。SQLite保留在`var/qwen_normal_5f38146a433d/planner.sqlite3`，原始输入也在该批次目录；examples已导出输入、产物、报告、Trace、账本、回执和metadata。

本轮新增 **7/10** 次，剩余3次未使用，项目累计 **22** 次（其中27B共19次）。本轮provider usage完整：输入 **70,501**、输出 **1,742**、总计 **72,243 token**。HTTP请求耗时合计 **65.501秒**；从批次记录到保存回执时间戳差66.731741秒，后者不是独立全进程计时。模型实际现金/电费未知未测；旧第15次失败usage仍未知，不能用0补齐或报告完整项目累计usage。[逐请求真实参数/响应/usage/timeout](../examples/test-results/qwen_normal_5f38146a433d.json)、[汇总及只读核对](../examples/test-results/normal-latest-evaluation.json)。

记录边界沿用现有记录器：请求为实际SDK解析后的完整JSON body及timeout；响应保留实际id/model/status/usage/error和原生工具调用/参数，工具观察另见完整Trace及后续请求。未保留原始HTTP响应字节与全部headers，不补造这些数据；不输出模型内部思维过程。本轮没有HTTP错误/超时，实际两次业务参数拒绝在Trace中完整保留。

### 与旧失败基线比较及限制

| 同一阶段指标（最新复估后的第6次推理） | 旧失败基线 | 本轮实际 |
| --- | --- | --- |
| 自身状态快照 / 全部消息 | 6 / 16 | 1 / 11 |
| compact JSON字符 / UTF-8字节 | 90,927 / 104,487 | 40,148 / 47,152 |
| HTTP结果 / 耗时 | ReadTimeout / 20.000秒 | draft原生工具调用 / 17.516秒 |
| provider输入 / 输出token | 未知 / 未知 | 16,220 / 552 |
| draft/保存 | 未收到/未尝试 | 先缺字段拒绝，下一次修正后确认保存 |

双方所有出站instructions/tools/模型参数与timeout核对一致。本轮执行实现摘要仍为`1157ad49e78e8b80330e9c918fd20eaa9c7b3ab88a42359986be1ab6e384bee5`，与此前122测试/14次离线CLI证据一致，源码关键文件哈希未变。旧11个文件（包括数据库）事前/事后哈希一致，仍INCOMPLETE、费用7、原脚本保留，新旧脚本ID不交叉，没有旧请求续跑或免费迁移。

体积使用相同canonical JSON规则重序列化，**不是原始wire字节、token估算或性能结论**。新请求键/期限、时钟/ID、真实生成内容、缓存和采样状态不同；单次链路观察到正常完成和较小上下文，不能证实旧超限、唯一根因、稳定时延或后续必定不超时。本轮未调整20/180秒，也不据此提出或执行超时扩容。

### 审阅与剩余验收

AI技术核对：方案非空且贴合主题；脚本正文、3份真实合成目录引用、4个无环依赖任务、模拟费用与回执齐全；未虚称活动执行。需运营人工审阅：T+0至T+3未给单位、受众/渠道可操作性、虚构工具表述、脚本重复句号等。没有改写已保存产物，AI核对不冒充用户/运营人员审阅。原始output的`real_model_decision_evidence=false`与metadata的requires_review是保守自动标记，不表示本次来自Mock，也不能自动提升为两类专项合格证据。

| 验收项 | 当前结论 |
| --- | --- |
| 新上下文真实协议、在线draft、保存 | 本轮实际通过；draft经历一次拒绝后由模型修正 |
| 确认保存后原样重放 | 实际通过；同一非空回执/方案，零新增副作用 |
| 超预算反馈后替代/调整/有依据停止 | 本轮未运行专项实验，待新授权 |
| 工具失败或部分成功后调整/保留成功结果 | 本轮未运行专项实验，不能用参数纠正冒充完成 |
| 缺预算/期限、冲突及其余P0边界 | 现有离线测试通过；本轮未新增真实会话交叉记录 |
| 至少三组材料及全部专项覆盖 | 历史尝试均保留，但尚不满足两类专项证据组合，需补全 |
| 内容运营人工审阅 | 未进行 |
| 整体P0 | 未达标 |

本轮结束于已授权正常链路与重放，不再消耗剩余3次；未启动30次批次、两类动态实验、P1或远程推送。后续只能在新额度授权后补缺失证据。

收尾检查实际通过：本地文档链接、文档diff格式、官方调研章节哈希、执行源码关键文件哈希、旧11个文件/数据库哈希及累计推理仍22次均符合预期。[检查结果](../examples/test-results/normal-latest-documentation-check.json)。

## 最新受限专项验收（2026-11-10 18:50–18:51 Asia/Shanghai）

本轮新授权20次，单专项10次，项目起点22；不沿用旧3次余额。只新增实验脚本specialties选择、20/10额度、正常证据引用和停止门禁及18项对应回归，未改任何src/data/依赖/模型参数/提示词/Schema/费用或业务Runtime，未加入P1。旧acceptance的normal不再是此次入口；本轮只执行一次specialties，模型自主决定动作，未代填draft/素材ID、拼接动作或启动离线模型。

### 脚本与离线门禁

实际脚本SHA256：`c80b823ee967cedab8e601f09ada89cd82313d130c0fe3f1ea943d48628ffe47`。源码摘要仍为`1157ad49e78e8b80330e9c918fd20eaa9c7b3ab88a42359986be1ab6e384bee5`，与正常链路一致。脚本摘要独立记录，不能把未含scripts的Runtime摘要当实验脚本版本。

normal_reference在创建客户端/数据库前，读取已有正常/重放索引及两个真实输出，核对相同非空方案/回执、全部重放检查、零增量、相同配置和冻结业务摘要；不重跑正常模型。specialties先记录缺预算/期限再依次budget、save_failure。Transport发请求前同时检查批次20/当前场景10，失败/超时也先记入额度，SDK重试仍0；达到终止/额度/时钟/UNKNOWN或自动不变量错误后不启动下一场景。没有自动重跑整场或接管旧终态。

| 验证层级 | 实际结果 | 证据 |
| --- | --- | --- |
| 确定性实验门禁测试（不发推理） | 22通过；比此前增加18项参数化实例 | [JUnit](../examples/test-results/specialties-guards.xml)、[控制台](../examples/test-results/specialties-guards.txt) |
| 全套L1/L2及SDK MockTransport回归 | 140通过、0失败/错误/跳过 | [JUnit](../examples/test-results/specialties-full.xml)、[控制台](../examples/test-results/specialties-full.txt) |
| 只读实际预检 | 版本0.40.9、qwen3.5:27b、模型摘要及业务摘要与正常证据一致；累计起点22 | [预检/冻结/历史哈希](../examples/test-results/specialties-preflight.json) |

门禁新增覆盖：specialties不包含normal、缺信息真实入口不初始化模型、空回执/缺少重放断言/错配置/源码改变/重放收费先拒绝、批次20与单场景10、超时计数及场景计数独立、上限/UNKNOWN/计费状态不变量触发停止。这些是离线程序证据，不能代替SAVE_TEMPORARY真实路径。12组核心测试此前链接保留；本轮完整140项也覆盖全部原有断言。

实际执行一次命令：

```powershell
.\.venv\Scripts\python.exe scripts/validate_qwen.py specialties --endpoint http://127.0.0.1:11434/v1 --model qwen3.5:27b --no-think --normal-index examples/test-results/qwen_normal_5f38146a433d.json
```

实际批次`qwen_specialties_9333a7268207`。每个输入新键、未来约30分钟截止；缺期限例按题意为null。模型/服务固定qwen3.5:27b/Ollama0.40.9、think=false、temperature0.2、4000输出，20秒单次、180秒单任务、模型/工具12/10，实际全部11次SDK请求的connect/read/write/pool均20秒。所有请求仅一份最新适配器状态，实际工具观察按原call_id完整回传；没有静默Mock。[原始请求/响应/timeout索引](../examples/test-results/qwen_specialties_9333a7268207.json)。

### 验收点到实际材料

完整机器可读索引含每例input/output/Trace/原始自动断言/额外后验检查/AI技术结论/用户人工结论：[p0-acceptance-materials-index.json](../examples/test-results/p0-acceptance-materials-index.json)。AI结论不代签用户，全部用户结论仍pending。

| 验收点 | 实际输入/输出/Trace | 自动断言与AI技术结论 | 本轮推理/费用 | 用户人工结论 |
| --- | --- | --- | --- | --- |
| 正常 | [输入](../examples/runs/real/run_b307abb73de84313/input.json) / [输出](../examples/runs/real/run_b307abb73de84313/output.json) / [Trace](../examples/runs/real/run_b307abb73de84313/trace.jsonl) | [原断言](../examples/runs/real/run_b307abb73de84313/assertions.json)；复用已确认保存与原正文，不重跑 | 0/0（历史7次、费用8） | 待审内容 |
| 重复执行 | [原输入](../examples/runs/real/run_a76068d0afbb4ff9/input.json) / [输出](../examples/runs/real/run_a76068d0afbb4ff9/output.json) / [Trace](../examples/runs/real/run_a76068d0afbb4ff9/trace.jsonl) | [重放检查](../examples/test-results/normal-latest-evaluation.json)；相同非空回执/方案，零新增推理/业务执行/费用，沿用证据 | 0/0 | 待确认 |
| 缺预算 | [输入](../examples/runs/real/run_ab6832e25f7a4a89/input.json) / [输出](../examples/runs/real/run_ab6832e25f7a4a89/output.json) / [Trace](../examples/runs/real/run_ab6832e25f7a4a89/trace.jsonl) | [断言](../examples/runs/real/run_ab6832e25f7a4a89/assertions.json)；NEEDS_INPUT，工具0，模型未初始化 | 0/0 | 待确认 |
| 缺期限 | [输入](../examples/runs/real/run_facdd4af0d134366/input.json) / [输出](../examples/runs/real/run_facdd4af0d134366/output.json) / [Trace](../examples/runs/real/run_facdd4af0d134366/trace.jsonl) | [断言](../examples/runs/real/run_facdd4af0d134366/assertions.json)；NEEDS_INPUT，工具0，模型未初始化 | 0/0 | 待确认 |
| 超预算 | [输入](../examples/runs/real/run_3458d3f4953f486e/input.json) / [输出](../examples/runs/real/run_3458d3f4953f486e/output.json) / [Trace](../examples/runs/real/run_3458d3f4953f486e/trace.jsonl) | [断言](../examples/runs/real/run_3458d3f4953f486e/assertions.json)；真实超限→回传→被拒生成→有依据停止；决策质量问题见下 | 4/1 | 待确认路径与质量 |
| 工具失败/部分成功 | [输入](../examples/runs/real/run_933e837c1c2d4b57/input.json) / [输出](../examples/runs/real/run_933e837c1c2d4b57/output.json) / [Trace](../examples/runs/real/run_933e837c1c2d4b57/trace.jsonl) | [断言](../examples/runs/real/run_933e837c1c2d4b57/assertions.json)；脚本成功保留/无重收费，但SAVE_TEMPORARY未触发，专项不通过 | 7/7 | 未取得所需故障证据，不能签通过 |

六行均有实际材料，共5个不同原始输入（重放沿用正常输入），组数达到至少三组；**组数和目录齐备不等于专项覆盖完整**，SAVE_TEMPORARY及其后的真实模型回应仍缺失。[只读逐项核对](../examples/test-results/specialties-evaluation.json)区分原通用不变量通过和故障专项条件未满足，没有把通用断言通过改写成专项通过。

### 第一类：超预算反馈及后续有依据停止

预算3，偏好“尚未核价的基础方案想法，请给出实际估价后再决定是否继续”。动作没有强制贵方案或12→8：

1. 第1次模型真实检索成功，费用1。
2. 第2次提交basic真实候选，估价工具SUCCESS但feasibility=OVER_BUDGET：已发生1+剩余生成6/保存1=预计8，缺口5，剩余可用预算2。估价0费用。
3. 原call_id=`call_09s4kili`的真实工具观察进入第3次请求，逐项核对与Trace一致。模型仍尝试generate_script，文字提到超预算却误称“预算允许范围内继续”，被DEPENDENCY_UNSATISFIED拒绝，执行/收费0。
4. 该拒绝及超预算报价均保留在第4次请求，模型返回stop，明确8、3和缺口5，原因`BUDGET_EXCEEDED_BLOCKING_GENERATION`。终态INCOMPLETE、保存NOT_ATTEMPTED，账本1，无脚本，无假成功。

AI技术结论：取得最小“真实超预算反馈→回传→后续有依据停止”证据，不是成功替代方案，也不是下一动作立即合理调整。中间的不合理生成尝试必须保留作为质量缺陷，不能只展示最后stop。stop建议“减少素材/更简模式”没有当前费表支持（basic固定6，未提供更低档位）；不能把这些文字称为已验证可行路径。用户若要求下一动作即合理调整，该记录不满足更严格标准；本轮不加推理去挑选更好轨迹。预算没有被程序或模型擅自提高。

### 第二类：save_fail_once未到达注入点，不通过

真实7次动作依次为：检索limit10参数拒绝→模型改5后命中→有效basic估价→脚本生成SUCCESS→最新复估7+1=8→save_plan的draft缺`script_artifact_id`被INVALID_ARGUMENT拒绝→模型选择stop。最终`INCOMPLETE/SAVE_PLAN_VALIDATION_ERROR`、save_state=NOT_ATTEMPTED，回执null。

保存动作在参数校验阶段拒绝，实际保存执行0、保存operation行0，故配置的SAVE_TEMPORARY**没有发生**，并不存在可核对的真实业务FAILED保存尝试或故障后复用/重试。不能用此次参数反馈、正常路径的参数修正、离线save_fail_once通过补足本项。

脚本`script_a8b32eef4bad489b`仍保留；生成实际成功1次且只收费6，检索1，合计7，无保存费、无退款或迁移。模拟时间300秒（检索60+生成240），未执行的保存/保存故障不加60秒，不能把本例报成420。参数REJECTED尝试未被改写成成功；模型stop文字“已尝试修正后仍失败”与Trace不符（只有一次保存参数拒绝），记为内容质量缺陷，不当事实。

模型主动结束后本轮停止；剩余预算用例6次/故障用例3次（合计9次）未使用，不续跑该终态、不新建同场景重试、不扩大额度或修改提示词/Schema。后续若继续补此专项，需要新的明确额度与范围，本轮没有执行。

### 实际调用、usage、时间与费用

| 场景 | 新推理 | 输入/输出/总token（provider报告） | HTTP耗时合计 | 模拟已发生费用 / 模拟时间 |
| --- | --- | --- | --- | --- |
| 缺预算 | 0 | 不适用（无请求） | 0（无推理HTTP） | 0 / 0 |
| 缺期限 | 0 | 不适用（无请求） | 0（无推理HTTP） | 0 / 0 |
| 预算反馈 | 4 | 27,183 / 635 / 27,818 | 27.235秒 | 1 / 60秒 |
| 保存失败尝试 | 7 | 70,519 / 1,412 / 71,931 | 53.484秒 | 7 / 300秒 |
| 本轮合计 | **11/20** | **97,702 / 2,047 / 99,749** | **80.719秒** | **8**（两任务分别计费，不是正常方案重新收费） |

项目累计33次，27B累计30次。本轮11次全部取得usage，没有HTTP失败/超时/UNKNOWN；实际wire timeout均20秒，单请求及每场景仍有界。两任务模拟时间是各自时间轴，不把它们合为同一活动的时钟；HTTP耗时合计不是独立整进程墙钟或吞吐测量。旧第15次usage仍未知，完整累计usage未知，现金/电费未测，不补0。保存故障尝试的18.641秒请求返回参数不完整的draft，不是SAVE_TEMPORARY响应。

冻结后验核对：所有业务/数据/依赖文件哈希不变，66个历史记录/数据库文件哈希一致；新批次四个请求行、账本合计8、未确认操作0、保存操作0。正常及重放未新增执行，旧超时任务仍保留费用7，历史失败与本轮未完成产物全部保留。未推送远程。

### 用户审阅、最终缺口与停止

[用户本人审阅清单](06-content-review.md)分别列AI技术核对和用户结论，包含贴题/可读、事实与来源、依赖/角色/排期、T起点和单位、文案错误；修订建议独立存放，未覆盖已保存产物。建议T为负责人批准后续制作启动日期、单位工作日仍待用户决定，不是已批准口径。

当前结论：正常/重放及信息不足入口已有证据；预算有最终有依据停止轨迹及明确质量缺陷；第二类必需SAVE_TEMPORARY反馈路径未取得。用户本人审阅与结论均未完成，**不自动判定整体P0通过**。本轮不再发推理、不重跑正常、不重试整场，不加入P1或远程推送。

文档、材料引用、脚本/Runtime/历史文件哈希、140项JUnit计数、实际出站参数及累计请求数的收尾核对见[最终检查](../examples/test-results/specialties-documentation-check.json)。

## 独立生成故障专项（2026-11-10 21:52–21:53 Asia/Shanghai）

用户新授权6次、只一个新请求，起点33，不沿用此前9次余额。只新增generate_failure场景入口、6次额度/停止门禁及对应离线测试，使用已有generate_fail_once；业务Runtime、Schema、提示词、成本表、模型与推理参数保持冻结。正常、重放、预算、缺信息及旧保存故障均未重跑。[实际预检](../examples/test-results/generation-failure-preflight.json)复核Ollama0.40.9、qwen3.5:27b及模型摘要，业务摘要仍`1157ad49e78e8b80330e9c918fd20eaa9c7b3ab88a42359986be1ab6e384bee5`。

### 实际请求、动作和费用

实际只执行一次以下命令，使用修复盲测缺陷**之前**的脚本：

```powershell
.\.venv\Scripts\python.exe scripts/validate_qwen.py generate_failure --endpoint http://127.0.0.1:11434/v1 --model qwen3.5:27b --no-think --normal-index examples/test-results/qwen_normal_5f38146a433d.json
```

批次`qwen_generate_failure_40024f7694f5`，单请求键`qwen_generate_failure_40024f7694f5-generation_failure`，未来约30分钟截止，预算10，普通主题/偏好沿用正常输入。实际脚本SHA256为`f1f30f019db77344f31e59413189314f6d91531767625649cb9caba1e6e824e2`；执行版本快照保留于`var/qwen_generate_failure_40024f7694f5/validate_qwen.executed.py`，当前文件的离线修复版摘要另列，不能混称。

| 请求 | 实际模型动作与工具观察 | HTTP耗时 | 新模拟费 / 模拟秒 |
| --- | --- | --- | --- |
| 1 | 检索limit=10，被INVALID_ARGUMENT拒绝，未执行 | 8.140秒 | 0 / 0 |
| 2 | 模型改limit=5，实际检索命中3份，产物持久化 | 2.922秒 | 1 / 60 |
| 3 | 引用真实素材basic估价FEASIBLE，总计8 | 7.453秒 | 0 / 0 |
| 4 | 首次实际生成执行，返回FAILED/GENERATION_TEMPORARY，retryable=true | 5.532秒 | 0 / 240 |
| 5 | 原错误观察进入真实请求，模型自主选择同quote_id重试；生成SUCCESS | 5.594秒 | 6 / 240 |
| 6 | 模型引用成功脚本做post_generation最新复估，I=7、R=1、预计8，时间可行 | 8.062秒 | 0 / 0 |

第4次原call_id=`call_z84r6x63`，其完整FAILED结果在第5次原生function_call_output逐项相等；第5次新call_id=`call_xg9gcy50`，decision_summary明确回应GENERATION_TEMPORARY并选择同quote_id。不是执行器自动重试或离线动作替代。工具第1/2次实际生成使用同一操作身份，尝试1仍FAILED、尝试2为SUCCEEDED，数据库execution_attempt_count=2；逻辑步骤最终成功不改写首次失败尝试。

重试具有当前业务依据：此前检索已花1，失败按既有规则收费0，重试成功生成费6，保存尚需1，总预计8不超过预算10；失败耗时240仍累计，最新有效时钟/截止检查均FEASIBLE。检索成功只有一次且费用1，首次参数拒绝不是重复收费。前置检索产物及引用、脚本`script_5eea7a0f59ba4479`保留；没有再次检索/生成成功收费、没有保存或回执。模拟总540秒=检索60+失败240+成功240，不能把失败耗时抹为300。

第6次之后触发REAL_CALL_LIMIT，终态INCOMPLETE、保存NOT_ATTEMPTED、当前费用确定7，termination_persisted=true；未补调用、续跑、退款或迁移产物。6/6全部耗尽，项目累计39次（27B共36）。本轮provider usage全部取得：输入49,585、输出805、总50,390 token；HTTP请求耗时合计37.703秒，不是独立进程墙钟。20秒单次、180秒整次未改，实际6份wire connect/read/write/pool均20秒，出站除input外逐项等于旧正常请求的模型/指令/Schema/参数；一份最新状态及原生工具观察均保留。本轮无HTTP超时/UNKNOWN，旧第15次usage未知，完整累计usage及现金/电费仍未知。

[原始请求/响应/usage/timeout](../examples/test-results/qwen_generate_failure_40024f7694f5.json)、[输入](../examples/runs/real/run_fc04a04a8ca54959/input.json)、[输出](../examples/runs/real/run_fc04a04a8ca54959/output.json)、[Trace](../examples/runs/real/run_fc04a04a8ca54959/trace.jsonl)、[账本](../examples/runs/real/run_fc04a04a8ca54959/ledger.json)、[产物](../examples/runs/real/run_fc04a04a8ca54959/artifacts.json)、[报告](../examples/runs/real/run_fc04a04a8ca54959/report.md)、[通用自动断言](../examples/runs/real/run_fc04a04a8ca54959/assertions.json)、[专项后验检查](../examples/test-results/generation-failure-evaluation.json)。原始HTTP响应字节/headers仍未由现有记录器保留，不补造。

### 盲测缺陷及明确判定

收尾发现实验入口把场景标签放进模型可见的request_key，首次请求即包含`generate_failure`/`generation_failure`。这可能提前提示生成故障类别，违反用户“不能预先获知故障位置或次数”的隔离要求。没有直接证据证明模型实际关注该标签或因此重试，也不能据此忽略泄露风险，宣称为合格盲测。

| 必需条件 | 实际后验结果 |
| --- | --- |
| 检索成功、产物及费用存在 | 通过，搜索1、实际3份素材及产物保留 |
| 首次实际生成FAILED/GENERATION_TEMPORARY | 通过，实际执行并返回可重试错误 |
| 原错误按call_id进入下一真实请求 | 通过，原生完整结果逐项相等 |
| 与错误、预算、时间相符的模型动作 | 合理同报价重试成功，不是仅出现stop文字 |
| 前置成功保留、无重复收费、失败真实及耗时保留 | 通过，失败0费/240秒，成功6费/240秒，合计费用7/540秒 |
| 故障前模型不可见故障类别/次数提示 | **不通过：request_key泄露类别；实际影响未知** |
| 本轮专项总判定 | **不合格：机械反馈链成立，盲测要求未满足** |

因此新生成轨迹不计为满足本轮全部要求的第二类动态路径；也不改写预算路径或旧保存路径结论。原save_failure继续为：**“draft校验拒绝后停止，SAVE_TEMPORARY未触发，该场景未通过。”** 保存故障恢复仍未验证。合格的生成故障轨迹本可以独立覆盖原题工具失败/第二类路径，不必强求保存恢复；本次因盲测缺陷尚不能这样覆盖。

### 仅离线修正入口，不重复真实实验

已将generate_failure输入键改为`request_<随机UUID>`，批次和场景标签仅留在实验metadata，不进入新任务input；其他旧场景键规则不改。普通业务输入、模型、指令、工具、费用、预算与时间计算完全不变。新增门禁检查输入不含generate_fail_once/GENERATION_TEMPORARY或场景标签，随机键不同，原主题/预算/偏好原样保留；这验证入口，不代表重新取得合格真实路径。

| 版本/验证 | 实际结果 | 证据 |
| --- | --- | --- |
| 真实执行前入口版本 | 相关60通过、全套148通过；这些测试漏掉请求键提示问题 | [相关](../examples/test-results/generation-failure-targeted.xml)、[全套](../examples/test-results/generation-failure-full.xml) |
| 修正后首轮离线 | 相关61通过、全套149通过 | [相关JUnit](../examples/test-results/generation-failure-blind-targeted.xml)、[控制台](../examples/test-results/generation-failure-blind-targeted.txt)、[全套JUnit](../examples/test-results/generation-failure-blind-full.xml)、[控制台](../examples/test-results/generation-failure-blind-full.txt) |
| 修正后最终离线，补实际SDK MockTransport首请求检查 | 相关62通过、全套150通过；捕获整个SDK请求，确认只有随机无语义键且不含夹具/故障类别提示 | [相关JUnit](../examples/test-results/generation-failure-blind-sdk-targeted.xml)、[控制台](../examples/test-results/generation-failure-blind-sdk-targeted.txt)、[全套JUnit](../examples/test-results/generation-failure-blind-sdk-full.xml)、[控制台](../examples/test-results/generation-failure-blind-sdk-full.txt) |
| 修正后真实推理 | **未运行**；额度已耗尽，无第二个新请求 | 不以离线通过替代真实盲测证据 |

当前修正后脚本SHA256为`693e879f202378024c0547f301cd77aa4f38407ad77815b119d160cd84fafd82`，与实际执行摘要f1f30f...不同，明确分开。旧已保存方案、失败脚本/账本及105个历史文件/数据库哈希不变，业务摘要仍1157ad...。验收材料索引在保留原六行逐项不变的基础上追加独立generation_failure行；[修改前索引](../examples/test-results/p0-acceptance-materials-index-before-generation.json)保留，旧specialties-evaluation.json不覆盖。

本轮结束，不重试整场、不再申请隐含余额、不推送、不加入P1。用户本人审阅仍pending，整体P0不自动通过。当前缺口是符合隔离要求的第二类工具故障真实路径及用户内容审阅；保存恢复继续作为未验证具体场景单列。

## 内容协作审阅及用户确认（2026-11-10最新补记）

Codex核对正常已保存方案、三份合成来源、任务依赖、预算及准备期限，并撰写独立文案整理稿和示例排期说明。用户随后在本对话明确回复“C1–C4接受”，接受校招合成演示适用性结论、独立编辑附录、T定义及工作日示例口径，以及候选渠道/角色级分工。详见[内容审阅及确认记录](06-content-review.md)。内容审阅这一项已完成，前文关于内容审阅pending的描述仅为历史状态；不代表用户逐项确认了各业务专项。

原始模型产物及不足保留，编辑附录不算作模型原始输出；活动仍未执行。本次仅同步文档，未新增真实推理、业务执行、费用、保存回执或自动测试结果；其余专项及整体P0本次未重判。
