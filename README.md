<picture>
  <source media="(prefers-color-scheme: dark)" srcset="readme-assets/header-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="readme-assets/header-light.svg">
  <img alt="File Tree Auditor · 文件变化地图 · ✦ EricMingle69" src="readme-assets/header-light.svg" width="100%">
</picture>

<p align="center">
  <a href="README.md">简体中文</a> · <a href="README.en.md">English</a> · <a href="PERSONAL-NOTICE.md">✦ EricMingle69</a>
</p>

# File Tree Auditor · 文件变化地图

扫描本地项目，生成文件树、增量差异与日期视图。
适合资料整理、结构交接和文件变化追踪；分析依据是路径与文件元数据。

## 用源码开始

准备 Python 3，在仓库根目录执行：

```sh
python3 scripts/file-tree-auditor.py --target "/path/to/project"
python3 scripts/file-tree-auditor.py --target "/path/to/project" --no-diff
```

将路径替换为有权扫描的目录。建议先用目录副本了解输出方式。
脚本直接导入标准库；[requirements.txt](requirements.txt)不代表额外图表能力已实现。

## 它会写入什么

报告写入 `--target` 目录，后续运行更新报告和 `_data_structure.json`。

| 输出 | 内容 |
| --- | --- |
| `<目录名>_文件结构.md` | 文件树 |
| `<目录名>_差异对比.md` | 与旧基线比较新增、移除、修改、移动 |
| `<目录名>_今日新增.md` | 当天修改时间命中的文件，包含旧文件修改 |
| `<目录名>_月度归档.md` / `每日归档.md` | 日期组织视图 |
| `<目录名>_加班输出资料.md` | 固定日期规则参考记录 |
| `_data_structure.json` | 下次比较的元数据基线 |

首次没有旧 JSON 时不能形成完整增量对比；`--no-diff` 仍更新其他报告与 JSON。

## 已发布程序

[v2.1](https://github.com/Ming-Sir-69/file-tree-auditor/releases/tag/v2.1)有 Linux x64、macOS arm64、Windows x64 命名附件。
二进制兼容性与源码参数是否一致需结合实际版本确认，下载源码压缩包不等于取得这些程序。

## 判断边界

文件时间不能单独证明工作时长、作者或质量，报告也不是 Git 历史或内容审计。
加班分类当前日期范围固定为 2025-07-01 至 2026-06-26，并使用固定节假日规则。
排除项不覆盖所有敏感路径；分享报告前检查其中的目录与时间。

## 实现与许可

[脚本](scripts/file-tree-auditor.py)提供入口，[构建定义](.github/workflows/build.yml)记录打包方式。
当前没有覆盖原代码的 LICENSE；复用与再分发权限需确认。

---

文档维护：**✦ EricMingle69** · [Ming-Sir-69](https://github.com/Ming-Sir-69)  
[个人标识、许可与权限说明](PERSONAL-NOTICE.md) · 明暗页眉随 GitHub 主题自动切换。
