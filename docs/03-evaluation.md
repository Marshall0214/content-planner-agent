# 评估、实际证据与未完成项

记录日期：2026-11-10。**工程与离线验证完成；整体P0真实模型验收未达完整标准。**

最终pytest：65通过，0失败，0错误，0跳过。证据：[final.xml](../examples/test-results/final.xml)、[控制台结果](../examples/test-results/final.txt)。实际Python 3.12.7、pydantic 2.14.3、openai 2.54.0、pytest 9.2.0；[环境及依赖检查](../examples/test-results/environment.json)，依赖检查退出码0。锁定文件uv.lock与requirements.lock来自实际解析/导出。

L1/L2测试和内存HTTP替身不调用真实推理API，不能充作L3。真实业务模型API调用0次；未取得任何合格真实动态路径。

## 12组P0逐项状态

“通过”限于自动断言和实际离线入口，语义质量及真实决策另列。

| 用例 | 工程/离线结果 | 验证重点 | 仍未运行/需人审 |
| --- | --- | --- | --- |
| C01 | 通过（2项关联测试；[JUnit](../examples/test-results/final.xml)） | 正文、引用、三表保存与立即终结 | 真实模型正常路径、运营语义审阅 |
| C02 | 通过（3项关联测试；[JUnit](../examples/test-results/final.xml)） | 缺预算、零模型/业务调用 | 真实会话对应交叉核对（如适用）；不另伪造模型调用 |
| C03 | 通过（2项关联测试；[JUnit](../examples/test-results/final.xml)） | 缺期限、零模型/业务调用 | 真实会话对应交叉核对（如适用）；不另伪造模型调用 |
| C04 | 通过（2项关联测试；[JUnit](../examples/test-results/final.xml)） | 超限观察进入下一离线轮；可调整或停止 | 第一类真实动态证据 |
| C05 | 通过（3项关联测试；[JUnit](../examples/test-results/final.xml)） | 失败保留产物、复用与费用、失败尝试不抹掉 | 第二类真实动态证据 |
| C06 | 通过（2项关联测试；[JUnit](../examples/test-results/final.xml)） | 跨CLI进程重放与冲突；真实提交输入与原绑定输入分开 | 真实会话完成后的重放材料 |
| C07 | 通过（1项关联测试；[JUnit](../examples/test-results/final.xml)） | 新报价读最新账本时钟；同规格复用0增量 | 真实会话对应交叉核对（如适用）；不另伪造模型调用 |
| C08 | 通过（1项关联测试；[JUnit](../examples/test-results/final.xml)） | 已花11+新basic6+保存1=18 | 真实会话对应交叉核对（如适用）；不另伪造模型调用 |
| C09 | 通过（3项关联测试；[JUnit](../examples/test-results/final.xml)） | 360模拟+60真实推进=420；复用不加时；最新期限守卫 | 真实会话对应交叉核对（如适用）；不另伪造模型调用 |
| C10 | 通过（10项关联测试；[JUnit](../examples/test-results/final.xml)） | 最后合法调用成功/失败/UNKNOWN与调用上限 | 真实会话对应交叉核对（如适用）；不另伪造模型调用 |
| C11 | 通过（4项关联测试；[JUnit](../examples/test-results/final.xml)） | 假finish不成功；UNKNOWN冻结、无查证/旧写覆盖 | 真实会话对应交叉核对（如适用）；不另伪造模型调用 |
| C12 | 通过（18项关联测试；[JUnit](../examples/test-results/final.xml)） | 输入、引用、有限硬需求和空正文/依赖校验 | 真实会话对应交叉核对（如适用）；不另伪造模型调用 |

全部测试名称、实际值失败信息见JUnit；测试源码位于tests/。其中时间/费用/事务用L1，循环/反馈与额度用L2。OpenAI适配器还通过实际已安装SDK加httpx.MockTransport的本地序列化与call_id回传测试；该测试不是在线模型验收。

README示例入口另有实际核对：[readme-commands.json](../examples/test-results/readme-commands.json)。

## 实际CLI材料

