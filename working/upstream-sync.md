# Taking a new Apertar-Studio release into the fork

Do it on the Mac, then pull on the Pi. Never on the Pi first: a big merge is easier to read here.

## Why this needs a procedure

Upstream publishes releases as large squashed commits, sometimes with **rewritten history**.
At fork time (2026-10-25) `Apertar-Core` had exactly one commit ("1.6.0 Release"), although
releases 1.0.0 to 1.5.0 existed. So `upstream/main` may share no history with your `main`, and a
plain `git merge` can fail or conflict on every file.

The fix: treat each release as a snapshot. The tag `upstream-<version>` marks the snapshot your
fork last took. Apply only the difference between two snapshots on top of your own commits.

## Steps

```bash
cd ~/Documents/Apertar/Apertar-Core        # then repeat for Apertar-UI
git pull                                   # start from GitHub's main
git fetch upstream --tags
git log --oneline -3 upstream/main         # what did they publish?
git merge-base HEAD upstream/main && echo "shared history" || echo "history was rewritten"
```

**A. Shared history** (normal case):

```bash
git merge upstream/main -m "upstream: merge Apertar-Studio 1.7.0"
```

**B. History rewritten:** apply the snapshot difference.

```bash
OLD=$(git describe --tags --abbrev=0 --match 'upstream-*')   # e.g. upstream-1.6.0
git diff --binary "$OLD" upstream/main -- . ':(exclude)build' | git apply --3way --index
git commit -m "upstream: apply Apertar-Studio 1.7.0 (snapshot diff from $OLD)"
```

`':(exclude)build'` matters for Apertar-UI only: upstream commits its build tree, the fork does not.

**Then, both cases:**

```bash
git tag -a upstream-1.7.0 upstream/main -m "Apertar-Studio 1.7.0"
git push origin main upstream-1.7.0
```

On the Pi: `git pull`, rebuild both components, restart services (see `build-deploy.md`).

## Conflicts

- A conflict means upstream touched a line you also changed. Read both sides. Your change is the
  one with a commit message that explains it (`git log -p -- <file>`).
- `build/...` modify/delete in Apertar-UI (case A only): `git rm -r --cached build`, continue.
- After any upstream sync, `architecture/*.md` line refs may be stale. Re-check the ones a current
  tutorial depends on.

## Check

`apertar_status.sh` prints `>> upstream/main moved past upstream-X` when a release is waiting.
