# 技能路由与参考入口修改计划

**目标**：按用户认可的提示词分析，明确选择、实际读取与应用技能的流程；修正竞争路由和路径说明，让现有 13 个技能及参考资料可发现、可验证。

**约束**：保留插件标识、版本和 13 个技能名称/挂载；保留上轮技术修正；本轮不处理头像、许可证或打包发布，不安装 WorkBuddy、不访问目标板，不提交或推送。技能说明用简洁中文；不假设宿主具有未证实的调用 API。已有授权无需重新询问。

## 分工与共享接口

1. 根代理：Agent 主提示词、两份 README、计划与错误账本。修正相对 Agent 的链接说明，增加主技能选择/读取成功/辅助加载/证据变化重分流/加载失败处理；将内核要求限定在相关任务。
2. 内核与诊断：只改 BSP、driver、peripherals、perf、debug、network 六个 SKILL.md。简化 description、明确主辅边界、链接所有适用参考。debug 入口链接下述 app-runtime.md。
3. 媒体与运行环境：只改 media、Qt、display、storage 四个技能及其 references，并创建 `embedded-debug-workflow/references/app-runtime.md`。MIPI 从 storage 移到 `media-pipeline-linux/references/mipi-bringup.md`；Docker/线程/异步/nginx 从 storage 移到 app-runtime.md；OpenCV/NPU 从 display 主干移到 `display-compositor-gpu/references/vision-inference.md`，作为明确的嵌入式视觉扩展保留。
4. 数据与通信：只改 data-storage、protocols、wireless 三个 SKILL.md。按数据持久性/应用协议/无线链路区分主辅，并链接已有参考。
5. 校验：只改 `scripts/validate_expert.py`、`tests/test_validate_expert.py`、`tests/expert-scenarios.md`。增加有向引用可达性检查：每个技能 references 下的文档必须能从该技能入口经本地链接到达；不要求全部直接链接，也不据此声称宿主实际加载。新增孤立参考/跨参考可达的 fixture 测试先 RED 后 GREEN。场景表补充主技能、辅助读取条件、实际读取证据，原生 WorkBuddy 结果保持未运行。

## 执行与验收

- [x] 保存本轮修改前快照，记录静态缺陷与基线路由；不虚构模型行为失败。
- [x] 并行完成四块非重叠修改，根代理整合主提示词和文档。
- [x] 所有 description 使用真实任务边界，去除冗余关键词堆叠和妨碍跨领域合作的硬排除。
- [x] 参考入口提供具体相对路径与读取条件；移出内容有明确归属，不丢失已有维护/测试限制。
- [x] 路由涵盖：未枚举设备/已枚举 probe 失败、未知卡死/已知 OOM、视频掉帧/Qt EGL、MQTT/TCP/WiFi、数据写满/块设备、应用线程/内核锁、容器部署/容器 OOM、视觉推理扩展。
- [x] 运行 fixture 测试、真实包校验、完整 frontmatter YAML 解析与 diff 空白检查。
- [x] 独立前向测试按新提示词实际读取文件并记录所选技能/参考；不提供预期答案；将离线工具读取与 WorkBuddy 原生调用区分。
- [x] 独立审查本轮差异，必要时交回原作者修正并复验，交付简短变更/验证/限制说明。

## 验证记录与限制

- 修改前快照保留在本机临时目录；基线代理仅做拟选择和歧义观察，未取得完整技能正文。这与后续要求提供初步技术指导的前向任务不同，不能用于声称调用成功率提高多少。
- 根代理执行 `python3 -m unittest discover -s tests -p 'test_*.py' -v`：25 项 fixture 测试通过。新增孤立参考用例先出现预期 RED，再在可达性检查实现后 GREEN；测试不是匹配提示词句子的断言。
- 最终 `python3 scripts/validate_expert.py embedded-software-architect` 通过：保留 13 个技能注册，100 处本地引用关系，44 个唯一目标文件（13 个技能入口与 31 份参考）。每个技能的参考文档均可从自己的入口经本地链接到达。
- Ruby `YAML.safe_load` 解析全部 14 个指令 frontmatter 并检查必需字符串、名称和长度；最新 Qt 描述另经作者同类检查。`py_compile`、本轮相对链接检查和 `git diff --check` 通过。
- 独立代理未读取计划、场景验收表或预期答案，处理 17 个实际问题形式的离线场景，记录取得 13 份技能正文和 12 份适用参考，允许已读取内容复用。根代理审阅全部答复与读取清单；主路由覆盖全部 13 个技能，Qt 托管 TLS、应用线程/内核锁、容器 OOM 等交叉场景符合预期。Qt 和 MIPI 更新后分别刷新了相应读取。工具建议均未执行，此结果是单次离线观察，不是 WorkBuddy 原生调用记录或跨模型稳定性统计。
- 独立差异审查确认路径基准、正文加载/缓存/失败流程、主辅路由与内容迁移。其发现的 MIPI 参考与场景细节不一致已交回原作者，补充按目标 binding 核对 endpoint/lane/frequency 的条件清单，限定复查通过。
- 原生 WorkBuddy 导入、技能发现/选择、完整正文注入和缓存行为仍未验证；19 个宿主场景的实际结果仍标记未运行。本轮未安装、打包、发布、改版本或操作目标板；头像和许可证打包问题不在本轮范围。