批次索引：[batch_ab59870dd4bf.json](../examples/test-results/batch_ab59870dd4bf.json)。以下是12次实际CLI执行，均标offline_mock；费用为模拟unit。每个目录含实际input、metadata、output、Trace、账本、产物、回执状态和自动不变量检查。

| Case | 状态/保存 | 已确认总额或最后可信 | 本次离线模型轮数 | 证据 |
| --- | --- | --- | --- | --- |
| C01 | COMPLETED/CONFIRMED | 8 | 5 | [output](../examples/runs/offline_mock/run_1f77a1440bad43d7/output.json)、[Trace](../examples/runs/offline_mock/run_1f77a1440bad43d7/trace.jsonl)、[方案/原因](../examples/runs/offline_mock/run_1f77a1440bad43d7/report.md) |
| C06 | COMPLETED/CONFIRMED | 8 | 0 | [output](../examples/runs/offline_mock/run_6a70e46b12004a03/output.json)、[Trace](../examples/runs/offline_mock/run_6a70e46b12004a03/trace.jsonl)、[方案/原因](../examples/runs/offline_mock/run_6a70e46b12004a03/report.md) |
| C06-conflict | FAILED/CONFIRMED | 8 | 0 | [output](../examples/runs/offline_mock/run_84ede2d1981648e9/output.json)、[Trace](../examples/runs/offline_mock/run_84ede2d1981648e9/trace.jsonl)、[方案/原因](../examples/runs/offline_mock/run_84ede2d1981648e9/report.md) |
| C02 | NEEDS_INPUT/NOT_ATTEMPTED | 0 | 0 | [output](../examples/runs/offline_mock/run_f252290c72024ed6/output.json)、[Trace](../examples/runs/offline_mock/run_f252290c72024ed6/trace.jsonl)、[方案/原因](../examples/runs/offline_mock/run_f252290c72024ed6/report.md) |
| C03 | NEEDS_INPUT/NOT_ATTEMPTED | 0 | 0 | [output](../examples/runs/offline_mock/run_7431c5df113749c0/output.json)、[Trace](../examples/runs/offline_mock/run_7431c5df113749c0/trace.jsonl)、[方案/原因](../examples/runs/offline_mock/run_7431c5df113749c0/report.md) |
| C04 | INCOMPLETE/NOT_ATTEMPTED | 1 | 3 | [output](../examples/runs/offline_mock/run_d9e2b0b159674fbc/output.json)、[Trace](../examples/runs/offline_mock/run_d9e2b0b159674fbc/trace.jsonl)、[方案/原因](../examples/runs/offline_mock/run_d9e2b0b159674fbc/report.md) |
| C04-adjust | COMPLETED/CONFIRMED | 8 | 6 | [output](../examples/runs/offline_mock/run_bc63dd8ac9d44ae8/output.json)、[Trace](../examples/runs/offline_mock/run_bc63dd8ac9d44ae8/trace.jsonl)、[方案/原因](../examples/runs/offline_mock/run_bc63dd8ac9d44ae8/report.md) |
| C05 | COMPLETED/CONFIRMED | 8 | 6 | [output](../examples/runs/offline_mock/run_595d1d811a7a4de3/output.json)、[Trace](../examples/runs/offline_mock/run_595d1d811a7a4de3/trace.jsonl)、[方案/原因](../examples/runs/offline_mock/run_595d1d811a7a4de3/report.md) |
| C05-permanent | INCOMPLETE/FAILED | 7 | 6 | [output](../examples/runs/offline_mock/run_4cbb51a91b4f4842/output.json)、[Trace](../examples/runs/offline_mock/run_4cbb51a91b4f4842/trace.jsonl)、[方案/原因](../examples/runs/offline_mock/run_4cbb51a91b4f4842/report.md) |
| C10-success | COMPLETED/CONFIRMED | 8 | 5 | [output](../examples/runs/offline_mock/run_1452503cf1f645dd/output.json)、[Trace](../examples/runs/offline_mock/run_1452503cf1f645dd/trace.jsonl)、[方案/原因](../examples/runs/offline_mock/run_1452503cf1f645dd/report.md) |
| C10-failed | INCOMPLETE/FAILED | 7 | 5 | [output](../examples/runs/offline_mock/run_35fc9979ee5c4646/output.json)、[Trace](../examples/runs/offline_mock/run_35fc9979ee5c4646/trace.jsonl)、[方案/原因](../examples/runs/offline_mock/run_35fc9979ee5c4646/report.md) |
| C10-unknown | INCOMPLETE/UNKNOWN | 未知（最后可信7） | 5 | [output](../examples/runs/offline_mock/run_1faa0502f2ba453f/output.json)、[Trace](../examples/runs/offline_mock/run_1faa0502f2ba453f/trace.jsonl)、[方案/原因](../examples/runs/offline_mock/run_1faa0502f2ba453f/report.md) |

