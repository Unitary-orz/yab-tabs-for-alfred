<img src="assets/icon.png" width="80" alt="Yab 应用图标">

# Yab Companion for Alfred

从 Alfred 搜索 Yab 标签、切换已有标签或空间，复制链接、标题或 Markdown 链接。

[English](README.md) · [下载工作流](./Yab%20Companion.alfredworkflow?raw=true)

## 安装

1. 安装 [Alfred 5 与 Powerpack](https://www.alfredapp.com/) 和 [Yab](https://yetanotherbrowser.com/)。
2. 在 Yab → Settings → Developers 安装 `yab` 命令行工具，并在 Settings → AI → Agents 中允许 Agent 使用 Yab，使工作流能访问本机 MCP 接口。
3. 准备 Python 3.9 或更新版本。启动脚本会检查常见的 Homebrew 和系统路径，也可以在工作流环境变量中通过 `PYTHON3` 指定解释器的完整路径。
4. 下载上方的 **Yab Companion.alfredworkflow**，双击导入 Alfred。如果 GitHub 打开文件页，选择 **Download raw file**。

无需第三方 Python 依赖，不调用 AI 模型。已检查 Alfred 5.8.1 与 Yab 0.45.2 的兼容性；后续 Yab 接口变化可能需要更新适配。公开版的界面提示使用英文，搜索支持中文。

## 使用

唤起 Alfred，输入 `yt`，或加上搜索词：

```text
yt webkit
yt example.com
yt design notes
yt 安全报告
```

可以匹配标题、网址、文件夹路径和空间名称。多个词需要全部匹配，顺序不限；支持中文及其他 Unicode 文本，英文不区分大小写。使用子串匹配，不提供拼写纠错式的模糊搜索。

| 按键 | 操作 |
| --- | --- |
| 回车 | 切到已有标签，或切换空间 |
| ⌥回车 | 复制链接 |
| ⌘回车 | 复制标题 |
| ⇧回车 | 复制 Markdown 链接 |

空间结果位于标签结果之后。输入空间名称并回车，切换后再次输入 `yt` 搜索该空间的标签。复制操作仅适用于标签，不会自动粘贴。

如需全局快捷键，在 Alfred Preferences 中设置工作流未绑定的 **Hotkey** 节点即可。External Trigger 的 bundle ID 为 `community.yab-companion.alfred`，trigger ID 为 `list_tabs`。

## 搜索范围

Yab 0.45.2 的相关接口只列出当前空间和共享标签，不包含其他空间收起的标签。请先切换空间，再搜索。工作流不会在后台轮流切换空间采集数据。

不包含隐私标签、空白标签和 Agent 标签，也不搜索书签或浏览历史。如果结果中的标签已关闭或移动，重新搜索即可；跨空间移动的标签需要先切换到新空间。

## 可选配置

在工作流环境变量中设置：

| 变量 | 用途 |
| --- | --- |
| `YAB_CLI` | 自动查找失败时，指定 `yab` 可执行文件的完整路径 |
| `PYTHON3` | 指定 Python 3.9+ 的完整路径 |

默认关键词为 `yt`，可在 Script Filter 节点中修改；界面内的提示仍以默认关键词 `yt` 为例。

## 本机数据

工作流通过 Yab 的公开工具读取标签标题、网址、文件夹路径和空间名称，不读取浏览器数据库，不模拟浏览器按键。

结果保存在 Alfred 工作流缓存目录中，两秒后重新读取；从终端运行时，默认目录为 `~/Library/Caches/community.yab-companion.alfred`。缓存文件创建时仅允许当前账户读写。缓存过期只影响复用，不会自动删除磁盘文件；成功执行切换操作后会清除缓存。复制内容也可能进入你使用的剪贴板管理器。

工作流本身不向模型或外部服务发送浏览数据；Yab 和网页的正常网络活动独立于此。Alfred 调试器可能显示标签标题和网址，分享日志前请脱敏。

## 排查问题

- 找不到 CLI：在 Yab 的 Developers 设置安装命令行工具，或设置 `YAB_CLI`。
- 无法连接或 Agents 未开启：打开 Yab，检查 Settings → AI → Agents，再重试。
- 找不到 Python：安装 Python 3.9+，或设置 `PYTHON3`。部分 Mac 的 `/usr/bin/python3` 需要先安装 Apple Command Line Tools。
- 标签没有显示：先检查当前空间及上方的搜索范围；新建或移动标签后，等待两秒再搜索。
- 操作等待确认：在 Yab 中完成确认后重试；工作流不会修改 Yab 权限。

卸载时在 Alfred Preferences 删除本工作流即可；如有剩余缓存，可从 Alfred 的工作流缓存目录清除。

## 开发

macOS 或 Linux 下使用 Python 3.9+：

```sh
python3 -m unittest discover -s tests -v
sh -n workflow/run.sh
python3 scripts/build.py
```

构建会在仓库根目录生成 `Yab Companion.alfredworkflow`。构建和离线测试只使用仓库文件及 Python 标准库，不需要安装 Alfred、Yab，也不需要网络。CI 检查离线测试和安装包与源码的一致性，不发布产物，不控制 macOS 应用。

修改后请在 Alfred 中实测搜索、回车、各个复制修饰键和空间切换，再分享工作流。测试仅使用虚构示例数据。贡献说明见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证与来源

代码和原创文档使用 [MIT 许可证](LICENSE)。Yab 图标不在其授权范围内，来源说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

这是独立的社区工作流，并非 Yab 或 Alfred 官方产品。使用的接口参见 [Yab 官方 MCP 项目](https://github.com/yetanotherbrowser/yab-mcp)。
