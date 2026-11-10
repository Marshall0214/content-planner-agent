# 内容任务规划 Agent

Python 原生单 Agent + SQLite 三表 + CLI。四个本地工具负责素材检索、脚本生成、成本估算和方案保存。

代码仓库：[Marshall0214/content-planner-agent](https://github.com/Marshall0214/content-planner-agent)。

**当前状态（2026-11-10）：工程与离线验证已完成，65项测试通过；真实模型端到端验收未运行，因此不能宣称整个P0验收达标。** 两类真实动态路径和人类内容审阅仍待完成。[逐项评估与证据](docs/03-evaluation.md)。

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
.\.venv\Scripts\python.exe -m pytest tests -q --junitxml=examples/test-results/final.xml
.\.venv\Scripts\python.exe scripts/collect_examples.py
```

pytest的临时目录固定为.cache/pytest，每次测试会清理这个专用目录。collect_examples只执行offline_mock，自动产生正常、信息不足、预算反馈、工具故障、重复和边界的12次实际CLI记录，并打印批次索引路径。examples只放实际执行产生的记录；输入模板不放这里。最新已核对批次：[batch_ab59870dd4bf.json](examples/test-results/batch_ab59870dd4bf.json)。

```powershell
# 模拟保存首次明确失败；模型是离线脚本，不能用作真实动态证据
.\.venv\Scripts\python.exe -m content_planner.cli run --mode offline_mock --input var/demo.json --db var/failure.sqlite3 --fixture save_fail_once
```

离线场景basic为常规流程；budget_adjust是显式的“先高级后降本”测试脚本，不代表真实模型会这样做；stop_on_failure用于停止路径。真实适配器没有这些预写决策分支。故障按工具实际执行序号触发，复用和参数拒绝不消耗实际尝试。

退出码：0已确认完成；2待补充；3未完成（含UNKNOWN）；4输入/请求键冲突；5配置或明确基础设施失败。非0是被验证的业务结果之一，不等于测试失败。

## 真实模型：已实现适配器，尚未在线验收

真实模式不会自动回退Mock；缺配置时明确报错且不调用API。下列是**待在线运行示例**，不属于已完成真实验证：

```powershell
$env:MODEL_PROVIDER = 'openai'
$env:MODEL_NAME = '<你明确指定且支持Responses工具调用的模型ID>'
$env:OPENAI_API_KEY = '<只在本地设置，不提交>'
# 可选OPENAI_BASE_URL须明确指定并支持Responses协议，不承诺任意兼容地址可用
.\.venv\Scripts\python.exe -m content_planner.cli run --mode real --input var/demo.json --db var/real.sqlite3 --real-call-limit 12
```

需要明确提供模型ID、端点（如有）、可用密钥、调用次数与费用额度。--real-call-limit是单次运行的实际API请求上限，SDK自动重试关闭；同时受默认12次模型/10次工具/180秒运行保护约束。不同模式绑定不同请求身份；在线验收使用新键和新的绝对截止时间。

建议在线材料包括正常、超预算反馈、工具失败/部分成功三种完整运行，加信息不足与重放入口记录。预计约15–30次模型请求只是规划估计；若预留最多6次运行、每次12次请求，硬上界为72次，仍须用户明确授权额度；不保证取得合格路径。每次输出上限4000 token，真实费用取决于模型、输入和usage，当前不报价。规则、协议和停止条件见[评估文档](docs/03-evaluation.md)。

## 费用、时间与边界

- 模拟unit仅覆盖方案准备：检索1、basic生成6/premium生成10、保存1、估价0。真实模型账单、制作和投放另计。
- 预计总费用=所有已发生费用+必需剩余费用。一次检索+basic+保存为8；已花11后另生成basic并保存为18。报价ID只引用不可变规格，同规格新报价不会重复收生成费。
- 有效时钟=真实UTC当前时间+累计模拟工具耗时；工具不sleep。basic模拟360秒，若真实时钟再前进60秒，总计420秒。失败已开始的模拟耗时仍保留，成功复用不再增加模拟时间。
- 保存正常COMMIT确认后立即结束，不请求模型收尾。最后合法调用成功也可完成；失败/UNKNOWN且无额度就明确未完成，不补调用。
- UNKNOWN不代表免费、失败或未提交，立即冻结。P0不查证、不接管、不续跑；普通同键读取只展示已有持久化事实。数据库不确定时不以旧JSON覆盖潜在提交。
- 30秒、竖屏和分镜标注不是通用门槛。P0硬需求只支持“必用素材:ID”“必含原文:文字”，其他明确需求保留并要求澄清，不静默降为偏好。
- 活动建议任务均NOT_STARTED；方案准备好供审阅不表示营销活动已执行。模板语义质量和实际效果未由测试证明。

## 配置与文档

.env.example只列变量，不自动加载；使用当前终端环境或CLI参数。单模型请求20秒、工具3秒与运行180秒均可配置。SDK/SQLite超时和提交前时钟检查限制后续执行；P0不引入强杀线程或通用外部工具，不能把同步阻塞调用宣传成实时系统硬保证。

- [需求](docs/01-requirements.md)
- [实际实现与局部取舍](docs/02-solution.md)
- [逐项评估、失败历史、待在线验证](docs/03-evaluation.md)
- [AI使用与贡献边界](docs/04-ai-usage.md)
- [复盘](docs/05-retrospective.md)
- [设计基线](plan.md)

P1未实现：自动回执查证、复杂恢复、跨进程失败续跑、并发接管、通用交付物和扩展视频规格。初版发布由用户明确授权；上传代码不代表真实模型验收通过。
