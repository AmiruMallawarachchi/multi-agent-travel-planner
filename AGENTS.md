TripWeaver Codex Engineering Instructions
=========================================

Required context
----------------

Before changing code:

- Read `SYSTEM.md`.
- Read the relevant existing source files and tests.
- Run `git status --short`.
- Confirm the working tree is clean.
- Identify the current branch.
- Never begin feature work directly on `main` or `dev`.

`SYSTEM.md` describes the intended architecture, but the actual code and tests
are the source of truth when they differ. Report any important mismatch.

Git branch workflow
-------------------

The permanent branches are:

- `main`: stable submission-ready code
- `dev`: integration branch

All implementation work must happen on a temporary branch created from the
latest `dev`.

Allowed branch prefixes:

- `feature/`
- `fix/`
- `test/`
- `docs/`
- `chore/`

Before starting a task:

```bash
git switch dev
git pull --ff-only origin dev
git switch -c <requested-branch-name>
```

Never:

- Commit directly to `main`
- Commit directly to `dev`
- Push directly to `main`
- Push directly to `dev`
- Force-push
- Rewrite published history
- Merge a pull request
- Delete remote branches unless explicitly requested
- Continue when the initial working tree contains unrelated changes

If the working tree is not clean before starting, stop and report the changed
files.

Scope control
-------------

Only modify files required for the requested feature.

Do not:

- Refactor unrelated modules
- Rename unrelated files
- Reformat the entire repository
- Upgrade unrelated dependencies
- Replace an established architecture without approval
- Add real payment or real travel booking
- Hardcode API keys or secrets
- Commit `.env`, credentials, caches, virtual environments, logs, or generated
  secrets

Before editing, report:

- The files expected to change
- The tests that will be run
- The planned commit boundaries

Implementation workflow
-----------------------

For each logically complete implementation unit:

1. Implement the smallest coherent change.
2. Run the smallest relevant test suite.
3. Review `git diff --check`.
4. Review `git diff`.
5. Stage only files belonging to that unit.
6. Create one Conventional Commit.
7. Continue to the next coherent unit.

Do not commit merely because one file was created.

Do not commit:

- Failing code
- Syntax errors
- Debug print statements
- Commented-out abandoned code
- Unrelated changes
- Temporary files
- Placeholder tests that do not verify behaviour

Commit format
-------------

Use Conventional Commits:

```text
feat(scope): description
fix(scope): description
test(scope): description
docs(scope): description
chore(scope): description
build(scope): description
ci(scope): description
refactor(scope): description
```

Rules:

- Use imperative lowercase descriptions.
- Keep each commit focused on one reason for change.
- Do not use vague messages such as `update files`, `changes`, `work done`, or
  `final`.
- Separate implementation, tests, documentation, and infrastructure when they
  are independently meaningful.
- Do not amend an existing commit after it has been pushed unless explicitly
  instructed.

Python verification
-------------------

Use the existing virtual environment when available.

Run syntax checks on changed Python areas:

```bash
python -m compileall backend mcp_servers frontend
```

For backend work:

```bash
cd backend
pytest -q
cd ..
```

For focused work, run the smallest relevant tests first, then run the complete
backend suite before opening a pull request.

Also run:

```bash
git diff --check
git status --short
```

Do not claim tests passed unless the command was actually run and its result was
observed.

If a test cannot run because credentials or an external service are unavailable:

- Run all available offline tests.
- Clearly report what could not be verified.
- Do not invent a successful result.

Commit safety
-------------

Before every commit:

```bash
git status --short
git diff --cached
```

Stage explicit paths rather than using `git add .` whenever possible.

After every commit:

```bash
git show --stat --oneline HEAD
git status --short
```

The working tree may remain dirty only when the remaining changes clearly belong
to the next planned commit.

Push and pull-request workflow
------------------------------

After all requested implementation is complete:

1. Run the full required tests.
2. Confirm `git status --short` is empty.
3. Show the branch's commits compared with `dev`.
4. Push the feature branch.
5. Open a pull request targeting `dev`.

Commands:

```bash
git log --oneline origin/dev..HEAD
git push -u origin HEAD
gh pr create --base dev --head <current-branch> --title "<title>" --body "<summary>"
```

The pull-request body must contain:

- Summary
- Important design decisions
- Changed areas
- Tests run and their exact results
- Known limitations
- Manual verification steps
- Confirmation that no secrets were committed

Do not merge the pull request. Leave it for human review.

Final report
------------

At the end of the task, report:

- Branch name
- Files changed
- Commits created
- Tests run
- Test results
- Pull-request link
- Remaining limitations
- Any work that could not be verified

Do not state that the task is fully complete when tests, push, or pull-request
creation failed.
