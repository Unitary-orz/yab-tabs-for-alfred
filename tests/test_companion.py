import json
import os
from pathlib import Path
import plistlib
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "workflow"))
sys.path.insert(0, str(ROOT / "scripts"))
import companion as c
import build


class SearchScenarios(unittest.TestCase):
    def setUp(self):
        self.data = {"spaceId": "space-1", "spaces": [
            {"id": "space-1", "name": "工作"}, {"id": "space-2", "name": "阅读"}], "tabs": [
            {"id": "abc12345", "title": "季度 安全报告", "url": "https://example.com/reports",
             "folderPath": "项目", "inEverySpace": False, "active": False},
            {"id": "def12345", "title": "Reference [2026]", "url": "https://example.org/a_(b)?x=1",
             "folderPath": "", "inEverySpace": True, "active": True}]}

    def test_chinese_multiple_keywords_find_tab(self):
        row = c.list_items(self.data, "报告 项目")["items"][0]
        self.assertTrue(row["valid"])
        self.assertEqual(json.loads(row["arg"])["id"], "abc12345")
        self.assertIn("工作", row["subtitle"])

    def test_url_search_and_copy_preserve_content(self):
        row = c.list_items(self.data, "EXAMPLE.org")["items"][0]
        self.assertEqual(row["mods"]["alt"]["arg"], self.data["tabs"][1]["url"])
        self.assertEqual(row["mods"]["cmd"]["arg"], "Reference [2026]")
        self.assertEqual(row["mods"]["shift"]["arg"], r"[Reference \[2026\]](<https://example.org/a_(b)?x=1>)")

    def test_normalized_full_width_query(self):
        row = c.list_items(self.data, "Ｒｅｆｅｒｅｎｃｅ")["items"][0]
        self.assertEqual(json.loads(row["arg"])["id"], "def12345")

    def test_space_result_cannot_be_copied_as_a_tab(self):
        row = c.list_items(self.data, "阅读")["items"][0]
        self.assertEqual(json.loads(row["arg"]), {"kind": "space", "id": "space-2"})
        self.assertTrue(all(not mod["valid"] for mod in row["mods"].values()))

    def test_no_match_explains_current_scope(self):
        row = c.list_items(self.data, "does-not-exist")["items"][0]
        self.assertFalse(row["valid"])
        self.assertIn("工作 and shared tabs", row["subtitle"])

    def test_empty_query_prefers_active_tab_and_lists_spaces_last(self):
        rows = c.list_items(self.data, "")["items"]
        self.assertEqual(json.loads(rows[0]["arg"])["id"], "def12345")
        self.assertEqual(json.loads(rows[-1]["arg"])["kind"], "space")

    def test_native_text_handles_commas_and_excludes_agents(self):
        result = {"content": [{"type": "text", "text":
            "abc12345 [user] (in front) A, B, https://example.com/one,two\n"
            "def12345 [agent] Agent tab, https://example.org/"}]}
        self.assertEqual(c.parse_live_tabs(result), {
            "abc12345": {"title": "A, B", "url": "https://example.com/one,two"}})

    def test_parenthesized_title_is_preserved(self):
        result = {"content": [{"type": "text", "text":
            "abc12345 [user] (in front) (Draft) Report, https://example.com/"}]}
        self.assertEqual(c.parse_live_tabs(result)["abc12345"]["title"], "(Draft) Report")


class NativeScenarios(unittest.TestCase):
    def test_pagination_includes_every_page_and_excludes_agent_tabs(self):
        class Client:
            def data(self, name, args):
                offset = args.get("offset", 0)
                rows = [{"id": str(i), "url": "https://example.com", "title": "Example"}
                        for i in range(offset, offset + (50 if offset == 0 else 3))]
                rows[0]["ownedByTask"] = True
                return {"activeSpaceId": "s", "spaces": [{"id": "s", "name": "Work"}],
                        "tabs": rows, "hasMoreTabs": offset == 0}
            def call(self, name, args):
                return {"content": []}
        self.assertEqual(len(c.read_snapshot(Client())["tabs"]), 51)

    def test_space_changed_during_pagination_is_rejected(self):
        class Client:
            def data(self, name, args):
                return {"activeSpaceId": "other" if args.get("offset") else "initial",
                        "spaces": [], "tabs": [], "hasMoreTabs": not args.get("offset")}
        with self.assertRaises(c.YabError):
            c.read_snapshot(Client())

    def test_switch_uses_action_preview_version_and_waits_for_ui(self):
        previews = []
        class Client:
            def data(self, name, args):
                previews.append((name, args))
                if name == "native_apply":
                    self.applied = True
                    return {"status": "verified"}
                return {"activeSpaceId": "target" if getattr(self, "applied", False) else "initial",
                        "resourceVersion": "action-preview-version"}
        c.switch_space(Client(), "target")
        self.assertEqual(previews[0][1]["action"], "space.switch")
        apply = next(args for name, args in previews if name == "native_apply")
        self.assertEqual(apply["expectedVersion"], "action-preview-version")
        self.assertEqual(apply["target"], {"kind": "space", "id": "target"})

    def test_action_uses_tab_identity_without_opening_url(self):
        calls = []
        class Client:
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def call(self, name, args): calls.append((name, args))
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"alfred_workflow_cache": directory}):
                with mock.patch.object(c, "MCP", Client), mock.patch.object(c, "switch_space") as switch:
                    c.action(json.dumps({"kind": "tab", "id": "abc12345", "spaceId": "s", "shared": False}))
        switch.assert_called_once()
        self.assertEqual(calls, [("show", {"tab": "abc12345"})])

    def test_invalid_actions_are_rejected_before_connecting(self):
        for payload in ([], {}, {"kind": "tab", "id": "abc"}, {"kind": "space", "id": ""}):
            with self.subTest(payload=payload), mock.patch.object(c, "MCP") as connect:
                with self.assertRaises(c.YabError):
                    c.action(json.dumps(payload))
                connect.assert_not_called()


