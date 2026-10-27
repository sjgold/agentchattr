# Review one document or source file

Open **Start a session**, choose a review design, and select **Choose UTF-8 file**. The same source controls are available when running a drafted design.

The preview shows the literal text, filename, byte size, SHA-256 and source ID. Check those details, assign the roles and select **Start Session**. Every CLI and API turn receives the frozen source, even after the conversation grows beyond the recent-message window. Editing or deleting the original file after Start leaves that review unchanged.

## Files and previews

- Select one plain UTF-8 file, up to **512 KiB (524,288 bytes)**. The limit counts bytes, including a leading UTF-8 BOM.
- The picker suggests common document and source extensions. Other plain-text files are accepted, including `.rs`, `.sql`, `Makefile` and extensionless files. Choose **All files** in the dialog if its filter hides them.
- Original CRLF, LF, bare CR, Unicode and a leading BOM are preserved in the stored snapshot. The textarea displays browser-normalized line endings; Start submits the canonical snapshot shown by the preview, rather than reading that textarea back.
- An empty file is allowed and marked **0 bytes (empty source)**. A BOM is marked **UTF-8 BOM present, preserved**. Both require an explicit Start.
- Source code, Markdown fences, mentions and HTML tags remain literal text. Selecting a file adds no new filesystem tools; existing client and tool permissions still apply.

Invalid UTF-8, NUL, disallowed ASCII controls and DEL are rejected. Errors identify the code point or UTF-8 byte offset without echoing source content. Content C1 code points are accepted as text. Filenames must be basenames without separators, colon, Unicode control/format characters, line separators, or a trailing ASCII space or dot.

## Keeping your draft

Choosing a file keeps your pasted draft. **Use pasted text** restores it and returns focus to the editor. Cancelling the picker leaves the current selection alone.

If a replacement file fails validation, the previous preview stays visible with **Previous preview, not ready to start**. Start remains blocked until you choose a valid file or switch to pasted text. A file check times out after eight seconds and keeps the draft; it never starts a review automatically.

A refused Start keeps the source and other settings. After an unconfirmed Start or connection error, check the conversation before trying again: the request may already have created a run. There is no automatic resend.

## Correcting a stopped file review

The restart panel labels the original filename and line endings. A corrected restart creates a new **pasted snapshot** and retains the original file review in history.

Make an actual content edit. For file-origin parents, byte-identical text and changes consisting only of CRLF/CR/LF conversion are treated as unchanged, because browser textareas normalize newlines. For a line-ending-only conversion, start a separate review from the converted file. The original stored bytes and hash are preserved.

## Operator API

`POST /api/documents/preview?filename=<encoded basename>` accepts a raw byte body with `Content-Type: application/octet-stream` and the operator's `X-Session-Token`. Encode the filename once, including literal plus as `%2B`. A raw query plus, missing/duplicate/unknown fields or malformed encoding returns 400. Agent bearer credentials cannot preview or start a file review.

The preview returns exactly:

```text
version, kind, source_id, name, encoding, byte_length, content_sha256, text
```

Echo that full object as `source_file` in the existing `POST /api/sessions/start` body, alongside the template or draft id, channel and cast. Omit `input_text` entirely for a file Start. For a pasted Start, send `input_text` and omit `source_file`. Including both keys is rejected even when the pasted value is empty.

The server recomputes the snapshot's size, hash and source ID at Start. This establishes self-consistency; the filename and file label are operator assertions, not attestation of an operating-system file path. Previews create no document library or stored upload. The run stores the text with its file metadata; briefs revalidate that metadata and place it only in the untrusted source packet. Existing run/turn/attempt and result authority checks continue to apply.

Current scope is one file. Multi-file packets, directory crawling and PDF/office-format extraction are separate work. Verification results and platform limits are recorded in [STATUS.md](STATUS.md).
