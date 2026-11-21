# Releasing consilience 0.3.0 to PyPI

A checklist for the owner. Plain language, copy-paste commands. Nothing in this
repository uploads anything by itself: every upload below happens only when you do it.

**Read this first.** PyPI never lets the same version number be uploaded twice, even
after a delete. If something is wrong after upload, the fix is a new version (0.3.1). So
do the checks in step 1 before step 4.

0.1.0 is on PyPI (published 17 Nov 2026 from the tag `v0.1.0`). Before releasing,
check that 0.1.0 is still the latest version there: open
https://pypi.org/pypi/consilience/json and look at `"version"` under `"info"`.

This release is made from the branch `main`. The links on
the PyPI page point to files at the tag `v0.3.0`, which GitHub creates when you publish
the release in step 4; until then those links do not work yet.

---

## Step 1. Build and check on your computer (about 5 minutes)

You need Python 3.10 or newer (3.12 or newer if you also want to run the nanopublication
tests). Check with:

```
python3 --version
```

Then, in a terminal:

```
git clone -b main https://github.com/Anuja-Khatri/consilience-core.git consilience-release
cd consilience-release
bash scripts/check_release.sh
```

(If your `python3` is older than 3.10 but you have, say, `python3.12`, run
`PYTHON=python3.12 bash scripts/check_release.sh` instead.)

That one script does everything below and stops with `FAIL` if anything is wrong:

- builds the two files that get uploaded into `dist/`:
  `consilience-0.3.0.tar.gz` and `consilience-0.3.0-py3-none-any.whl`;
- runs `twine check --strict` on them (checks the PyPI page will render);
- lists what is inside the wheel and checks the electrochemistry pack and the examples
  are there;
- makes a brand-new, empty Python environment, installs only the wheel, and runs the
  README quickstart there, command by command: every output and every exit code must be
  exactly what the README shows, and the README's Python example must print exactly
  what its comments say.

The last line must be:

```
== release check passed: dist/ is ready (nothing was uploaded)
```

To also run the test suite:

```
python3 -m venv .venv && .venv/bin/pip install -e ".[test]"
.venv/bin/python -m pytest -q
```

If you prefer to run the release steps by hand, they are:

```
python3 -m venv /tmp/cs-build && /tmp/cs-build/bin/pip install build twine
rm -rf dist && /tmp/cs-build/bin/python -m build
/tmp/cs-build/bin/twine check --strict dist/*

python3 -m venv /tmp/cs-test && /tmp/cs-test/bin/pip install dist/consilience-0.3.0-py3-none-any.whl
mkdir /tmp/cs-try && cd /tmp/cs-try
/tmp/cs-test/bin/consilience examples .
/tmp/cs-test/bin/consilience compare measurement_a.json measurement_b.json --pack electrochemistry; echo "exit $?"   # disagree, exit 1
/tmp/cs-test/bin/consilience compare measurement_a.json measurement_c.json --pack electrochemistry; echo "exit $?"   # not_comparable(current_density), exit 2
/tmp/cs-test/bin/consilience check readings.csv --rules readings_rules.yaml; echo "exit $?"                         # 5 violations, 2 unreadable cells, exit 3
```

## Step 2. One-time setup for trusted publishing (already done for 0.1.0)

If 0.1.0 was published through the `publish` workflow, this is already set up: skip to
step 3. The steps are kept here for reference.

Trusted publishing lets GitHub upload the package for you without any password or
token stored anywhere. You set it up once. (You did the same for lab-gate; this is a
second pending publisher for a second project.)

**On pypi.org** (PyPI requires two-factor login):

1. Log in at https://pypi.org .
2. Click your user name (top right), then **Your projects**, then **Publishing** in
   the left menu. (Direct link: https://pypi.org/manage/account/publishing/ )
3. Under **Add a new pending publisher**, choose the **GitHub** tab and fill in:
   - PyPI Project Name: `consilience`
   - Owner: `Anuja-Khatri`
   - Repository name: `consilience-core`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`
4. Click **Add**.

**On github.com**:

1. Open https://github.com/Anuja-Khatri/consilience-core , then **Settings**, then
   **Environments**, then **New environment**.
2. Name it `pypi` (exactly) and click **Configure environment**.
3. Recommended: tick **Required reviewers**, add yourself, and click
   **Save protection rules**. Then every upload waits for your click.

Optional rehearsal on TestPyPI (a separate practice site): make an account at
https://test.pypi.org , add the same pending publisher there but with Environment
name `testpypi`, and create a GitHub environment called `testpypi`. Then in GitHub
open **Actions**, then **publish**, then **Run workflow**, choose the branch
`main` and the target `testpypi`, and run it. It uploads to
https://test.pypi.org/project/consilience/ only.

## Step 3. Look at the workflow before you use it

The workflow file is `.github/workflows/publish.yml`. It runs only when you publish a
GitHub Release, or when you click **Run workflow** yourself. It never runs on a push.
Before uploading, it runs the same `scripts/check_release.sh` as step 1, and on a
release it checks that the release tag matches the version `0.3.0`.

## Step 4. Publish

1. On GitHub, open https://github.com/Anuja-Khatri/consilience-core , then **Releases**
   (right-hand side of the repository page), then **Draft a new release**.
2. **Choose a tag**: type `v0.3.0` and click **Create new tag: v0.3.0 on publish**.
   **Target**: choose the branch `main` .
3. Release title: `consilience 0.3.0`. Description: paste the 0.3.0 section of
   `CHANGELOG.md`.
4. Click **Publish release**.
5. Open the **Actions** tab. The `publish` run builds and checks the package. If you
   set required reviewers, click **Review deployments**, tick `pypi`, and approve.
6. When it is green, the package is at https://pypi.org/project/consilience/ .

### Alternative: upload by hand with twine

Only if you do not want trusted publishing.

1. On pypi.org: your user name, then **Account settings**, then **API tokens**, then
   **Add API token**. Scope: "Entire account" for the first upload (you can make a
   project-only token afterwards). Copy the token (it starts with `pypi-`). It is shown
   once. Do not paste it into any file in the repository.
2. From the folder where step 1 built `dist/`:

   ```
   python3 -m venv /tmp/cs-build && /tmp/cs-build/bin/pip install twine
   /tmp/cs-build/bin/twine upload dist/*
   ```

   When asked for the username type `__token__`; for the password paste the token.
3. Then create the tag `v0.3.0` on `main` as in step 4 (so the links on the PyPI
   page work), and delete the token on pypi.org if you will not use it again.

## Step 5. Check the published package

In a new terminal, in an empty folder:

```
python3 -m venv /tmp/cs-pypi && /tmp/cs-pypi/bin/pip install consilience
/tmp/cs-pypi/bin/consilience version          # consilience 0.3.0
/tmp/cs-pypi/bin/consilience examples .
/tmp/cs-pypi/bin/consilience compare measurement_a.json measurement_b.json --pack electrochemistry   # disagree
```

A receipt made with 0.1.0 must still verify with 0.3.0 (`consilience verify
old-receipt.json`); the test suite checks this with the receipts in
`tests/fixtures/receipts-0.1.0/`.

`CHANGELOG.md` already carries the date 2026-11-21 for 0.3.0. If you publish on a later day, correct the date in a small follow-up commit.
