#!/bin/sh
# Alfred provides arguments as argv, never as interpolated shell source.
if [ -n "${PYTHON3:-}" ]; then
    yab_tabs_python="$PYTHON3"
else
    yab_tabs_python=""
    for yab_tabs_candidate in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
        if [ -x "$yab_tabs_candidate" ]; then
            yab_tabs_python="$yab_tabs_candidate"
            break
        fi
    done
    if [ -z "$yab_tabs_python" ]; then
        yab_tabs_python="$(command -v python3 2>/dev/null || true)"
    fi
fi

if [ -n "$yab_tabs_python" ] && [ -x "$yab_tabs_python" ]; then
    exec "$yab_tabs_python" "$(dirname "$0")/yab_tabs.py" "$@"
fi

if [ "${1:-list}" = "list" ]; then
    printf '%s\n' '{"items":[{"title":"Python 3 not found","subtitle":"Install Python 3.9+ or set the PYTHON3 workflow variable to its full path.","valid":false}]}'
else
    printf '%s\n' 'Python 3 not found. Install Python 3.9+ or set the PYTHON3 workflow variable.'
fi
exit 1
