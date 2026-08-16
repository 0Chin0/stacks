# Git Update Workflow — Merging Upstream Changes While Keeping Custom Modifications

This guide explains how to pull updates from the original Stacks repository (upstream) without losing the custom changes made in this fork. It assumes minimal Git experience — every command is given in full, with explanations.

---

## Prerequisites: What you need

- **Git for Windows** installed ([git-scm.com](https://git-scm.com/download/win))
- A terminal (CMD or PowerShell) opened in the project root: `cd X:\Coding\stacks-orig\stacks`

---

## Step 1: Check your current state

Before doing anything, see where you stand:

```cmd
git status
```

This shows:
- `modified:` — files you changed (your custom modifications)
- `untracked:` — new files Git doesn't know about (backups, docs, patches)

Also check what branch you're on:

```cmd
git branch
```

You should see `* master` (the asterisk means "currently on this branch").

---

## Step 2: Add the upstream remote (one-time only)

The "upstream" is the original Stacks repository on GitHub. You need to tell Git about it once:

```cmd
git remote add upstream https://github.com/zelest/stacks.git
```

Verify it was added:

```cmd
git remote -v
```

You should see two remotes:
- `origin` — your fork / local repo
- `upstream` — the original zelest/stacks repo

**What is a remote?** A nickname for another Git repository URL. `origin` is the default name for your own repo; `upstream` is the conventional name for the original repo you forked from.

---

## Step 3: When upstream releases updates — fetch them

Periodically (or when you hear about a new release), fetch the upstream changes:

```cmd
git fetch upstream
```

This downloads all new commits from the original Stacks repo into a hidden local copy called `upstream/master`. **It does not change your working files yet.** It just says "download what's new."

---

## Step 4: See what upstream changed (optional but recommended)

Compare upstream changes against your current code:

```cmd
:: How many new commits upstream has that you don't
git log HEAD..upstream/master --oneline

:: What files upstream changed
git diff --stat HEAD..upstream/master
```

The first command shows commit messages — gives you a sense of what was fixed or added upstream.
The second command shows which files were touched — this tells you which of your local files might have a conflict.

---

## Step 5: Merge upstream changes

Now apply upstream's changes on top of your work:

```cmd
git merge upstream/master -m "Merge upstream changes"
```

**What this does:** Git tries to combine upstream's changes with yours automatically. It uses your files as the base and applies upstream's modifications on top.

**Three possible outcomes:**

### Outcome A: Merge succeeds automatically

You'll see a message like `Merge made by the 'ort' strategy.` This means Git combined everything cleanly — congratulations.

Run:
```cmd
git status
```

Confirm your modified files are still there. Then rebuild and test:
```cmd
docker compose up -d --build
```

### Outcome B: Merge has conflicts (likely)

You'll see a message like:
```
Automatic merge failed; fix conflicts and then commit the result.
```

And `git status` will show files under `both modified:` — these are the files Git couldn't merge automatically.

**What is a conflict?** Both you and upstream changed the same lines in the same file. Git doesn't know which version to keep.

#### How to resolve conflicts

**Method 1: Manual (simple conflicts)**

Open each conflicted file in a text editor. You'll see markers like:

```
<<<<<<< HEAD
Your custom code
=======
Upstream's new code
>>>>>>> upstream/master
```

For each conflict block:
- The top section (`HEAD`) is **your** change
- The bottom section (`upstream/master`) is **their** new change
- Delete the markers and the section you DON'T want, or manually combine both

**Method 2: Accept upstream's version (discard your change)**

If you want to throw away your change for a specific file and just take upstream's version:

```cmd
git checkout --theirs -- path/to/file.py
git add path/to/file.py
```

After doing this, you'll need to re-apply your custom change using the patch files (see Step 6).

**Method 3: Accept your version (keep your change)**

If you want to ignore upstream's change to a file and keep yours:

```cmd
git checkout --ours -- path/to/file.py
git add path/to/file.py
```

**After resolving all conflicts:**

```cmd
:: Tell Git the conflict is resolved
git add .

:: Complete the merge commit
git commit -m "Merge upstream changes with conflict resolution"
```

### Outcome C: Merge conflict in docker-compose.yml

Upstream might add new services or environment variables to `docker-compose.yml`. Your `docker-compose.yml` has your custom volume paths. Resolve the conflict carefully, keeping your volume paths (`X:/AnnasArchive-...`) while incorporating any new services upstream added.

---

## Step 6: Re-apply custom changes that were lost

If you accepted upstream's version of any file (discarding your change), you need to re-apply your modification. Use the patch files:

```cmd
:: Try applying all patches in order
git apply patches/01-fix-suffix-hash.patch
git apply patches/02-retry-all-failed-backend.patch
git apply patches/03-bulk-add-backend.patch
git apply patches/04-frontend-changes.patch
```

If a patch applies cleanly, you'll see no output (good). If a patch fails, you'll get an error message like `error: patch failed: src/stacks/api/queue.py:122`. This means the code around that location changed and the patch no longer fits exactly. In that case, use the LLM guide:

**Option A: Ask an LLM to fix it**

Provide the LLM with these instructions:

> "Read `docs/guides/custom-changes-reference.md`. Then read each patch file that failed. Manually apply the logic from the failed patches to the current codebase. Files have been updated by an upstream merge and the line numbers in the patches are stale."

**Option B: Re-apply manually**

Open `docs/guides/custom-changes-reference.md`, find the section for the failed patch, and insert the code manually at the correct location in the file.

---

## Step 7: Build and test

After merging and re-applying, rebuild the Docker image and test:

```cmd
docker compose up -d --build
```

Then open `http://localhost:7788` and verify:
- Single-add works (type an MD5, press Enter)
- Bulk-add works (click "v", paste multiple MD5s, click "Add All")
- Retry All Failed button appears in History
- Files download with correct extensions (hash suffix fix)

---

## Summary: the full workflow in one page

```cmd
:: 1. Fetch upstream changes
git fetch upstream

:: 2. See what changed
git log HEAD..upstream/master --oneline
git diff --stat HEAD..upstream/master

:: 3. Merge (may produce conflicts)
git merge upstream/master -m "Merge upstream changes"

:: 4. Resolve conflicts if any
::    Edit files manually, or use --ours/--theirs

:: 5. Re-apply patches for changes that were overwritten
git apply patches/01-fix-suffix-hash.patch
git apply patches/02-retry-all-failed-backend.patch
git apply patches/03-bulk-add-backend.patch
git apply patches/04-frontend-changes.patch

:: 6. Rebuild and test
docker compose up -d --build
```

---

## Troubleshooting

### "fatal: remote upstream already exists"
You already added the upstream remote. Skip Step 2. Run `git remote set-url upstream https://github.com/zelest/stacks.git` if you need to fix it.

### "error: Your local changes to the following files would be overwritten by merge"
You have uncommitted changes. Stash them first:
```cmd
git stash
git merge upstream/master
git stash pop
```

### Patch says "fuzzy" or "offset"
This means Git found the right spot but the exact line numbers shifted. The patch likely applied successfully despite the warning. Run `git status` and `git diff` to verify.

### "I accidentally accepted the wrong version during conflict resolution"
Undo the merge and start over:
```cmd
git merge --abort
```
Then redo from Step 5.

---

## Appendix: Git concepts explained

| Concept | Plain English |
|---------|---------------|
| **Remote** | A nickname for a Git repository URL. Like a contacts list entry for a repo. |
| **Fetch** | Download new commits from a remote (like checking for email). Doesn't change your files. |
| **Merge** | Combine two branches of history. Applies the downloaded commits on top of your work. |
| **Conflict** | Two edits that touch the same code in different ways. Git needs your help to decide. |
| **Patch** | A file containing a "diff" (list of insertions and deletions). Can be re-applied with `git apply`. |
| **Stash** | Temporarily put aside uncommitted changes to do something else, then bring them back. |
