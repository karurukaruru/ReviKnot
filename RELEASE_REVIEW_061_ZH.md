# ReviKnot 0.6.1 安装与完整功能验收

本次改善公开版本的安装、快速开始和 MCP 接入；完整程序继续按 MIT 许可公开。

- Python3.11+ 的默认运行依赖现在包含 MCP，不需要单独安装 extra；Python3.10 保留基础命令兼容。
- 新增 setup_reviknot.py：环境创建、全部运行依赖安装、真实MCP发现、客户端配置生成和可选网页启动。
- 新增 run_reviknot.py：无需手动激活环境即可使用完整CLI。
- Codex显式注册、Cursor/Claude Code配置合并；已有其他服务保留，变更先备份。
- doctor 使用官方 SDK 连接真实 stdio 服务并发现四个工具，不把静态列表当健康检查。
- 网页工作台默认不限手动运行次数；--max-runs 为可选设置。每次实际调用仍由用户启动，不会自动无限循环。
- 英中README和QUICKSTART均提供可复制命令、预期结果和排错。

## 已执行验证

- 全新本地运行环境：Python3.14.5、OpenAI2.54.0、MCP2.3.0；默认安装后真实发现全部四个工具，provider_requests为0。
- 本地全量回归：707 passed，201 subtests passed，6 skipped；无失败。跳过项未计入通过数。
- 安装/配置合并/幂等与网页设置针对性检查：34 passed，1 skipped。
- 无默认三次运行限制：HTTP处理与实际网页脚本均检查了超过三次的手动运行和显式自定义上限。
- HTTP集成测试显式绕过机器代理，只连接本机虚拟API。

## 历史模型证据

0.6.0的Nebius/NVIDIA模型执行与96秒视频保留原始身份和记录。本次没有再次调用付费模型，不把安装改进描述成新一轮模型验收。消息检查与模型修复核心源码未修改。

公开CI：https://github.com/karurukaruru/ReviKnot/actions
快速开始：[QUICKSTART.md](QUICKSTART.md)
