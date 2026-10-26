# Manage channels safely

Open **Manage channels** beside the channel tabs, or **Manage** in the sidebar. Choose a channel and preview an action before confirming it. The preview shows the affected records and any work that must finish first. `general` stays protected.

| Action | What happens |
| --- | --- |
| Create | Registers a new active name. Reserved old names cannot be reused. |
| Rename | Moves chat and mutable channel references. The old name stays reserved. Frozen review inputs, typed journals and queue audit records keep their original authority. |
| Archive | Keeps history and saved records, hides the channel from active navigation and blocks new chat, reviews and automatic routing. |
| Reopen | Makes an archived channel writable again. The preview discloses enabled overdue schedules. |
| Delete | Removes channel chat and todos. Jobs, reviews, schedules, summaries, authored artifacts and upload references remain retained. Upload files stay on disk. |
| Cancel queued only | Cancels only the exact queued dispatches in its preview. Active or uncertain work stays untouched. This action never chains into archive or delete. |

Type the exact displayed channel name to confirm. Changing a rename destination invalidates its preview. The UI refetches the catalog after a change; it keeps your draft while a request is refused or unconfirmed.

## Busy channels and repair

Finish or explicitly Stop live reviews before renaming, archiving or deleting their channel. The blocker list identifies outstanding sessions, dispatches and pending history projections. Channel management never stops a worker or cancels remote computation for you.

Pending authored-artifact requests also block rename, archive and delete. **Cancel queued only** saves a queued artifact request as cancelled before fencing its dispatch. If fencing fails, the response reports the saved cancellation and unconfirmed dispatches. Refresh the preview and retry queued cancellation to repair the fence. Active work stays untouched. A refused queued request returns 409 with the refused request IDs and any earlier saved changes. Refresh the preview before trying again.

**Repair history** projects pending results for completed or stopped runs. A live pending projection is labeled as requiring a wait or restart. Reopening also attempts scoped terminal-history repair. Typed results and receipts remain admissible while chat is read-only; a late result can therefore stay unprojected while archived and appear after reopening. Legacy reviews remain readable and do not acquire an unrecoverable projection blocker.

An interrupted rename or delete leaves a durable repair intent. Its named channels stay held while peers remain usable. Restart preserves that hold. Use the exact-name **Retry repair** control to resume; startup does not silently finish a destructive action. A rename holds both names until it finishes.

If the catalog itself is unreadable, channel writes and queue claims are held. Existing queue release, Stop and typed-result admission stay available. A held Jobs or schedules file gets its own alert while healthy chat continues. Management previews need a complete storage view: an unreadable retained-upload catalog or authored-artifact index pauses create, reopen, archive, rename and delete, including reopening an archived channel. The catalog marks authored counts as unavailable while healthy owners remain readable. A damaged individual artifact body leaves metadata available. Repair storage before trying again. Ordinary queued-chat cancellation and review-history repair remain available while the authored index is held. Queued artifact cancellation still needs readable authored metadata.

## Reading archived and deleted channels

The selected channel stays visible as a read-only view after archive or delete. The composer and session controls show why they are disabled. **Back to general** is an explicit choice.

In Manage, **View retained records** reads the summary, job conversations and stopped review source/journal. Retained schedules and jobs are read-only, including deletion and reorder. Jobs from inactive channels cannot be dragged or used as reorder targets.

Delete previews count **attachment references**. The retained view counts **messages with attachments** and lists their files. These are different units. Only safe owned upload links are clickable; other saved attachment fields remain inert metadata. Artifact purge is not supported.

Authored-artifact counts include lineages with no completed version, all request attempts, version totals and copied-source bytes. **View retained records** shows bounded lineage, head-version and pending-request metadata. Delete previews disclose that authored artifacts and their copied source remain in retained audit and backups.

Old aliases and deleted names refuse new writes. Delayed ordinary callbacks on an inactive channel are dropped and do not reroute on reopening. They never redirect to `general`.

## Schedules, imports and uncertain requests

An enabled overdue schedule fires once on the next ordinary tick after reopening, then follows its normal cadence. Missed intervals are not replayed. The scheduler durably advances or disables a row before sending: a crash or policy failure between that reservation and publication can lose one fire. A failed reservation sends nothing. Targets already enqueued before another target fails are retained, with no automatic retry within the interval. A failed one-shot stays inactive until explicitly enabled again.

Configured import reports rows redirected from inactive or reserved names to `general` with reason `channel_retired`; summaries for remapped names are skipped. An import started during a pending channel repair is refused (409). If a repair appears mid-import, names not yet registered redirect to `general` with reason `channel_repair_pending`. New names otherwise pass through catalog registration. Partial job imports report landed/skipped rows and the re-import limitation: an existing job UID is skipped as a whole, so re-importing the archive does not fill its missing conversation rows.

