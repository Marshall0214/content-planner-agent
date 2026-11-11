# 最终交付复核（2026-11-11，Asia/Shanghai）

**建议按第二题原始最低要求提交，附本页限制说明。** 现有资料支持正常方案保存、信息不足、预算超限、工具失败、重复执行，以及两条真实模型收到工具反馈后改变动作的记录。内容方案已由用户接受C1–C4。此结论是对现有证据的技术复核，不是外部考官评分，也不表示所有项目附加实验、每个模型动作或生产能力都通过。

本轮只读核对既有记录并整理文档/索引：新增模型调用0，新增业务运行0，没有重跑测试、安装依赖、修改Runtime或推送。机器可读结论见[最终交付评估](../examples/test-results/final-delivery-assessment.json)，逐场景材料见[验收索引](../examples/test-results/p0-acceptance-materials-index.json)。

## 1. 原题要求与已有证据

| 原题要求 | 现有实际记录与结论 | 证据入口 |
| --- | --- | --- |
| 四个业务工具、可审阅活动方案及脚本/引用 | 正常请求实际执行检索、估价、脚本生成和保存；输出目标、受众、渠道、任务依赖、正文、素材事实、费用和非空回执 | [原始方案报告](../examples/runs/real/run_b307abb73de84313/report.md)、[完整输出](../examples/runs/real/run_b307abb73de84313/output.json) |
| 正常完成 | COMPLETED/CONFIRMED，费用8，预算10；有效完成时间早于当时截止时间。活动尚未执行 | [正常记录及重放检查](../examples/test-results/normal-latest-evaluation.json) |
| 缺预算或期限 | 两个真实模式入口分别NEEDS_INPUT，模型未初始化，工具/模型调用及收费均0 | [缺预算输出](../examples/runs/real/run_ab6832e25f7a4a89/output.json)、[缺期限输出](../examples/runs/real/run_facdd4af0d134366/output.json) |
| 预算超限及动态选择 | 实际报价OVER_BUDGET：已花1+剩余7=8，预算3、缺口5；反馈进入真实下一轮，模型尝试生成被拒后依据预算停止。没有加预算或扣生成费 | [预算Trace](../examples/runs/real/run_3458d3f4953f486e/trace.jsonl)、[输出](../examples/runs/real/run_3458d3f4953f486e/output.json) |
| 工具失败及动态选择 | 首次实际生成FAILED/GENERATION_TEMPORARY；完整错误按原call_id回传；模型选择同报价重试并成功。保留成功检索、首次失败及费用/耗时 | [生成故障Trace](../examples/runs/real/run_fc04a04a8ca54959/trace.jsonl)、[输出](../examples/runs/real/run_fc04a04a8ca54959/output.json)、[账本](../examples/runs/real/run_fc04a04a8ca54959/ledger.json) |
| 重复执行 | 原输入重放返回同一非空方案/回执，新增模型调用、业务执行、收费均0，数据库逻辑转储不变 | [重放输出](../examples/runs/real/run_a76068d0afbb4ff9/output.json)、[实际重放断言](../examples/test-results/qwen_normal_5f38146a433d.json) |
| 至少两条反馈驱动的真实路径 | 成本反馈后的有依据停止；生成故障反馈后的同报价重试。均有实际本地Qwen请求、工具结果、下一请求和动作记录 | 上述预算/生成Trace及[原始推理索引](../examples/test-results/qwen_generate_failure_40024f7694f5.json) |
| 至少三组实际输入/输出/运行记录 | 当前索引7行，6个不同原始输入（含旧保存故障失败记录），重复例复用正常输入；所需场景具有各自input/output/Trace/断言入口 | [完整材料索引](../examples/test-results/p0-acceptance-materials-index.json) |
| 有界退出、失败真实性和成功结果保留 | 生成重试成功后6次额度耗尽，诚实返回INCOMPLETE/REAL_CALL_LIMIT、保存NOT_ATTEMPTED、费用7，未假称保存或补调用；首次FAILED尝试仍在 | [生成输出](../examples/runs/real/run_fc04a04a8ca54959/output.json)、[既有150项测试](../examples/test-results/generation-failure-blind-sdk-full.xml) |

题面允许本地函数/Mock作为业务工具；真实模型为本地Ollama运行的qwen3.5:27b，原生无状态Responses工具协议。实际验证环境为2026-11-10的Ollama0.40.9、think=false、temperature=0.2、输出上限4000、SDK重试0、20秒单次/180秒整次。offline_mock及SDK MockTransport从未替代上述真实模型证据。

