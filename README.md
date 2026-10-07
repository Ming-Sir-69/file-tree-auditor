# File Tree Auditor · 文件结构审计与变动追踪

扫描一个本地项目目录，生成文件树、变动对比、每日/月度归档和结构化 JSON 记录。适合需要整理项目材料、查看文件变化或准备目录交接的使用者。

## 快速开始

### 使用源码

在下载或克隆的仓库根目录，用 Python 3 执行：

```sh
python3 scripts/file-tree-auditor.py --target "/path/to/project"
# 可选：跳过本次差异对比
python3 scripts/file-tree-auditor.py --target "/path/to/project" --no-diff
```

将目标路径替换为自己有权扫描的目录。脚本当前直接导入 Python 标准库；仓库另保留了 [requirements.txt](requirements.txt)，不要据此推断尚未实现的图表能力。

### 获取已发布程序

已观察到的最新归档为 [v2.1](https://github.com/Ming-Sir-69/file-tree-auditor/releases/tag/v2.1)，可按系统与架构下载命名附件：

| 系统 | 附件 |
| --- | --- |
| Linux x64 | `file-tree-auditor-linux-x64` |
| macOS Apple Silicon | `file-tree-auditor-macos-arm64` |
| Windows x64 | `file-tree-auditor-windows-x64.exe` |

命名附件与 GitHub 自动打包的源码不同。此页的源码参数已按当前主分支核对；Release 二进制的实际运行兼容性与参数一致性尚未重新验证。

## 产出与目录入口

报告会写入被扫描的 `--target` 目录，后续运行会更新相应报告和 `_data_structure.json` 基线。首次没有历史 JSON 时无法形成完整增量对比；`--no-diff` 仍会生成其他报告并更新 JSON 基线。请先在目标目录的副本中了解输出方式。

| 文件 | 用途 |
| --- | --- |
| `<目录名>_文件结构.md` | 文件树 |
| `<目录名>_差异对比.md` | 与上次基线的新增、移除、修改与移动对比 |
| `<目录名>_今日新增.md` | 按当天修改时间筛选的文件清单（含修改，非仅新建） |
| `<目录名>_月度归档.md` / `<目录名>_每日归档.md` | 按月份或日期组织的目录视图 |
| `<目录名>_加班输出资料.md` | 以文件时间与固定日期规则划分的参考记录 |
| `_data_structure.json` | 供下次比较及程序读取的文件元数据 |

实现入口：[scripts/file-tree-auditor.py](scripts/file-tree-auditor.py)。构建定义：[.github/workflows/build.yml](.github/workflows/build.yml)。

## 限制与状态

- 分析依据是文件系统元数据与路径，不是 Git 提交历史或文档内容审计；文件时间不能单独证明实际工作时长、作者或内容质量。
- 当前加班分类日期范围硬编码为 2025-07-01 至 2026-06-26，并使用固定节假日/调休规则；其他年份须核对实现，不能把报告直接当成考勤依据。
- 当前排除集合包含 `.git`、`__pycache__`、`node_modules`、常见虚拟环境与部分 IDE 目录，并非所有敏感路径都会自动排除。报告会列出目标目录的路径与时间，分享前请检查内容。
- 本次仅核对源码入口与 Release 元数据，未扫描用户目录、运行代码或验证二进制。

## 贡献与维护

欢迎通过本仓库 Issue 或 Pull Request 补充可复现步骤、纠正文档或说明兼容问题；请附环境、操作步骤和预期结果，并保留原作者与引用来源。

文档与导航维护：[Ming-Sir-69](https://github.com/Ming-Sir-69)。此署名只标识仓库维护，不改变项目、资料或第三方组件的权属。

## 许可

当前文件树未发现 LICENSE 或 NOTICE。此 README 的维护署名不新增开源、商用或资料再分发授权；具体授权范围待维护者确认。
