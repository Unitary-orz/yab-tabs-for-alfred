#!/usr/bin/env python3
"""Build the workflow without Alfred, Yab, third-party packages or network access."""
import argparse
from pathlib import Path
import plistlib
import sys
import uuid
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "workflow"))
from yab_tabs import BUNDLE, VERSION

PACKAGE_NAME = "Yab Tabs for Alfred.alfredworkflow"


def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, BUNDLE + "/" + name)).upper()


def metadata():
    objects, positions, connections = [], {}, {}

    def node(name, kind, config, x, y, version=1, note=""):
        obj = {"uid": uid(name), "type": "alfred.workflow." + kind,
               "version": version, "config": config}
        objects.append(obj)
        positions[uid(name)] = {"xpos": float(x), "ypos": float(y)}
        if note:
            positions[uid(name)]["note"] = note
        return obj

    def edge(source, destination, modifier=0):
        connections.setdefault(uid(source), []).append({
            "destinationuid": uid(destination), "modifiers": modifier,
            "modifiersubtext": "", "vitoclose": False})

    search = node("search", "input.scriptfilter", {
        "alfredfiltersresults": False, "alfredfiltersresultsmatchmode": 0,
        "argumenttreatemptyqueryasnil": False, "argumenttrimmode": 0, "argumenttype": 1,
        "escaping": 68, "keyword": "yt", "queuedelaycustom": 2,
        "queuedelayimmediatelyinitially": True, "queuedelaymode": 0, "queuemode": 2,
        "runningsubtext": "Reading Yab tabs…",
        "script": '/bin/sh ./run.sh list "$1"', "scriptargtype": 1, "scriptfile": "",
        "skipuniversalaction": True,
        "subtext": "Search current-space and shared tabs, or switch spaces by name",
        "title": "Search Yab tabs", "type": 11, "withspace": True,
    }, 260, 200, 3)
    search["inboundconfig"] = {"externalid": "list_tabs", "usecustominputarg": False}
    node("hotkey", "trigger.hotkey", {
        "action": 0, "argument": 0, "focusedappvariable": False,
        "focusedappvariablename": "", "hotkey": 0, "hotmod": 0,
        "leftcursor": False, "modsmode": 0, "relatedAppsMode": 0,
    }, 70, 200, 2, "Optional global hotkey")
    node("action", "action.script", {
        "concurrently": False, "escaping": 68,
        "script": '/bin/sh ./run.sh action "$1"', "scriptargtype": 1,
        "scriptfile": "", "type": 11,
    }, 510, 150, 2, "Switch to tab / space")
    node("clipboard", "output.clipboard", {
        "autopaste": False, "clipboardtext": "{query}",
        "ignoredynamicplaceholders": True, "transient": False,
    }, 510, 350, 3, "⌥ URL · ⌘ title · ⇧ Markdown")
    node("error", "output.notification", {
        "lastpathcomponent": False, "onlyshowifquerypopulated": True,
        "removeextension": False, "text": "{query}", "title": "Yab Tabs for Alfred",
    }, 750, 150, 1, "Only show action errors")
    edge("hotkey", "search")
    edge("search", "action")
    for modifier in (524288, 1048576, 131072):
        edge("search", "clipboard", modifier)
    edge("action", "error")
    return {
        "bundleid": BUNDLE, "category": "Internet", "connections": connections,
        "createdby": "Yab Tabs for Alfred contributors",
        "description": "Search Yab tabs, switch spaces, and copy links and titles",
        "disabled": False, "name": "Yab Tabs for Alfred", "objects": objects,
        "readme": (ROOT / "workflow/README.md").read_text(), "uidata": positions, "version": VERSION,
        "variables": {}, "variablesdontexport": ["YAB_CLI", "PYTHON3"],
    }


def build(output=None):
    output = Path(output) if output else ROOT / PACKAGE_NAME
    output.parent.mkdir(parents=True, exist_ok=True)
    files = {name: (ROOT / name).read_bytes() for name in ("LICENSE", "THIRD_PARTY_NOTICES.md")}
    for name in ("yab_tabs.py", "run.sh", "VERSION", "README.md"):
        files[name] = (ROOT / "workflow" / name).read_bytes()
    files["icon.png"] = (ROOT / "assets/icon.png").read_bytes()
    files["info.plist"] = plistlib.dumps(metadata(), sort_keys=True)
    # Fixed metadata and stored entries make builds byte-identical across supported Python versions.
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, contents in sorted(files.items()):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, contents)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Output path (default: repository root)")
    print(build(parser.parse_args().output))