## 2. 生成故障记录：证明范围与限制

实际证明：检索成功并收费1；生成实际开始执行、返回可重试GENERATION_TEMPORARY且收费0/模拟240秒；`call_z84r6x63`的完整错误进入第5次真实请求；模型明确选择相同quote_id重试，成功生成收费6/模拟240秒。两次尝试同一操作身份，首次FAILED没有被覆盖；成功搜索只收费一次，总计7、总模拟540秒。最新复估为7+保存1=8，预算10且截止可行。这里的合理动作是重试，不是只凭stop文字或预写日志判断。

限制：模型可见request_key带`generation_failure`类别提示。它不等于程序预写了模型下一动作，但可能使模型预期故障；因此不能证明“完全未预期故障时仍会恢复”、排除提示对选择的影响，或据此推断成功率/稳定性/普遍因果能力。后续随机键修正只经离线SDK验证，没有新的真实盲测。

**按原题可将该轨迹作为带限制说明的工具失败与第二类动态调整证据。** 原题要求真实模型观察工具结果并选择后续动作，没有明文规定故障类别必须盲化。历史那轮额外要求了盲测隔离，故其“不合格”结论仍有效，见[原始专项评估](../examples/test-results/generation-failure-evaluation.json)；本轮没有把它改成“盲测通过”，也没有修改请求、动作、Trace、账本或产物。

原执行脚本已从被忽略的var目录原样归档：[执行版源文本](evidence/validate_qwen-generation-failure-f1f30f019db7.py.txt)，SHA256为`f1f30f019db77344f31e59413189314f6d91531767625649cb9caba1e6e824e2`。它用于核对历史运行，不作为当前入口执行。当前修正版脚本摘要为`693e879f202378024c0547f301cd77aa4f38407ad77815b119d160cd84fafd82`，两个版本明确区分。

归档文本使用局部.gitattributes禁用换行归一化，避免Windows checkout改变上述字节摘要；这只是交付文件配置，不改变业务或实验脚本。

## 3. 题面、设计选择与附加条件

| 分类 | 本项目口径及最终处理 |
| --- | --- |
| 题面最低要求 | 四工具、真实反馈循环、五类场景、两条动态记录、至少三组材料、有界退出和可信费用/状态；当前有证据支持 |
| 项目设计选择 | Python原生单Agent、SQLite三表、CLI、不可变候选报价和操作幂等；其实现/边界由既有测试和材料核对，不是题面指定框架 |
| 额外评测：故障盲测隔离 | 是先前实验的明确条件，历史不合格保留；不是原题最低硬门槛，也不应抹去实际恢复行为 |
| 额外具体场景：保存失败恢复 | 原save_failure为“draft校验拒绝后停止，SAVE_TEMPORARY未触发，该场景未通过。”保存恢复仍未验证；生成故障轨迹不能改名冒充保存恢复，但可独立覆盖原题工具失败 |
| 展示规格 | 30秒、竖屏、分镜标注不是通用门槛；真正用户硬需求仍需保留 |
| 三小时 | 建议开发工时，不是验收时限；实际用时不到6小时（用户确认），不声称三小时内完成 |
| 加分/P1 | 跨进程失败续跑、自动对账/回执查证、并发接管、多Agent等未实现；不作为本次最低要求缺口 |

决策质量缺陷：预算反馈后仍尝试不可行生成，被程序守卫拒绝才停止；“减少素材/更简模式”的建议没有当前固定basic费表支持；正常及旧保存场景出现参数遗漏，旧保存stop还描述了不存在的多次修正。全部保留，不当作优质决策示例或已验证替代方案。程序约束避免了这些动作导致虚假成功或额外生成费。

未验证能力：干净随机键的真实盲测、SAVE_TEMPORARY恢复、跨机器/全新clone运行、其他模型/云端兼容、生产稳定性、真实营销效果。它们属于范围/效果限制；当前没有据此发现必须扩展Runtime或追加模型实验的提交阻断。

## 4. 内容确认与编辑附录

用户已接受C1–C4，确认记录日期2026-11-10，见[完整协作审阅](06-content-review.md)。原始模型方案仍保留无单位T+排期及文案不足；Codex整理稿和T定义/工作日口径是**用户接受的独立编辑附录**，没有写回原方案/脚本/数据库，没有新回执。接受内容不代表真实拍摄、制作、发布或传播效果已经发生，也不是用户逐项签署所有技术实验。

## 5. 评审运行与证据读取

从项目根目录阅读以下文件即可评审，**不需要启动Ollama、重建历史数据库或重跑过期输入**：