C06-conflict的FAILED表示本次输入冲突，原任务仍COMPLETED且保存事实不变；input.json是本次实际提交，bound_input.json是原请求。C10-unknown的总额未知，7只是最后可信累计，不宣称保存免费或失败。

材料分组：G1正常/重复/冲突；G2分别缺预算/期限；G3预算停止及离线调整；G4工具失败与部分成功。已有四类离线实际材料，但不替代题面要求的两类真实动态路径。正常保存8、永久保存失败保留7、最后调用三分支和重放零增量均有实际CLI输出。最早smoke-normal输出是历史冒烟记录，最新批次是本表索引。

## 失败历史与修正

| 记录 | 当时结果 | 处理 |
| --- | --- | --- |
| [initial.xml](../examples/test-results/initial.xml) | 3通过、51启动错误 | 默认临时目录无写权限，改为项目.cache/pytest。 |
| [retry.xml](../examples/test-results/retry.xml) | 51通过、3失败 | 报价先后不能依赖JSON字典顺序，改sequence。 |
| [ordering-fix.xml](../examples/test-results/ordering-fix.xml) | 54通过 | 保留该阶段记录；后续增加关键边界和SDK序列化测试。 |
| [environment-initial.json](../examples/test-results/environment-initial.json) | 依赖检查退出2 | uv默认缓存不可写；设置项目内cache/temp后environment.json检查退出0。 |

没有删除失败记录，也未将环境错误算业务通过。初始venv/依赖下载及重装临时目录错误的过程记录于复盘。当前最终测试没有已知失败；最终新增了非法停止文本反馈进入下一轮的回归断言。此前批次仍保留，最新批次的source_digest对应当前应用代码。真实模型效果仍未验证。

## 未运行的真实验收与资源需求

| 项目 | 当前状态 | 最小后续验证/停止条件 |
| --- | --- | --- |
| 指定模型与端点兼容 | 未运行 | 用户明确提供配置后做一次真实工具往返；不通则保留实际错误，不降级Mock。 |
| 正常真实方案 | 未运行 | 完整输入到保存确认，审阅脚本、引用和方案；正常确认后不得另请求收尾。 |
| 第一类：超预算反馈后选择 | 未运行 | 实际超限结果进入下一次真实请求，模型替代/调整/有依据停止。12→8不强制；未触达反馈不计证据。 |
| 第二类：工具失败/部分成功后选择 | 未运行 | 使用本地save_fail_once等真实工具返回，下一真实请求处理错误且保留成功结果。 |
| 真实会话重放与信息不足 | 未运行/普通入口逻辑已离线验证 | 在线正常请求后同键重放/冲突；缺字段入口应保持0模型调用。 |
| 人类业务质量审阅 | 未完成 | 运营人员核对贴题、事实支持、可读性和合理取舍；自动结构校验不能代替。 |

需要：MODEL_PROVIDER、明确MODEL_NAME、密钥、可选明确端点，以及每次和总体调用/费用额度。本次未读取可用密钥发起请求。预计3个核心在线场景约15–30次请求仅为规划；最多6次运行×每次12次可设72次请求硬上界，仍需事先授权，不保证取得证据。价格、真实延迟、实际usage与费用均待运行记录，当前不填写。

资源不足、额度耗尽或缺任一类合格路径/必要场景证据，就标未达标。发现重复收费、失败冒成功、越过硬约束，应先停扩展并修复。P1自动查证、跨进程续跑等未实现、未运行，不进入P0通过清单。
