<img src="assets/icon.png" width="80" alt="Yab application icon">

# Yab Companion for Alfred

Search Yab tabs from Alfred, switch to an existing tab or space, and copy a tab's URL, title, or Markdown link.

[中文说明](README.zh-CN.md) · [Download workflow](./Yab%20Companion.alfredworkflow?raw=true)

## Install

1. Install [Alfred 5 with Powerpack](https://www.alfredapp.com/) and [Yab](https://yetanotherbrowser.com/).
2. In Yab → Settings → Developers, install the `yab` command-line tool. Allow agents in Settings → AI → Agents so the workflow can use Yab's MCP interface.
3. Have Python 3.9 or later available. The launcher checks common Homebrew and system locations. You can also set `PYTHON3` to your interpreter's full path in the workflow environment variables.
4. Download **Yab Companion.alfredworkflow** above and double-click it to import into Alfred. If GitHub opens the file page, use **Download raw file**.

The workflow has no third-party Python dependencies and does not call an AI model. It uses Yab's local MCP server. Compatibility has been checked with Alfred 5.8.1 and Yab 0.45.2; future Yab interface changes may require an update.

## Use

Open Alfred and type `yt`, optionally followed by search terms:

```text
yt webkit
yt example.com
yt design notes
yt 安全报告
```

Search matches titles, URLs, folder paths, and space labels. Multiple terms must all match; terms can appear in any order. Matching is case-insensitive and supports Chinese and other Unicode text. This is substring matching, not typo-tolerant fuzzy search.

| Action | Key |
| --- | --- |
| Switch to the existing tab or space | Return |
| Copy URL | ⌥ Return |
| Copy title | ⌘ Return |
| Copy Markdown link | ⇧ Return |

Space results appear after tab results. Type a space's name, press Return, then type `yt` again to search its tabs. Modifier-copy actions apply to tab results only. Clipboard actions do not paste automatically.

To open the search with a global shortcut, set the workflow's unassigned **Hotkey** object in Alfred Preferences. External trigger: bundle ID `community.yab-companion.alfred`, trigger ID `list_tabs`.

## Search scope

Yab 0.45.2 exposes the current space's tabs and shared tabs through the interfaces used here. Tabs parked in other spaces are not included. Switch spaces first to search them. The workflow does not cycle through spaces in the background to collect tabs.

Private tabs, blank tabs, and agent-owned tabs are excluded. Bookmarks and browsing history are outside this workflow's scope. If a tab is closed or moved after the results load, search again; if it moved to another space, switch there first.

## Configuration

Optional variables under the workflow's environment settings:

| Variable | Purpose |
| --- | --- |
| `YAB_CLI` | Full path to the `yab` executable, if automatic discovery does not find it |
| `PYTHON3` | Full path to Python 3.9+ |

The default keyword is `yt`; change it in the Script Filter object if it conflicts with another workflow. The in-app hints use `yt` as the default keyword.

## Local data

The workflow reads tab titles, URLs, folder paths, and space names through Yab's public tools. It does not read Yab's database or simulate browser keystrokes.

Results are cached locally with a two-second freshness interval in Alfred's workflow cache directory, or `~/Library/Caches/community.yab-companion.alfred` when run outside Alfred. Cache files are created with owner-only permissions. A cache file can remain on disk after it expires; expiration controls reuse, not automatic deletion. Successful actions clear it. Clipboard copies also enter any clipboard manager you use.

The workflow itself does not send browsing data to a model or external service. Normal Yab and website network activity is separate. Alfred's debugger can display result titles and URLs; redact those before sharing a log.

## Troubleshooting

- **Yab CLI not found:** install the CLI in Yab's Developers settings, or set `YAB_CLI`.
- **Cannot connect / agents are off:** open Yab, check Settings → AI → Agents, and retry.
- **Python 3 not found:** install Python 3.9+ or set `PYTHON3`. On some Macs, `/usr/bin/python3` requires Apple's Command Line Tools.
- **A tab is missing:** check the current space and the scope above. Wait two seconds and search again after opening or moving tabs.
- **An action needs confirmation:** complete it in Yab, then retry. The workflow does not change Yab's permissions.

To uninstall, remove the workflow in Alfred Preferences. Any remaining cache can be removed from Alfred's workflow cache directory.

## Development

Build and test with Python 3.9+ on macOS or Linux. Yab and Alfred are only needed for live checks.

```sh
python3 -m unittest discover -s tests -v
sh -n workflow/run.sh
python3 scripts/build.py
```

The build produces `Yab Companion.alfredworkflow` in the repository root. It uses only repository files and the Python standard library; archive metadata is fixed for reproducible builds. CI runs the offline tests and checks that the committed workflow matches the source. CI does not publish anything or exercise the macOS apps.

Before sharing a changed package, test search, Return, each copy modifier, and a space switch in Alfred. Offline fixtures contain synthetic example data, never exported browser state. See [CONTRIBUTING.md](CONTRIBUTING.md).

```text
workflow/        Runtime and shell launcher
scripts/build.py Workflow metadata and deterministic packaging
tests/           Offline behavior and packaging checks
assets/icon.png  Yab application icon
```

## License and attribution

Project code and original documentation are available under the [MIT license](LICENSE). The Yab application icon is excluded; see [third-party notices](THIRD_PARTY_NOTICES.md).

This is an independent community project, not an official Yab or Alfred product. It uses the interface documented by [Yab's official MCP project](https://github.com/yetanotherbrowser/yab-mcp).