class CacheAndTransportScenarios(unittest.TestCase):
    def test_cache_is_private_and_fresh_results_are_reused(self):
        data = {"fetched": c.time.time(), "spaceId": "s", "spaces": [], "tabs": []}
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"alfred_workflow_cache": directory}):
                with mock.patch.object(c, "MCP"), mock.patch.object(c, "read_snapshot", return_value=data) as fetch:
                    self.assertEqual(c.snapshot(), data)
                    self.assertEqual(c.snapshot(), data)
                    fetch.assert_called_once()
                self.assertEqual((Path(directory) / "tabs.json").stat().st_mode & 0o777, 0o600)

    def test_broken_cache_is_refetched(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "tabs.json").write_text("[]")
            data = {"fetched": c.time.time(), "spaceId": "s", "spaces": [], "tabs": []}
            with mock.patch.dict(os.environ, {"alfred_workflow_cache": directory}):
                with mock.patch.object(c, "MCP"), mock.patch.object(c, "read_snapshot", return_value=data):
                    self.assertEqual(c.snapshot(), data)

    def test_stdio_mcp_accepts_structured_tool_results(self):
        # A local synthetic MCP server, not Yab and not a model.
        server = '''import json, sys
for line in sys.stdin:
    r = json.loads(line)
    if 'id' not in r: continue
    if r['method'] == 'initialize': result = {'protocolVersion': '2024-11-05', 'capabilities': {}}
    else: result = {'structuredContent': {'status': 'verified'}, 'content': []}
    print(json.dumps({'jsonrpc': '2.0', 'id': r['id'], 'result': result}), flush=True)
'''
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "server.py"
            script.write_text(server)
            command = Path(directory) / "fake-yab"
            command.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + " " + shlex.quote(str(script)) + "\n")
            command.chmod(0o700)
            with mock.patch.dict(os.environ, {"YAB_CLI": str(command)}):
                with c.MCP() as client:
                    self.assertEqual(client.data("native_apply", {}), {"status": "verified"})


class PackagingScenarios(unittest.TestCase):
    def test_modifier_routes_and_literal_clipboard_content(self):
        d = build.metadata()
        search = next(o for o in d["objects"] if o["type"].endswith("input.scriptfilter"))
        destinations = {o["uid"]: o["type"] for o in d["objects"]}
        routes = {r["modifiers"]: destinations[r["destinationuid"]] for r in d["connections"][search["uid"]]}
        self.assertTrue(routes[0].endswith("action.script"))
        for key in (524288, 1048576, 131072):
            self.assertTrue(routes[key].endswith("output.clipboard"))
        clipboard = next(o for o in d["objects"] if o["type"].endswith("output.clipboard"))
        self.assertFalse(clipboard["config"]["autopaste"])
        self.assertTrue(clipboard["config"]["ignoredynamicplaceholders"])

    def test_archive_is_reproducible_and_contains_only_the_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            first = build.build(Path(directory) / "first.alfredworkflow")
            second = build.build(Path(directory) / "second.alfredworkflow")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as package:
                self.assertIsNone(package.testzip())
                self.assertEqual(set(package.namelist()), {
                    "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "VERSION",
                    "companion.py", "run.sh", "icon.png", "info.plist"})
                metadata = plistlib.loads(package.read("info.plist"))
                self.assertEqual(metadata["version"], package.read("VERSION").decode().strip())
                self.assertEqual(metadata["bundleid"], c.BUNDLE)
                self.assertEqual(package.read("companion.py"), (ROOT / "workflow/companion.py").read_bytes())

    def test_launcher_preserves_unicode_and_shell_metacharacters_as_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            interpreter = Path(directory) / "fake python"
            interpreter.write_text("#!/bin/sh\nprintf '%s\\n' \"$3\"\n")
            interpreter.chmod(0o700)
            query = '报告 $(touch SHOULD_NOT_EXIST) `echo test` "quotes"'
            env = dict(os.environ, PYTHON3=str(interpreter))
            output = subprocess.check_output(["/bin/sh", str(ROOT / "workflow/run.sh"), "list", query], env=env, cwd=directory)
            self.assertEqual(output.decode().rstrip("\n"), query)
            self.assertFalse((Path(directory) / "SHOULD_NOT_EXIST").exists())


if __name__ == "__main__":
    unittest.main()