The current archive export and import **exclude retained-artifacts metadata**. Keeping upload bytes on disk does not make the archive a backup of those source references. Preserve the owned data directory separately when those references matter.

Authored Markdown artifacts, when present, travel with the history backup in schema 2. The ZIP includes every version, failed or pending attempt, historical producer/model labels and its frozen source packet. Import restores them as read-only history and starts no agent work. Re-import skips an identical lineage; a conflicting identifier skips the whole lineage and leaves local versions intact. History-only backups keep schema 1.

While authored metadata is held, history imports can use existing active channels. New channel names redirect to `general` with the reported reason `artifact_owner_held`. An artifact lineage that needs a new channel is skipped and reported as `channel_unavailable`. The import report includes fixed repair guidance.

Copied source text survives deletion of the original chat and is included in artifact backups. Those packets also keep the message and attachment metadata that was saved with the chat. Treat the ZIP as sensitive as the channel history. Upload files and the separate retained-upload reference catalog still need an owned-data-directory backup.

Artifact-bearing backups have two 50 MiB limits: total uncompressed members and the final ZIP. The artifact index is limited to 4 MiB, the manifest to 64 KiB, and the archive to 4,096 members and 1,024 lineages. With a source packet per attempt, the member limit allows roughly 2,000 versions; unversioned attempts use space too. A source packet can hold up to 2 MiB, so about 25 full-size attempts can exhaust the raw-byte budget. Export refuses the whole backup when a limit is exceeded and reports the bound, byte counts and dominant section.

Read the import report even when some data was skipped. An invalid or conflicting lineage leaves healthy peers available to import. A later storage failure can leave earlier rows saved; the report marks that partial result and lists the committed counts. Earlier commits survive an import failure.

After a connection failure or unconfirmed management request, reload the catalog and inspect the current state before trying again. A committed rename can report a settings-projection warning; catalog reads repair that projection without replaying the rename. A decision reply whose card was saved as resolved but whose publication was unconfirmed needs a manual resend if the reply is absent. The error explains that distinction.

## Artifact authoring remains disabled

Ticket 20 authoring remains disabled while the approved store redesign is specified and tested. The proposed store-wide limit of 128 saved requests and 512 KiB of metadata was withdrawn after sizing showed that existing diagnostic records alone exceed it. No such quota is enabled. Seth approved the three storage/compatibility slices recorded in [the storage decision memo](TICKET-20-STORE-DECISION.md).

Any future finite quota would count failed, cancelled and imported attempts across all channels, and a successful import could consume it. Exporting or deleting a channel would leave that quota unchanged because artifact purge is unsupported. No replacement quota has been selected.

In the Ticket 20 storage candidate, diagnostic logs use a separate private file. Diagnostic logs and retained diagnostic bodies are excluded from channel backups. Deleting a channel retains those diagnostic files. The candidate remains under review and artifact authoring stays disabled.

## Verification and limits

Ticket 19 channel-lifecycle acceptance used a managed local fake CLI client with real MCP, plus separate Traycer-managed isolated Electron Chromium browser runs by Codex and Sonnet. No live AI/provider, installed-client, Omarchy, OS drag/picker or assistive-technology compatibility is claimed. Synthetic browser DragEvents exercised the actual job handlers, with network and persisted-order checks. Full discovery at the final product freeze ran 1,374 tests with four platform skips, run by the implementation owner and not re-run by the reviewer.

At 390 CSS pixels the Manage dialog measured 356 pixels wide, with 14px text and controls at least 45.3px high. The inherited page still overflows to 476px. Hover reveals can take about a second to settle in the tested runtime; keyboard focus reveals the same actions. Touch/coarse-pointer behavior has static/VM coverage only.

Local rename timing with a 33.9MB message log, 11.6MB jobs file and 3.3MB sessions file measured individual holds around 0.27 to 0.29 seconds. The engine boundary is released between steps. These are measurements for that shape and disk, not a general latency guarantee.

[Independent review and method limits](REVIEW-CLAUDE-TICKET-19.md) distinguish component tests, native evidence and each observer's browser coverage. The isolation guard covers its listed Python operations; its documented blind spots include pre-hook startup, direct native calls and unlisted path operations. [STATUS.md](STATUS.md) records publication state.

Ticket 20 artifact-backup checks currently cover temporary stores, in-memory ZIPs and in-process API handlers. Its native and rendered-browser acceptance is still pending; [STATUS.md](STATUS.md) distinguishes implementation, review and publication.
