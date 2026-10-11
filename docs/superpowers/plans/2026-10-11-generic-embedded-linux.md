# 通用嵌入式 Linux 集合完善计划

**目标**：落实用户认可的“通用工程底座＋领域工作流＋平台适配”方案，将现有集合完善为可复用、可取证、可维护的嵌入式 Linux 工程工作流。保留 13 个技能与插件标识，不增加 MCU/RTOS 分支。

## 全局约束

- 保留之前未提交的技术修正、路由和引用结构。无提交、推送、安装、发布、烧写或板卡操作；本轮不改头像或处理发布包。
- 主干采用通用 Linux 方法；ARM32/ARM64 常见示例按架构标注，其他架构以目标 BSP/ABI 为准。不得从主机架构或厂商系列名推断目标能力。
- 中文说明，渐进读取。每个领域入口明确目标/输入、可继续与需补充的信息、证据分支、产物、成功/失败标准。复杂细节和案例进入条件参考，避免复制整份通用规范。
- 厂商参考仅补差异。没有精确 SDK 依据的私有命令不得继续以可直接执行的工具示例出现；改成能力发现/核对事项，保留官方来源和适用边界。
- 命令区分 HOST/TARGET/U-BOOT、完整命令/参数模板/代码片段；说明前置条件、预期观察和副作用。授权范围沿用已有用户意图，不增加普遍确认流程。
- 案例使用明确标注的教学输入/夹具，不捏造实机历史、构建成功或板测结果。每份关键工作流/案例给出依据和验证限制。
- 资料核对、工具/夹具测试、目标构建、板测为独立证据。静态检查和主机工具测试不能宣称验证目标驱动或硬件。

## 共享接口与所有权

根代理拥有 Agent 主提示词、plugin.json、两份 README、本计划、DEBUGGING_LESSONS、`tests/content-scenarios.md` 和以下通用参考：

- `embedded-debug-workflow/references/engineering-workflow.md`：跨领域任务/命令/交付契约。
- `embedded-debug-workflow/references/validation-policy.md`：来源、版本与实际验证记录要求。

所有路径均位于专家包的 `skills/` 下，测试路径另注明。各作者链接通用参考时使用从自身 SKILL.md 出发的真实相对路径。

### 工作单元 A：BSP、驱动与外设

拥有 `embedded-bsp-kernel/**`、`linux-device-drivers/**`、`embedded-peripherals/**`。

- [x] 加强目标识别/SDK/干净构建/启动/设备树/驱动开发的完整工作流；按设备未枚举、无匹配、probe 错误、defer 分支判断。
- [x] 补充流程参考与教学案例：DTB 未生效、probe defer、异步卸载死锁、streaming DMA 所有权。每案包含输入、候选原因、最小证据、修复边界、构建/回归步骤和未验证项。
- [x] 案例代码片段标为片段；没有目标内核构建环境时不虚构完整模块编译结果。保留 kernel API 版本边界与 devres/fd/DMA 生命周期规则。
- [x] 核对 BSP 厂商页，移除未获 SDK 依据的可执行私有工具名/固定路径保证，保留候选调查事项；链接新增参考并验证。

### 工作单元 B：诊断、性能与取证工具

拥有 `embedded-debug-workflow/**`（除根代理两份通用参考）、`embedded-perf-debug/**`、新 `tests/test_collect_evidence.py`。

