#!/bin/sh
# Alfred provides arguments as argv, never as interpolated shell source.
if [ -n "${PYTHON3:-}" ]; then
    companion_python="$PYTHON3"
else
    companion_python=""
    for companion_candidate in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
        if [ -x "$companion_candidate" ]; then
            companion_python="$companion_candidate"
            break
        fi
    done
    if [ -z "$companion_python" ]; then
        companion_python="$(command -v python3 2>/dev/null || true)"
    fi
fi

if [ -n "$companion_python" ] && [ -x "$companion_python" ]; then
    exec "$companion_python" "$(dirname "$0")/companion.py" "$@"
fi

if [ "${1:-list}" = "list" ]; then
    printf '%s\n' '{"items":[{"title":"Python 3 not found","subtitle":"Install Python 3.9+ or set the PYTHON3 workflow variable to its full path.","valid":false}]}'
else
    printf '%s\n' 'Python 3 not found. Install Python 3.9+ or set the PYTHON3 workflow variable.'
fi
exit 1
