# Contributing

Keep changes focused on searching and switching Yab tabs and spaces, and copying tab information. Use Yab's public interfaces. Report a reproducible example when an interface changes.

## Check a change

```sh
python3 -m unittest discover -s tests -v
sh -n workflow/run.sh
python3 scripts/build.py
git diff --check
```

Commit the rebuilt `Yab Companion.alfredworkflow` together with its source changes. Builds do not touch your installed Alfred workflows.

For runtime changes, also import the rebuilt package and check search, Return, URL/title/Markdown copies, and space switching in Alfred. CI's offline checks do not replace those live checks. Use a disposable test tab for live testing.

## Fixtures and reports

Use invented titles, IDs, and `example.com` URLs. Do not commit tab exports, caches, real browser screenshots, account details, or raw debugger logs. Before opening an issue, include the Alfred and Yab versions, expected result, actual result, and minimal steps; redact browsing data.

## Version and commit conventions

`workflow/VERSION` is the version source. Routine fixes do not automatically change it; a version change should be intentional.

Use `type(scope): summary` for commits. Useful scopes are `search`, `tabs`, `spaces`, `clipboard`, and `repo`. Keep a change and its validation in one coherent commit.

The source code and original documentation are MIT licensed. Keep the Yab icon's separate notice intact; its inclusion does not grant trademark or artwork rights.
