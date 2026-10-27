# Start a review with frozen source

Use **Start a session** in chat. Keep using **Design a session / Ask** to request an editable coordinator proposal, or choose a saved template. Assign the participants, enter the task brief, and paste the review source into **Pasted review source**. Source can be empty for a document-free task.

**Start** saves the accepted design, cast, source, task brief and active rules with their revisions. Later edits to a template, rules or the form do not change that run. If input is too large or invalid, Start reports an error and retains the dialog text for editing.

Current UTF-8 limits are 32 KiB for the task brief, 512 KiB for pasted source, 32 KiB for frozen rules, and 256 KiB for prior results. These are byte limits; non-ASCII characters can occupy several bytes. Input is rejected in full when it exceeds a limit. Existing role/phase/participant capacity limits remain until ticket #16.

Each dispatched participant receives a reference to a frozen, seat-scoped brief. API seats fetch it directly. CLI seats receive an instruction to call **chat_review_brief** with its brief ID, then respond in the session's channel. The brief contains the assigned role, phase instructions, task, frozen rules, exact source revision and relevant prior results. Recent chat supplements the brief; a 20-message window cannot replace or displace its source.

The application preserves pasted code, mentions and instructions as untrusted text, without executing them or treating them as tool permissions. A missing, malformed or wrong-seat brief is rejected. The API adapter refuses its provider request when retrieval fails; CLI instructions require successful retrieval before answering and prohibit chat-only fallback. Actual native-client behavior still needs live acceptance. Authentication ties retrieval to the seat identity that received the turn; relaunching another instance with the same visible name does not inherit access.

The input and design snapshots survive as local records. Older sessions created before this feature retain their historical behavior; start a new session to obtain frozen inputs. This ticket does not provide durable queue/outbox delivery, explicit completion admission, automatic restart reconciliation or Stop cancellation; those remain tickets #7-10. A normal participant chat message can still advance a session until #8 changes that contract.

Routine checks use fake clients and a loopback fake provider. Real CLI login/MCP behavior and native Linux/Omarchy compatibility require separate authorized acceptance. CLI readiness in pre-flight continues to mean mention injection readiness, with provider authentication/model confirmation tracked separately.