- [x] 完善取证→假设→区分实验→修复→回归流程，补充 memcg OOM 教学案例。
- [x] TDD 实现 `embedded-debug-workflow/scripts/collect-evidence.sh`，只依赖 Linux POSIX shell/常见 BusyBox 工具，CLI：`--mode env|kernel|process --output NEW_DIR [--pid POSITIVE_PID] [--source-root SNAPSHOT_ROOT]`。
- [x] 默认 live 模式只在 Linux 收集；显式 `--source-root` 使用离线目录中的 proc/sys/etc 数据并标记 offline，不读取主机实时 proc 或调用主机 dmesg 冒充目标证据。process 模式要求正整数 PID。
- [x] 输出目录必须新建，不覆盖已有路径。写操作只发生在用户指定的新输出目录；不改变 sysctl、硬件、设备树、服务、模块或网络，不调用 sudo，不自动 SSH。
- [x] 有界读取版本、启动参数、OS、DT model/compatible、内存/swap等基础文件；kernel 模式采集有界 dmesg（live）或离线日志；process 模式采集 status/limits/wchan/cgroup/mountinfo 等相关文件。不默认导出 environ、完整 cmdline、core、内存映射或整棵 sysfs。
- [x] 文件/工具缺失、权限不足分别记录 manifest 状态，缺失可选数据不是目标正常。manifest 记录 mode、source kind/root、PID（适用时）、时间和每项状态；说明采样非原子、数据范围有限，不能自动定性 OOM/泄漏。工具完成可报告 partial，参数/输出/不支持 live 平台错误需非零退出。
- [x] 新测试先 RED，再验证离线文件采集/标签、缺失数据、PID校验、既有输出拒绝、有界输出和不读取主机实时数据；用 temp fixtures，不访问设备。`sh -n` 检查。可用 BusyBox 环境存在时再做额外测试，不假装完成未具备的环境检查。

### 工作单元 C：媒体、Qt 与图形

拥有 `media-pipeline-linux/**`、`qt-embedded-rendering/**`、`display-compositor-gpu/**`。

- [x] 增加任务契约与流程参考：协商能力→逐阶段计数/时间戳→背压/格式/资源定位→最小改动→同负载回归。
- [x] 增加多媒体掉帧教学案例，保留 Qt/QPA 与媒体/协议/数据的分流，以及平台未知可继续通用调查的规则。
- [x] 清理厂商参考和视觉扩展中没有实际 SDK 依据的 CLI/API 执行保证；用标准能力查询和具体 SDK 核对事项取代猜测工具命令，保留适用资料链接。
- [x] 保留 Qt RenderControl、LinuxFB/EGLFS 条件、MIPI endpoint 与 DMA/异步规则；所有新参考可达。

### 工作单元 D：通信、网络、数据与块设备

拥有 `embedded-networking/**`、`protocols-embedded/**`、`wireless-connectivity/**`、`data-storage-embedded/**`、`storage-hardware-io/**`。

- [x] 补全任务输入/层级分支/输出/验收；协议、传输、无线、数据与块设备证据继续分开。
- [x] 增加网络断连与持久化恢复教学案例（可采用两个 focused references），包含重连/部分读写/退避，以及 WAL/fsync/目录同步/掉电验证边界。
- [x] 命令和参数说明环境、用途、前置条件、预期观察和状态改变；有界普通文件 fio 的字节/时间边界与原始设备禁用默认规则不回退。
- [x] 不把来源不明的厂商私有命令当通用工具；主干与适配差异清楚，所有新参考可达。

## 根代理整合与验收

- [x] 保存本轮修改前快照与已有验证基线；在当前工作区按非重叠所有权分工。
- [x] 添加两份通用工程/验证参考并明确路由，泛化 Agent 与元数据的 Linux 范围，保留身份、13 名称、挂载和版本。
- [x] 更新 README 的能力、工具入口、案例性质、验证层次与使用方式；不宣称任何案例已经实机验证。
- [x] 编写内容评测矩阵，比较不加载/加载技能的任务行为，记录输入、源码/命令依据、主辅选择、正文读取、关键证据、错误/无效动作与输出验收；没有运行的比较保持未运行。
- [x] 运行新工具测试与原有 validator fixture 测试、真实包/引用可达性、所有 frontmatter YAML 与 Shell 语法检查；对缺失 SDK、BusyBox/QEMU 或板测环境明确限度。
- [x] 独立审查本轮 diff 与工具权限/输出/失败边界；交回原作者处理重要发现并复验。
- [x] 独立使用教学输入进行前向内容评测，不提供预期答案或伪造测量提升；交付实际产物、验证与剩余限制。

## 本轮实际验证记录

