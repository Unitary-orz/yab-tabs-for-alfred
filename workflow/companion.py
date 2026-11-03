#!/usr/bin/python3
"""Alfred integration using only Yab's public MCP server; standard library only."""
import contextlib
import fcntl
import json
import os
from pathlib import Path
import re
import select
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import uuid

BUNDLE = "community.yab-companion.alfred"
VERSION = Path(__file__).with_name("VERSION").read_text().strip()
CACHE_TTL = 2


class YabError(Exception):
    pass


def yab_path():
    candidates = [os.environ.get("YAB_CLI", ""), str(Path.home() / ".local/bin/yab"),
                  "/opt/homebrew/bin/yab", "/usr/local/bin/yab", shutil.which("yab")]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    raise YabError("Yab CLI not found. Install it in Yab → Settings → Developers.")


def tool_text(result):
    return "\n".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")


class MCP:
    def __enter__(self):
        env = dict(os.environ)
        env["PATH"] = os.pathsep.join([str(Path.home() / ".local/bin"), "/opt/homebrew/bin",
                                       "/usr/local/bin", env.get("PATH", "/usr/bin:/bin")])
        self.process = subprocess.Popen([yab_path(), "mcp"], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env)
        self.buffer = b""
        self.sequence = 0
        try:
            self.rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                     "clientInfo": {"name": "alfred-yab-companion", "version": VERSION}})
            self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        except Exception:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, *_):
        self.process.terminate()
        try:
            self.process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.process.stdin.close()
        self.process.stdout.close()

    def send(self, payload):
        self.process.stdin.write((json.dumps(payload, ensure_ascii=False) + "\n").encode())
        self.process.stdin.flush()

    def rpc(self, method, params):
        self.sequence += 1
        request_id = self.sequence
        self.send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + 8
        while True:
            while b"\n" not in self.buffer:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not select.select([self.process.stdout], [], [], remaining)[0]:
                    raise YabError("Yab timed out. Open Yab and try again.")
                data = os.read(self.process.stdout.fileno(), 65536)
                if not data:
                    raise YabError("Cannot connect to Yab. Open Yab and check Settings → AI → Agents.")
                self.buffer += data
            line, self.buffer = self.buffer.split(b"\n", 1)
            try:
                response = json.loads(line)
            except ValueError:
                continue
            if response.get("id") != request_id:
                continue
            if "error" in response:
                raise YabError("Yab could not complete the request. Open Yab and try again.")
            return response.get("result", {})

    def call(self, name, arguments):
        result = self.rpc("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            text = tool_text(result).lower()
            if "no tab" in text:
                raise YabError("This tab was closed or moved. Search again.")
            if "needs_user" in text or "confirm" in text:
                raise YabError("Complete the confirmation in Yab, then try again.")
            raise YabError("Yab could not complete the action. Open Yab and try again.")
        return result

    def data(self, name, arguments):
        result = self.call(name, arguments)
        data = result.get("structuredContent")
        if isinstance(data, dict):
            return data
        try:
            return json.loads(tool_text(result))
        except ValueError:
            raise YabError("Cannot read Yab data. Check that Yab is up to date.")


def cache_directory():
    path = Path(os.environ.get("alfred_workflow_cache", str(Path.home() / "Library/Caches" / BUNDLE)))
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def parse_live_tabs(result):
    """tabs() supplies the complete current title/URL; native_context supplies metadata."""
    records = {}
    for line in tool_text(result).splitlines():
        match = re.match(r"^([a-zA-Z0-9-]+) \[user\] (.*)$", line)
        if not match:
            continue
        tab_id, label = match.groups()
        markers = ("(in front) ", "(in every shared-sign-in space) ")
        while label.startswith(markers):
            label = next(label[len(marker):] for marker in markers if label.startswith(marker))
        match_url = re.match(r"^(.*), ([a-zA-Z][a-zA-Z0-9+.-]*:.*)$", label)
        if match_url:
            title, url = match_url.groups()
            records[tab_id] = {"title": title, "url": url}
    return records


def read_snapshot(client):
    context = client.data("native_context", {"section": "summary", "limit": 50})
    current = context["activeSpaceId"]
    spaces = [{k: s[k] for k in ("id", "name", "active") if k in s} for s in context.get("spaces", [])]
    all_tabs = context.get("tabs", [])
    more = context.get("hasMoreTabs", False)
    offset = 50
    while more:
        page = client.data("native_context", {"section": "summary", "limit": 50, "offset": offset})
        if page["activeSpaceId"] != current:
            raise YabError("The space changed. Search again.")
        all_tabs.extend(page.get("tabs", []))
        more = page.get("hasMoreTabs", False)
        offset += 50
        if offset > 10000:
            raise YabError("Too many tabs to read. Search in Yab instead.")
    live = parse_live_tabs(client.call("tabs", {}))
    result = []
    for tab in all_tabs:
        if tab.get("ownedByTask") or tab.get("blank") or not tab.get("url"):
            continue
        # Use exactly the short identity returned by tabs, rather than inventing one.
        short_id = next((key for key in live if tab["id"].lower().startswith(key.lower())), None)
        row = {key: tab.get(key, "") for key in
               ("id", "title", "url", "folderPath", "inEverySpace", "active", "lastUsed")}
        row["id"] = short_id or tab["id"]
        row.update(live.get(short_id, {}))
        result.append(row)
    return {"fetched": time.time(), "spaceId": current, "spaces": spaces, "tabs": result}


def snapshot():
    directory = cache_directory()
    path = directory / "tabs.json"
    lock = directory / "tabs.lock"
    fd = os.open(str(lock), os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, "w") as guard:
        fcntl.flock(guard, fcntl.LOCK_EX)
        try:
            data = json.loads(path.read_text())
            if (isinstance(data, dict) and isinstance(data.get("tabs"), list)
                    and isinstance(data.get("spaces"), list) and isinstance(data.get("spaceId"), str)
                    and 0 <= time.time() - data.get("fetched", 0) < CACHE_TTL):
                return data
        except (OSError, ValueError, TypeError):
            pass
        with MCP() as client:
            data = read_snapshot(client)
        handle, temporary = tempfile.mkstemp(prefix="tabs-", dir=str(directory))
        try:
            with os.fdopen(handle, "w") as stream:
                json.dump(data, stream, ensure_ascii=False)
            os.replace(temporary, path)
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temporary)
        return data


