# Fix: Suffix hash placement in filename

## File Modified
`src/stacks/downloader/html.py`

## Original Behavior
When `include_hash` was set to `suffix`, the hash was appended after the full filename including its extension:
- Input: `book.pdf`, MD5: `d6e1dc51a50726f00ec438af21952a45`
- Output: `book.pdf - d6e1dc51a50726f00ec438af21952a45`

This broke the file extension, making the file unopenable by its type.

## Fixed Behavior
The hash is now inserted before the extension, preserving the file type:
- Input: `book.pdf`, MD5: `d6e1dc51a50726f00ec438af21952a45`
- Output: `book - d6e1dc51a50726f00ec438af21952a45.pdf`

## Code Change (line 238)
The suffix case now splits the filename into stem and extension using `rpartition('.')`, inserts the hash between them, and re-appends the extension. If no extension is found (odd case), it falls back to the original behavior as a safety measure.