- 主机环境：macOS，Python 标准库测试与 `/bin/sh`；取证测试使用临时离线文件树和可控命令替身，不读取真实板卡日志。
- `python3 -m unittest discover -s tests -p 'test_*.py'`：审查修正后 48 项通过（28 项包校验器夹具、20 项取证工具夹具）。包含输出目录拒绝覆盖、离线来源隔离、PID、缺失/权限/截断状态、近期日志、生产命令失败、报告汇总/临时文件失败、OS-release 受限选源和 helper 引用边界。OS-release live 选源仅在临时文件树上进行函数级测试，不是目标 Linux 整体运行测试。
- `sh -n` 与 Python `py_compile`：通过。Ruby `YAML.safe_load` 检查 14 个 Agent/Skill frontmatter；63 份 Markdown 代码围栏结构通过；`git diff --check` 无问题。
- 真实包校验：保留 13 个技能名称及挂载，46 份参考文档可达，180 条本地 Markdown 关系与 59 个不同 Markdown 目标通过。显式脚本链接额外检查存在和包内路径，不执行脚本。
- 未进行：真实目标 SDK/内核/模块构建、QEMU、BusyBox 运行兼容测试、板卡功能/故障/性能回归、WorkBuddy 原生加载。当前环境未提供这些验证条件，不能将主机检查替代它们。

## 离线前向内容观察

使用两个隔离上下文，对照组只获得四份原始合成问题/事实，技能组获得相同输入并自行读取 Agent、所选技能及条件参考。没有给回答代理预期答案，未让两组互看输出。该观察是同一代理运行配置下的一批教学推理任务，不是 WorkBuddy 调用试验、量化基准或板卡实测。

| 合成输入的关键事实 | 对照组与技能组共同识别的主要方向 | 技能组实际读取与补充 |
|---|---|---|
| 引导选择旧 DTB，运行控制器禁用，预期是新 DTB | 先查实际启动产物和运行树，不能先改驱动 | BSP/外设与 DTB 案例；补打包输入、产物身份、枚举/绑定分步验收与恢复 |
| regulator get 返回 defer，provider 节点禁用 | 追 provider/运行资源描述，传播错误 | 驱动及资源参考、defer 案例；补版本/binding、后续 probe 失败回滚和重试验收 |
| remove 持锁同步取消 work，worker 取同锁且可能 requeue | 存在等待环，须同时处理重新入队 | 驱动生命周期与卸载案例；补生产者停止、IRQ/DMA 完成依赖、fd 跨解绑边界 |
| memcg OOM 日志，256 MiB 限额，接近限额，宿主仍有余量且 RSS 增长 | 限额 OOM 与宿主有余量可并存，RSS 增长不足以证明泄漏 | perf 与 OOM 案例；补有效祖先限额、计费归属、负载预算和同窗口回归 |

两组均给出了合理主要判断，未观察到足以声称解决率提升的差异。技能组在这批输出中更明确记录了工程产物、回归和未验证项；不能从四次观察推导稳定性、调用率或收益百分比。实际读取记录确认了这批文件正文的取得；不证明 WorkBuddy 宿主自动加载成功。八份案例中的 DMA、媒体、网络和持久化内容尚未做本轮双组前向比较。

## 独立审查与修正记录

- 内容审查确认 13 个技能路由保留、八份案例的合成性质与技术边界明确。发现 debug 旧示例的 shell 占位符、温度区域假设及相邻 IPC 推断需修正；由单独文档作者处理，避免与 collector 同文件竞争。驱动作者已补充异步卸载和 defer 案例未执行目标构建/板测的明确说明。
- 工具审查要求处理 live OS-release 标准链接兼容性，并用失败夹具修复 manifest/summary 汇总失败仍报告成功的问题。离线链接拒绝不放宽，数据项不可用仍按 partial 记录；报告输出/汇总失败需非零退出。修正后的复验结果将在下方记录。
- 复验完成：根代理整合运行 48 项测试与 Shell 语法检查通过；工具审查者对原发现及相邻行为复核通过，另运行五项针对性测试通过。内容审查者确认占位符、部署流程、温度采样及相邻 IPC 修正通过；剩余一处原始 zone 读数的文字不一致已由根代理按建议修正。文档作者提取的 15 个完整 shell 块仅作 `sh -n` 检查并通过，没有执行示例命令。
- 最终静态整合检查通过：真实包引用、14 个 YAML frontmatter、63 份 Markdown 代码围栏与差异空白检查。保留原 13 个技能标识与版本；没有安装、发布、提交、推送、真实 SDK 构建或板卡操作。
