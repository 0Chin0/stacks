# Feature: Bulk Add Downloads

Adds the ability to paste multiple MD5 hashes or Anna's Archive URLs at once, instead of adding them one by one.

## Files Modified

### 1. `src/stacks/api/queue.py`
- **Added:** `POST /api/queue/add_bulk` endpoint
- Accepts a JSON object: `{"items": [{"md5": "...", "source": "...", "subfolder": "..."}, ...]}`
- Processes each item through the existing `add_download()` / `add()` method
- Returns a summary: `{success, message, added, skipped, errors: [...]}`

### 2. `web/index.html`
- **Added:** A collapsible "Bulk Add" section below the single-input row
- Contains a `<textarea>` for pasting multiple MD5s/URLs (one per line) and a "Add All" button
- The single-input row remains unchanged for quick one-off additions

### 3. `web/script/app.js`
- **Added:** `bulkAddDownloads()` JavaScript function
- Splits the textarea value by newlines, extracts MD5 from each line
- Sends all valid MD5s to `/api/queue/add_bulk`
- Shows a detailed toast: "Added X, skipped Y (already in queue), Z invalid"
- Clears the textarea on success

## Backup
Full backup of `src/`, `web/`, `files/`, `requirements.txt`, and `VERSION` is stored in `backup_bulk_add/`.