```powershell
Get-Content docs/07-final-delivery.md -Encoding UTF8
Get-Content examples/test-results/final-delivery-assessment.json -Encoding UTF8
Get-Content examples/runs/real/run_b307abb73de84313/report.md -Encoding UTF8
Get-Content docs/06-content-review.md -Encoding UTF8
```

可选的代码复核入口（本轮未执行）：先按README安装锁定依赖，再运行`python -m pytest tests -q --junitxml=var/reviewer-tests.xml`；这是离线工具/流程/SDK替身测试，不调用真实模型。CLI体验使用新键和未来期限，见README；不要用旧截止时间重跑业务来核验历史结果。历史真实命令及错误均留在03-evaluation.md；本轮不安排重新取证。

## 6. AI贡献与实际用时

用户提供业务题面、范围与取舍、调用额度，并完成C1–C4确认。Codex协助设计、编写/修复工程、运行已授权测试/本地模型实验、核对证据、编辑文档和审阅附录。不能宣称由用户独立编码或亲自执行全部测试。详见[AI使用说明](04-ai-usage.md)。

可确认的计时：39次历史真实请求的HTTP等待合计**277.502秒**（含失败/超时），最新一次全套150项JUnit记录用时**18.391秒**，时间戳`2026-11-10T22:02:12.642346+08:00`。两者都不是项目开发工时。**用户于2026-11-11确认项目实际用时不到6小时。** 这是用户对实际投入的陈述，未提供精确分钟/分项计时，也不是Codex独立测量；不能以跨多轮的日志跨度或设计的三小时估计代替该记录。本轮不新增模型或测试计时；历史一次超时没有usage，完整累计token和模型现金/电费仍未知。

## 7. Git交付状态与必要动作

本节及JSON中的初版HEAD、未提交文件计数是最终复核时的历史快照。用户随后已另行授权上传Git；本交付版本将代码、文档和证据一并提交，最新提交号及发布结果以实际Git历史为准。

<!-- GIT_SNAPSHOT_START -->
本地独立仓库：`D:/硕/work/JobHuntBot/content-planner-agent`；origin：[Marshall0214/content-planner-agent](https://github.com/Marshall0214/content-planner-agent)。当前分支`codex/initial-p0`，HEAD为`3129570031d01ea41892f00b82a10c6c7409df63`，提交主题为`feat: implement P0 content planner agent and offline verification`，仍是初版。

最终检查时，已有跟踪文件修改18个，未跟踪文件1154个（其中examples材料1141个），暂存0个。代码/配置/测试/文档及真实证据尚未形成最终commit；不能只提交README或仅提交已跟踪文件，遗漏schema_compat.py等新模块/测试及examples会造成交付不完整。完整路径清单见[本地最终检查](../examples/test-results/final-delivery-check.json)。

未发现合并冲突、index.lock、缺少作者身份或超过10MB的候选文件；静态敏感标记检查未命中候选文件，但这不等于绝对安全保证。没有新增Runtime工程阻断。具体交付缺口已原样补齐：原执行脚本原在被忽略的var下，现已归档并保留SHA256。尚需stage/commit（或打包）是版本交付动作，不需要追加模型实验。本轮未测试Git写权限、未执行commit，也未联网验证远端HEAD/访问权限，因此不保证未来Git操作或远端状态。
<!-- GIT_SNAPSHOT_END -->

必要收尾动作是将本地最终代码、文档、锁文件和全部选定证据纳入本项目的一次最终提交，或先交付完整文件包。本轮仅核对，不擅自stage/commit/push；远端HEAD/权限未联网核验。不能把初版HEAD当成包含最新修复及真实证据的最终版本。

从已核实的本项目根目录，可在另行决定提交时使用（本轮未执行）：

```powershell
git status --short
git add -A
git diff --cached --stat
git commit -m "docs: finalize evidence and submission review"
```

如评审入口要求GitHub链接展示最终版本，还需在后续授权下推送该提交；本轮禁止推送，因此这里只报告所需动作。没有新的必需模型调用、功能扩展或验收实验。

## 8. 提交说明补充（2026-11-11）

用户确认实际用时不到6小时；不补造分钟数或阶段耗时。当前.env.example和使用说明统一为qwen3.5:27b、MODEL_THINK=false、temperature=0.2，20/180秒配置不变。早期7B模型的失败记录属于历史实验，保持原样，不冒充27B结果。本次只更新配置清单和文档，不新增模型调用、业务运行或验收测试；完整150项仍是既往实测记录。
