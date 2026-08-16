# Feature: Retry All Failed Downloads

Adds a "Retry All" button to the History tab that retries every failed download in one click, instead of requiring the user to click each item individually.

## Files Modified

### 1. `src/stacks/coordinator/queue_ops.py`
- **Added:** `retry_all_failed()` method (multi-process mode)
- Counts all downloads with `status = 'failed'`, resets them to `status = 'pending_scrape'` with `error = NULL`, and returns the count.

### 2. `src/stacks/server/queue.py`
- **Added:** `retry_all_failed()` method (debug/single-process mode)
- Same logic as above but for the in-memory queue used in debug mode.

### 3. `src/stacks/api/history.py`
- **Added:** `POST /api/history/retry_all` endpoint
- Calls the appropriate backend method depending on the running mode (multi-process or debug).
- Returns `{success, message, count}`.

### 4. `web/index.html`
- **Added:** "Retry All" button (`btn btn-warning` with `refresh-line` icon) next to the existing "Clear History" button in the History card header.

### 5. `web/script/app.js`
- **Added:** `retryAllFailed()` JavaScript function that calls the new API endpoint and shows a toast notification with the count of retried downloads.
- Includes a `confirm()` dialog before proceeding to prevent accidental clicks.

## Backup
Full backup of `src/`, `web/`, `files/`, `requirements.txt`, and `VERSION` is stored in `backup_retry_all/`.
