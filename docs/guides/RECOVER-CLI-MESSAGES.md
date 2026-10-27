# Recover a CLI review message

If a managed CLI seat posted its answer in ordinary chat instead of completing the review turn, you can attach that existing message. Recovery uses the saved text and makes no model request.

1. Open **Recover a CLI message** from the stalled turn or its session history.
2. Enter the channel message number and choose **Preview message**. Message number 0 is valid.
3. Read the exact text and attribution. A verified message has matching machine turn metadata. An older message without complete turn metadata requires the explicit operator-attribution checkbox. The server still requires the original authenticated seat identity.
4. Choose **Attach as final answer** or **Attach as question**. A question waits for your answer through the normal Continue turn control.

Close or Escape returns to the review. After attaching a question, Close focuses the answer field. Changing channels hides the recovery panel.

## Content and worker release

Attachment records the content once and fences the outstanding attempt. It does not stop the CLI or prove that its process has ended. The physical seat remains held until both the owned worker and its CLI child have genuine exit evidence. Other seats remain usable.

**Check worker release** repeats the same accepted decision and checks the transport evidence. It never terminates a worker. An uncertain acknowledgement can be retried without generating another answer or admitting the message twice. Session history retains this release check after reload.

## Which messages qualify

The message must be ordinary chat in the review channel, with the authenticated immutable identity of the expected CLI seat. A matching display name alone is insufficient. Imported history, quarantined messages, typed review projections, conflicting turn metadata and messages already used by another review cannot be attached.

After an explicit Retry, an original CLI message can qualify through the preserved source-attempt lineage. The current replacement must still be unconsumed. Recovery preserves the original source identity separately and fences that replacement. Late replacement output is rejected and quarantined.

A pending selection cannot bypass Stop, corrected or superseded runs, or unfinished retry preparation. If the source changed since preview, preview it again. An exact already-accepted request remains acknowledged after later Stop or source deletion; it never re-admits content or advances a successor twice.

## Verification scope

Verified with actual Windows workers, hidden local fake CLI clients, MCP and a local fake HTTP provider, including final answers, legacy questions, recovery after Retry, Stop refusal and browser attachment. Live AI clients, remote compute cancellation and native Linux/Omarchy behavior are outside this verification.
