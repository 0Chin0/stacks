# Custom Changes Reference — LLM Re-Application Guide

This document catalogues every custom modification made to this Stacks fork. It is designed so that a future LLM (or developer) can re-apply all changes after pulling upstream updates.

## Quick Apply (if no conflicts)

```bash
cd /path/to/stacks
git apply patches/00-all-changes-comprehensive.patch
```

If that fails, apply each patch in order:

```bash
git apply patches/01-fix-suffix-hash.patch
git apply patches/02-retry-all-failed-backend.patch
git apply patches/03-bulk-add-backend.patch
git apply patches/04-frontend-changes.patch
# 99-local-docker-compose.patch is optional (your local paths only)
```

---

## Change 1: Fix suffix hash placement in filenames

**Files:** `src/stacks/downloader/html.py`

**What it does:** When `include_hash` is set to `"suffix"`, the hash was appended after the filename extension (e.g. `book.pdf - HASH`), which broke the file type. Now the hash is inserted before the extension (e.g. `book - HASH.pdf`).

**Patch file:** `patches/01-fix-suffix-hash.patch`

**Location in file:** Lines 238-244

**Original code (what was there before):**
```python
elif d.include_hash == "suffix":
    filename = f"{filename} - {md5}"
```

**New code:**
```python
elif d.include_hash == "suffix":
    # Insert hash before the extension to preserve file type
    stem, _, ext = filename.rpartition('.')
    if stem:
        filename = f"{stem} - {md5}.{ext}"
    else:
        filename = f"{md5} - {filename}"
```

**How to re-apply manually (if patching fails):**
1. Open `src/stacks/downloader/html.py`
2. Find `elif d.include_hash == "suffix":`
3. Replace the line `filename = f"{filename} - {md5}"` with the 5-line block above

---

## Change 2: Retry All Failed Downloads

### 2a. Backend — `queue_ops.py` (multi-process mode)

**File:** `src/stacks/coordinator/queue_ops.py`

**What it does:** Adds `retry_all_failed()` method that resets ALL failed downloads to `pending_scrape` in one atomic SQL UPDATE.

**Location:** Between `retry_failed()` method (ending ~line 819) and `clear_history()` method (starting ~line 867 in original, shifted by the insertion)

**Method signature:**
```python
def retry_all_failed(self) -> tuple[bool, str, int]:
```

**Implementation:**
```python
    def retry_all_failed(self) -> tuple[bool, str, int]:
        conn = get_connection()
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) AS cnt FROM downloads WHERE status = 'failed'"
            )
            row = cursor.fetchone()
            count = row['cnt'] if row else 0
            if count == 0:
                return True, "No failed downloads to retry", 0
            conn.execute("""
                UPDATE downloads
                SET status = 'pending_scrape',
                    error = NULL, completed_at = NULL, success = NULL,
                    assigned_worker = NULL, assigned_mirror = NULL,
                    added_at = ?
                WHERE status = 'failed'
            """, (datetime.now().isoformat(),))
            conn.commit()
            return True, f"Retrying {count} failed download(s)", count
        except Exception as e:
            conn.rollback()
            return False, str(e), 0
        finally:
            conn.close()
```

### 2b. Backend — `server/queue.py` (debug/single-process mode)

**File:** `src/stacks/server/queue.py`

**Same logic** but for the in-memory queue (JSON-backed, debug mode).

**Location:** Between `retry_failed()` and `requeue_current()` methods.

### 2c. API endpoint — `history.py`

**File:** `src/stacks/api/history.py`

**Added endpoint:** `POST /api/history/retry_all`

**Location:** Right after the existing `api_history_retry()` function (after the closing `}` of its response).

**Code:**
```python
@api_bp.route('/api/history/retry_all', methods=['POST'])
@require_auth_with_permissions(allow_downloader=False)
def api_history_retry_all():
    if current_app.stacks_multiprocess:
        ops = get_queue_ops()
        success, message, count = ops.retry_all_failed()
    else:
        q = current_app.stacks_queue
        success, message, count = q.retry_all_failed()
    return jsonify({
        'success': success,
        'message': message,
        'count': count
    })
```

### 2d. Frontend — History button + JS

**File:** `web/index.html` — Added `refresh-line` button in History card header (line ~104):
```html
<button class="btn btn-warning" data-icon="refresh-line" onclick="retryAllFailed()" title="Retry all failed downloads"></button>
```

**File:** `web/script/app.js` — Added `retryAllFailed()` function (insert after existing `retryFailed()`).

**File:** `web/css/main.css` — Added `refresh-line` RemixIcon unicode mapping:
```css
[data-icon][data-icon=refresh-line]:before {
  content: "\f064";
}
```

---

## Change 5: Use DB filename column (hash-bearing) for file path instead of title

**Files:** `src/stacks/coordinator/download_worker.py`, `src/stacks/coordinator/queue_ops.py`

**What it does:** Two-part fix ensuring the hash-bearing `filename` from the DB is what actually lands on disk.

### Part A — `download_worker.py` (lines 254, 308)

**Before:** Both `download_direct()` and `download_from_mirror()` received `title=title`, where `title` is the DB `title` column (may lack hash due to `COALESCE` in `complete_scrape`).

**After:** `title=filename or title` — the DB `filename` column (which always has the hash) is preferred. `title` is used only as fallback if `filename` is null.

