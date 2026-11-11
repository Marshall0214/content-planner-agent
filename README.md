# 内容任务规划 Agent

题号：**第二题「内容任务规划 Agent」**。Python 原生单 Agent + SQLite 三表 + CLI。四个本地工具负责素材检索、脚本生成、成本估算和方案保存。

代码仓库：[Marshall0214/content-planner-agent](https://github.com/Marshall0214/content-planner-agent)。

**最终交付结论（2026-11-11）：现有记录支持按第二题原始最低要求提交，须附限制说明；不是所有项目附加实验均通过。** 正常保存、缺信息、预算停止、工具失败及重复执行均有材料，两条真实模型反馈调整路径分别为预算反馈后的停止、生成错误后的重试。生成轨迹的请求键类别提示限制了盲测/因果结论，但不抹去实际错误回传与恢复；历史盲测不合格记录原样保留，旧保存故障场景仍未通过。用户已接受内容审阅C1–C4，编辑附录与原模型输出分开。本轮新增推理/业务运行0，累计仍39次，150项是既往测试记录，未重跑。本交付版本包含最终修复和证据；提交前Git快照保留，实际提交号以Git历史为准。[最终交付说明](docs/07-final-delivery.md)、[逐项机器评估](examples/test-results/final-delivery-assessment.json)、[材料索引](examples/test-results/p0-acceptance-materials-index.json)、[用户确认](docs/06-content-review.md)。

## 评审入口

无需启动模型或重跑历史输入。先读[最终要求核对与限制](docs/07-final-delivery.md)，再看[原始已保存方案](examples/runs/real/run_b307abb73de84313/report.md)及[用户接受的独立编辑附录](docs/06-content-review.md)。验收索引逐项链接输入、输出、Trace和自动断言；原始结果、失败记录和账本没有改写。

```powershell
Get-Content docs/07-final-delivery.md -Encoding UTF8
Get-Content examples/test-results/final-delivery-assessment.json -Encoding UTF8
Get-Content examples/runs/real/run_b307abb73de84313/report.md -Encoding UTF8
```

实际用时：**不到6小时（用户于2026-11-11确认）**。这是用户对实际投入的陈述，未提供精确分钟或分项计时，不声称三小时完成。39次历史真实请求HTTP合计277.502秒、最近150项测试JUnit用时18.391秒，均不是开发工时。AI贡献、Git状态、必要提交动作和未验证能力见最终交付说明。以下运行命令供后续评审选择，最终复核未新增运行；后续提交推送由用户另行授权，提交前状态快照不是发布版本号。

## 安装

已在 Windows / Python 3.12.7 验证。先进入本仓库根目录（包含pyproject.toml），再执行以下命令；需要已安装uv。锁文件为uv.lock，requirements.lock是实际导出的带哈希依赖清单。

```powershell
$env:UV_CACHE_DIR = Join-Path $PWD '.cache\uv'
$env:TMPDIR = Join-Path $PWD '.cache\tmp'
$env:TEMP = $env:TMPDIR
$env:TMP = $env:TMPDIR
$env:UV_LINK_MODE = 'copy'
New-Item -ItemType Directory -Force -Path $env:TMPDIR | Out-Null
uv sync --locked --extra dev
```

首次安装需要访问PyPI；已缓存环境可加--offline。本次沙箱默认临时目录不可写，因此缓存/临时文件固定到项目.cache。配置仅影响当前终端；不用激活脚本即可直接运行python.exe。项目支持本地源码可编辑安装；未验证独立wheel部署，默认合成资料位于项目data目录。

## 跑通并查看离线方案

以下CLI入口已经通过实际子进程验证。首次生成输入，再执行；make-input只做本地文件生成，不调用模型。

```powershell
.\.venv\Scripts\python.exe -m content_planner.cli make-input --out var/demo.json --request-key demo-001
.\.venv\Scripts\python.exe -m content_planner.cli run --mode offline_mock --input var/demo.json --db var/demo.sqlite3 --case-id C01
.\.venv\Scripts\python.exe -m content_planner.cli inspect --request-key demo-001 --db var/demo.sqlite3
```

run的stdout包含evidence_dir和完整output。打开该目录下report.md即可审阅活动目标、受众、脚本正文、合成素材出处、运营任务建议、费用和保存回执。stdout也可重定向到var中的文件再解析。

复用同一个输入文件执行同一run命令，返回同plan_id，本次模型调用与新增费用均为0。**不要重新运行make-input来测试重放**，因为它会生成新deadline；同键不同输入返回冲突。要创建新的请求就使用新request-key。

将实际回执中的plan_id替换到下方；export和inspect只做普通读取，不启动UNKNOWN查证或续跑。

```powershell
.\.venv\Scripts\python.exe -m content_planner.cli export --plan-id '<实际回执中的plan_id>' --db var/demo.sqlite3 --out var/export
```

## 测试与实际示例

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q --junitxml=var/reviewer-tests.xml
.\.venv\Scripts\python.exe scripts/collect_examples.py
```

pytest的临时目录固定为.cache/pytest，每次测试会清理这个专用目录。collect_examples只执行offline_mock，自动产生正常、信息不足、预算反馈、工具故障、重复和边界的14次实际CLI记录，包含真实SQLite写入异常后的首次内存UNKNOWN与同键重放，并另核对inspect。每次生成新批次，保留历史。examples只放实际执行产生的记录；输入模板不放这里。最新已核对离线批次：[batch_cff97e13a98e.json](examples/test-results/batch_cff97e13a98e.json)；[最近完整测试（150通过，历史实测）](examples/test-results/generation-failure-blind-sdk-full.xml)、[最近相关回归（62通过，历史实测）](examples/test-results/generation-failure-blind-sdk-targeted.xml)。原73项及历史批次保留。

```powershell
# 模拟保存首次明确失败；模型是离线脚本，不能用作真实动态证据
.\.venv\Scripts\python.exe -m content_planner.cli run --mode offline_mock --input var/demo.json --db var/failure.sqlite3 --fixture save_fail_once
```

离线场景basic为常规流程；budget_adjust是显式的“先高级后降本”测试脚本，不代表真实模型会这样做；stop_on_failure用于停止路径。真实适配器没有这些预写决策分支。故障按工具实际执行序号触发，复用和参数拒绝不消耗实际尝试。

退出码：0已确认完成；2待补充；3未完成（含UNKNOWN）；4输入/请求键冲突；5配置或明确基础设施失败。非0是被验证的业务结果之一，不等于测试失败。

## 本地Qwen：正常保存与零增量重放已验证

2026-11-10已核实Ollama0.40.9、qwen3.5:27b及模型摘要不变；本机 `http://127.0.0.1:11434/v1` 使用原生无状态Responses，无需云端密钥。保持temperature=0.2、think=false、4000输出、SDK重试0、20秒单次/180秒总上限。[正常轮预检](examples/test-results/normal-latest-20261110T102828Z-preflight.json)。

正常证据批次实际执行一次以下命令：新键`qwen_normal_5f38146a433d-normal`、未来期限2026-11-10T10:59:00.371285Z，仅一条正常链路，确认保存后才原样重放。7次真实推理完成，剩余3次未使用；没有启动30次批次或额外动态实验。再次执行会创建新请求并消耗新的额度：

```powershell
.\.venv\Scripts\python.exe scripts/validate_qwen.py normal --endpoint http://127.0.0.1:11434/v1 --model qwen3.5:27b --no-think
```

[正常批次实际请求/响应](examples/test-results/qwen_normal_5f38146a433d.json)：limit=10被拒→模型改5、检索命中3份→basic估价8→生成脚本→最新复估7+1=8→模型提交draft缺少嵌套script_artifact_id被拒→模型补齐后保存确认。两次拒绝均未执行业务或收费；模拟费用为检索1+生成6+保存1=8，工具模拟耗时360秒。7次请求usage为输入70,501、输出1,742、合计72,243 token；HTTP耗时合计65.501秒，实际wire timeout每次20秒。确认后直接结束，没有模型收尾调用；[原样重放](examples/runs/real/run_a76068d0afbb4ff9/output.json)与原方案/回执一致且零增量，数据库逻辑转储不变。

[旧失败基线](examples/test-results/qwen_normal_0f1745fd4b32.json)保留：第6次20秒ReadTimeout，INCOMPLETE/MODEL_UNAVAILABLE、保存NOT_ATTEMPTED、费用7及脚本保留，失败usage未知。事前/事后11个文件（含数据库）字节哈希一致，见本轮总索引。没有续跑、退款或迁移旧产物。

检索query按空白分词、任一词作不区分大小写子串匹配；tags必须全部精确匹配（AND），[]不滤标签；allowed_usage精确匹配，只有null表示不限。语义词放query，不假定它们是目录标签。输出feedback含实际过滤条件、关键词/过滤后/返回数量、从实际目录计算的标签/usage和未识别值。计数在limit截断前后分开；后台不自动改条件。空结果仍收费1/60模拟秒，成功复用0增量。

空结果后由模型决定改查询、减少可选过滤或停止；没有实际命中就补检索或说明缺口，不用空material_ids估价。用户硬过滤不放宽；P0现有硬需求解析不支持的过滤要求保留原文并NEEDS_INPUT澄清，不新增通用硬过滤配置。[原两条查询0→3的实际工具核对](examples/test-results/retrieval-filter-audit.json)是确定性工具证据，没有模型调用。

原[27B Schema内联对照](examples/test-results/schema-inline-comparison.json)、[27B失败基线](examples/test-results/qwen_smoke_6c1a2138f50b.json)和[7B记录](examples/test-results/qwen_smoke_7a495877ab1f.json)全部保留。内联、业务参数校验、费用、幂等和UNKNOWN未放宽；共享字段描述已更新，云端仍使用当前原始Schema，不作Ollama专用内联。

后续CLI调用配置示例（**待运行**，不代表本轮成功）如下，须使用新输入键/未来期限及明确的新额度。P0不续跑本轮终态，不靠新请求清除已花费用记录：

```powershell
$env:MODEL_PROVIDER = 'ollama'
$env:MODEL_NAME = 'qwen3.5:27b'
$env:OPENAI_BASE_URL = 'http://127.0.0.1:11434/v1'
$env:MODEL_TEMPERATURE = '0.2'
$env:MODEL_THINK = 'false'
.\.venv\Scripts\python.exe -m content_planner.cli run --mode real --input var/demo.json --db var/qwen.sqlite3 --real-call-limit 10
```

.env不自动加载，真实失败不回退Mock。完成请求重放本轮已验证；两类正式动态业务验收仍待另行授权，本轮没有安排。没有P1恢复或远程推送。[实际结果及待验证项](docs/03-evaluation.md)。

## 上下文修复与线上比较边界

模型请求组织为：输入首位一份完整最新状态，后接原顺序的原生调用、function_call_output及供应商续接对象。适配器用对象身份追踪自己创建的状态消息，只移除该对象；不按角色/文本/JSON关键词删除其他消息，不做模型摘要。数据库和Trace仍完整记录每轮累计状态，没有回写裁剪。

实际运行的离线比较命令（仅MockTransport，不启动任务或执行工具）：

```powershell
.\.venv\Scripts\python.exe scripts/compare_model_context.py --recording examples/test-results/qwen_normal_0f1745fd4b32.json
```

[六轮体积对比](examples/test-results/context_replay_1ddfc0adb7cd/comparison.json)：第6次状态快照6→1、消息16→11；用同一compact JSON/UTF-8规则重新序列化，字符90,927→39,889，字节104,487→46,581。历史原始网络字节未保存，这些是统一重序列化体积，不是token或性能数据。最新费用/账本版本、报价/候选/产物及全部原生观察逐项一致；[旧请求11个文件及数据库哈希不变](examples/test-results/context-history-preservation-after.json)。

正常批次在线第6次实际请求也只有一份最新快照：11条消息、40,148字符、47,152 UTF-8字节；旧失败第6次为6份、16条、90,927字符、104,487字节，采用同一重序列化规则。新第6/7次draft请求分别17.516/17.578秒返回，未发生超时。模型动作/内容、请求键、期限、实时时钟及缓存不同，单次成功不能证明体积缩减是唯一原因或时延稳定。

脚本自行构造Limits()，仍为单次20秒、整次180秒，未调整超时。后续若改超时，必须核对实际Limits构造、记录limits和SDK request.timeout，不能只改环境变量就认定生效。上下文和一次正常通过不能自动证明专项或整体P0达标。

## 历史受限专项验收（2026-11-10，已执行并停止）

本轮只改实验脚本的场景选择/证据引用/额度及停止门禁，未改src、data、Schema、提示词或模型配置。门禁22项、全套140项实际通过。专项入口引用已确认的正常及重放产物，先记录缺预算/期限的零推理结果，再尝试budget与save_failure，每项最多10、批次最多20次。实际执行一次：

```powershell
.\.venv\Scripts\python.exe scripts/validate_qwen.py specialties --endpoint http://127.0.0.1:11434/v1 --model qwen3.5:27b --no-think --normal-index examples/test-results/qwen_normal_5f38146a433d.json
```

预算用例4次：真实估价OVER_BUDGET（已花1+剩余7=8，预算3，缺口5），观察进入下一次推理；模型仍尝试生成被拒，随后依据预算停止。保存故障用例7次：脚本成功且仅收费6一次，但draft缺script_artifact_id被拒后模型停止；没有实际保存执行、SAVE_TEMPORARY或重试，因此不能用此次参数纠正/停止替代专项通过。脚本和已花7保留，没有回执。尚余9次未使用，不自动重跑。

本轮usage输入97,702、输出2,047、合计99,749；HTTP耗时80.719秒。旧超时usage未知，项目完整累计usage仍未知。[原始请求/响应索引](examples/test-results/qwen_specialties_9333a7268207.json)记录实际脚本SHA256、20/180秒及各次wire timeout。[人工审阅与分离的修订建议](docs/06-content-review.md)未代签、未覆盖原始方案；本轮不推送。

## 历史生成故障实验：恢复已观察，盲测不合格

本节保留当轮附加盲测条件下的结论；该轨迹作为原题最低要求证据的适用范围，见[最终交付复核](docs/07-final-delivery.md)。

本轮独立生成失败只执行一个新请求，使用已有generate_fail_once，预算10、未来期限，模型/Schema/提示词/费用/业务Runtime及20/180秒不变。实际执行以下命令时的脚本摘要为`f1f30f019db77344f31e59413189314f6d91531767625649cb9caba1e6e824e2`：

```powershell
.\.venv\Scripts\python.exe scripts/validate_qwen.py generate_failure --endpoint http://127.0.0.1:11434/v1 --model qwen3.5:27b --no-think --normal-index examples/test-results/qwen_normal_5f38146a433d.json
```

实际链路：检索limit10被拒→改5检索成功→估价→生成FAILED/GENERATION_TEMPORARY→模型同报价重试成功→最新复估→6次额度结束，INCOMPLETE/REAL_CALL_LIMIT，未保存。已发生7=检索1+成功生成6，失败收费0；模拟540秒=检索60+失败240+成功240。usage输入49,585/输出805/合计50,390，HTTP合计37.703秒。[原始请求/响应](examples/test-results/qwen_generate_failure_40024f7694f5.json)、[Trace](examples/runs/real/run_fc04a04a8ca54959/trace.jsonl)。

验收缺陷：首次模型可见request_key带故障类别标签，故不能声称盲测合格或唯一由错误反馈触发。保留完整实际记录和执行脚本快照。当前入口改为`request_<随机UUID>`，修复后相关62项、完整150项离线通过（含实际SDK MockTransport首请求隔离检查），当前脚本摘要`693e879f202378024c0547f301cd77aa4f38407ad77815b119d160cd84fafd82`；**修复后未做在线重测，上方命令不是修复后通过证据**。不重复消耗6次、不续跑终态、不推送。历史保存故障结论不变，两种轨迹没有混称。

## 费用、时间与边界

- 模拟unit仅覆盖方案准备：检索1、basic生成6/premium生成10、保存1、估价0。真实模型账单、制作和投放另计。
- 预计总费用=所有已发生费用+必需剩余费用。一次检索+basic+保存为8；已花11后另生成basic并保存为18。报价ID只引用不可变规格，同规格新报价不会重复收生成费。
- 有效时钟=真实UTC当前时间+累计模拟工具耗时；工具不sleep。basic模拟360秒，若真实时钟再前进60秒，总计420秒。失败已开始的模拟耗时仍保留，成功复用不再增加模拟时间。
- 保存正常COMMIT确认后立即结束，不请求模型收尾。最后合法调用成功也可完成；失败/UNKNOWN且无额度就明确未完成，不补调用。
- UNKNOWN不代表免费、失败或未提交，立即冻结。P0不查证、不接管、不续跑；同键重放、inspect和export共用只读报告投影，读取请求快照及STARTED/UNKNOWN操作身份，不查询回执以判断未知结果、不回写旧JSON。未确认保存继续显示UNKNOWN；当前总额为null，7只是最后可信金额，待确认保存最高1 unit单列，不直接断言总额7或8。
- 仅在内存投影终态时termination_persisted=false，read_projection标明数据库原状态。重放的this_invocation_units=0只表示本次读取未新增收费，不代表历史未知操作免费。正常已确认任务仍返回原方案和回执。
- 30秒、竖屏和分镜标注不是通用门槛。P0硬需求只支持“必用素材:ID”“必含原文:文字”，其他明确需求保留并要求澄清，不静默降为偏好。
- 活动建议任务均NOT_STARTED；方案准备好供审阅不表示营销活动已执行。模板语义质量和实际效果未由测试证明。

## 配置与文档

.env.example默认统一为本地qwen3.5:27b、MODEL_THINK=false、temperature=0.2；只列变量，不自动加载，使用当前终端环境或CLI参数。单模型请求20秒、工具3秒与运行180秒均可配置。SDK/SQLite超时和提交前时钟检查限制后续执行；P0不引入强杀线程或通用外部工具，不能把同步阻塞调用宣传成实时系统硬保证。

- [需求](docs/01-requirements.md)
- [实际实现与局部取舍](docs/02-solution.md)
- [逐项评估、失败历史、待在线验证](docs/03-evaluation.md)
- [AI使用与贡献边界](docs/04-ai-usage.md)
- [复盘](docs/05-retrospective.md)
- [内容协作审阅、独立修订稿与用户确认记录](docs/06-content-review.md)
- [最终交付复核与评审入口](docs/07-final-delivery.md)
- [设计基线](plan.md)

P1未实现：自动回执查证、复杂恢复、跨进程失败续跑、并发接管、通用交付物和扩展视频规格。初版发布由用户明确授权；上传代码不代表真实模型验收通过。
