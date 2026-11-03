# Yab Companion

Type `yt` in Alfred to search the current Yab space and shared tabs. Search title, URL, folder path, or space name; Chinese and other Unicode text are supported.

| Key | Action |
| --- | --- |
| Return | Switch to the existing tab or space |
| ⌥ Return | Copy URL |
| ⌘ Return | Copy title |
| ⇧ Return | Copy Markdown link |

For another space, type `yt` followed by its name, press Return, then search again. Tabs parked in other spaces are not searched automatically. Private and agent tabs are excluded. Clipboard actions do not paste automatically.

An optional global shortcut can be assigned to the Hotkey object. The default keyword can be changed in the Script Filter; the hints use `yt` as an example.

Requires Alfred 5 with Powerpack, Yab's CLI (Settings → Developers), allowed agents (Settings → AI → Agents), and Python 3.9+. Set `YAB_CLI` or `PYTHON3` in the workflow environment variables if automatic discovery fails. No model is called.

Results are refreshed after two seconds. Cache files remain on disk until cleared or replaced. If a tab closes or moves, search again; switch spaces first if it moved to another space. Complete any confirmation in Yab before retrying.

The workflow uses Yab's public MCP interfaces. It does not read the browser database or simulate browser keystrokes. Debugger output can contain tab titles and URLs; redact logs before sharing them.

代码使用 MIT 许可证；Yab 图标不在其授权范围内，参见 THIRD_PARTY_NOTICES.md。这是独立的社区工作流。

中文用法：输入 `yt 关键词` 搜索当前空间和共享标签；回车切换标签，⌥回车复制链接，⌘回车复制标题，⇧回车复制 Markdown 链接。搜索其他空间时，先输入其名称并回车切换，再次搜索。