### Part B — `queue_ops.py` (line 337)

**Before:** `title = COALESCE(title, ?)` — preserved any pre-existing non-hash title forever.

**After:** `title = ?` — always overwrites `title` with the scraped filename (which carries the hash). Existing downloads self-heal on retry.

**Patch file:** `patches/06-fix-worker-pass-filename-not-title.patch`

## Change 4: Fix scraper not applying include_hash

**Files:** `src/stacks/coordinator/scraper_process.py`

**What it does:** The scraper process creates an `AnnaDownloader` but was missing the `include_hash` and `prefer_title_naming` config parameters. This meant filenames scraped from Anna's Archive never had the hash applied (regardless of the `include_hash` setting), so files saved to disk never included the hash.

**Bug location:** `scraper_process.py` lines 110-116 (original), the `AnnaDownloader()` constructor call was missing `prefer_title_naming` and `include_hash` parameters.

**Fix:** Added config reads and passed both parameters to `AnnaDownloader()`, matching what `download_worker.py` already does.

**Patch file:** `patches/05-fix-scraper-include-hash.patch`

**New code:**
```python
prefer_title_naming = config.get('downloads', 'prefer_title_naming', default=False)
include_hash = config.get('downloads', 'include_hash', default="none")

downloader = AnnaDownloader(
    output_dir=DOWNLOAD_PATH,
    incomplete_dir=incomplete_dir,
    flaresolverr_url=flaresolverr_url if flaresolverr_enabled else None,
    flaresolverr_timeout=flaresolverr_timeout_ms,
    prefer_title_naming=prefer_title_naming,
    include_hash=include_hash,
    proxy_config=proxy_config
)
```

## Change 3: Bulk Add Downloads

### 3a. API endpoint — `queue.py`

**File:** `src/stacks/api/queue.py`

**Added endpoint:** `POST /api/queue/add_bulk`

**Location:** Between the existing `api_queue_add()` (ending ~line 121) and `api_queue_pause()`.

**Request body:** `{"items": [{"md5": "...", "source": "manual", "subfolder": null}, ...]}`

**Response:** `{success, message, added, skipped, errors: [{md5, error}]}`

### 3b. Frontend — UI

**File:** `web/index.html` — Added toggle button and textarea section below the single input row (lines 50-60):
```html
<div class="add-item">
  <div class="card input-row">
    <input type="text" id="manual-add" ... />
    <button data-icon="file-add-line" class="btn btn-success" ...></button>
    <button class="btn btn-secondary toggle-bulk" onclick="toggleBulkAdd()" title="...">v</button>
  </div>
  <div id="bulk-add-section" class="card bulk-add-card" style="display:none;">
    <textarea id="bulk-add-input" placeholder="..." rows="6"></textarea>
    <button data-icon="file-add-line" class="btn btn-success" onclick="bulkAddDownloads()">Add All</button>
  </div>
</div>
```

### 3c. Frontend — JavaScript

**File:** `web/script/app.js` — Added `toggleBulkAdd()` and `bulkAddDownloads()` functions right after the existing `addDownload()` function.

### 3d. CSS

**File:** `web/css/main.css` — Added `.bulk-add-card`, `.bulk-add-card textarea`, `.bulk-add-card .btn-success`, `.toggle-bulk` selectors (inserted before `#current-download`).

---

## How to use this document with an LLM

Copy the entire contents of this file and provide it as context to the LLM along with these instructions:

> "Read `docs/guides/custom-changes-reference.md`. Apply all changes described there to the current codebase. Files have been reset to upstream state. Do NOT create backups or .md files — just apply the changes."

The LLM will need to:
1. Open each file listed
2. Find the locations described
3. Insert/replace the specified code blocks

## Patch files reference

| Patch file | Scope | Applies to |
|------------|-------|-----------|
| `patches/00-all-changes-comprehensive.patch` | ALL tracked file changes | All modified files |
| `patches/01-fix-suffix-hash.patch` | Suffix hash fix only | `html.py` |
| `patches/02-retry-all-failed-backend.patch` | Retry all — backend | `history.py`, `queue_ops.py`, `server/queue.py` |
| `patches/03-bulk-add-backend.patch` | Bulk add — backend | `api/queue.py` |
| `patches/04-frontend-changes.patch` | All UI/JS/CSS changes | `index.html`, `app.js`, `main.css` |
| `patches/05-fix-scraper-include-hash.patch` | Fix scraper missing hash params | `scraper_process.py` |
| `patches/06-fix-worker-pass-filename-not-title.patch` | Use `filename` column (hash) for file path instead of `title` | `download_worker.py`, `queue_ops.py` |
| `patches/99-local-docker-compose.patch` | Volume path config | `docker-compose.yml` |

## New files created (not in patches)

These files were created as documentation and are tracked separately:
- `docs/fixes/add-retry-all-failed-button.md`
- `docs/fixes/fix-suffix-hash-placement.md`
- `docs/fixes/add-bulk-add-downloads.md`
- `docs/guides/custom-changes-reference.md` (this file)
- `docs/guides/git-update-workflow.md`
- `patches/` (all `.patch` files)
- `backup_retry_all/` (full backup of change 1 + 2)
- `backup_bulk_add/` (full backup of change 3)