def normalized(value):
    return unicodedata.normalize("NFKC", value).casefold()


def markdown_link(title, url):
    title = re.sub(r"([\\\[\]])", r"\\\1", title.replace("\n", " "))
    return "[{}](<{}>)".format(title, url.replace("<", "%3C").replace(">", "%3E"))


def list_items(data, query):
    query = normalized(query.strip())
    tokens = query.split()
    current_space = next((s["name"] for s in data["spaces"] if s["id"] == data["spaceId"]), "Current space")
    matches = []
    for row in data["tabs"]:
        title = row["title"] or row["url"]
        label = "Shared tabs" if row["inEverySpace"] else current_space
        folder = row["folderPath"]
        haystack = normalized(" ".join([title, row["url"], label, folder]))
        if not all(token in haystack for token in tokens):
            continue
        payload = {"kind": "tab", "id": row["id"], "spaceId": data["spaceId"],
                   "shared": bool(row["inEverySpace"])}
        item = {"uid": "tab:" + row["id"], "title": title,
                "subtitle": " · ".join(filter(None, [label, folder, row["url"]])),
                "arg": json.dumps(payload), "valid": True,
                "text": {"copy": row["url"], "largetype": title},
                "mods": {
                    "alt": {"valid": True, "arg": row["url"], "subtitle": "Copy URL"},
                    "cmd": {"valid": True, "arg": title, "subtitle": "Copy title"},
                    "shift": {"valid": True, "arg": markdown_link(title, row["url"]), "subtitle": "Copy Markdown link"},
                }}
        score = (int(query != normalized(title)), int(not normalized(title).startswith(query)),
                 int(not row["active"])) if query else (0, 0, int(not row["active"]))
        matches.append((score, item))
    matches.sort(key=lambda entry: entry[0])
    items = [item for _, item in matches]
    for space in data["spaces"]:
        if space["id"] == data["spaceId"]:
            continue
        if tokens and not all(token in normalized("space " + space["name"]) for token in tokens):
            continue
        items.append({"uid": "space:" + space["id"], "title": "Switch to " + space["name"],
                      "subtitle": "Switch, then type yt to search tabs in this space",
                      "arg": json.dumps({"kind": "space", "id": space["id"]}), "valid": True,
                      "mods": {key: {"valid": False, "subtitle": "Press Return to switch space"} for key in ("alt", "cmd", "shift")}})
    if not items:
        items.append({"title": "No matching tabs or spaces", "subtitle": "Search scope: " + current_space + " and shared tabs", "valid": False})
    return {"items": items, "rerun": CACHE_TTL}


def switch_space(client, space_id):
    # The action preview returns the aggregate version space.switch actually expects.
    target = {"kind": "space", "id": space_id}
    context = client.data("native_context", {"action": "space.switch", "arguments": {}, "target": target, "limit": 1})
    if context["activeSpaceId"] != space_id:
        result = client.data("native_apply", {"action": "space.switch", "target": target, "arguments": {},
                             "expectedVersion": context["resourceVersion"], "requestId": str(uuid.uuid4())})
        if result.get("status") != "verified":
            raise YabError("The space has not switched. Check Yab and try again.")
        # Native changes are queued on Yab's UI thread; wait for the space before resolving a parked tab.
        for _ in range(20):
            context = client.data("native_context", {"limit": 1})
            if context["activeSpaceId"] == space_id:
                return
            time.sleep(0.05)
        raise YabError("The space has not switched yet. Search again shortly.")


def action(payload):
    payload = json.loads(payload)
    if (not isinstance(payload, dict) or payload.get("kind") not in ("space", "tab")
            or not isinstance(payload.get("id"), str) or not payload["id"]):
        raise YabError("Invalid action. Search again.")
    if (payload["kind"] == "tab" and not payload.get("shared")
            and (not isinstance(payload.get("spaceId"), str) or not payload["spaceId"])):
        raise YabError("Invalid action. Search again.")
    with MCP() as client:
        if payload["kind"] == "space":
            switch_space(client, payload["id"])
        else:
            if not payload.get("shared"):
                switch_space(client, payload["spaceId"])
            client.call("show", {"tab": payload["id"]})
    with contextlib.suppress(FileNotFoundError):
        (cache_directory() / "tabs.json").unlink()


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "list"
    value = sys.argv[2] if len(sys.argv) > 2 else ""
    try:
        if mode == "list":
            print(json.dumps(list_items(snapshot(), value), ensure_ascii=False))
        elif mode == "action":
            action(value)
        else:
            raise YabError("Unknown action. Search again.")
    except (YabError, OSError, ValueError, KeyError) as error:
        message = str(error) if isinstance(error, YabError) else "Cannot read tabs. Open Yab and try again."
        if mode == "list":
            print(json.dumps({"items": [{"title": "Cannot read Yab right now", "subtitle": message, "valid": False}]}, ensure_ascii=False))
        else:
            # Alfred's notification output only displays nonempty output.
            print(message)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
