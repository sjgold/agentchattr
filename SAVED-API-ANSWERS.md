# Deliver a saved API answer

Managed API review turns save a verified final answer or question before their first delivery attempt. A failed post can be recovered without another model call.

1. Open **Check saved answers** in the interrupted or stalled review. You can also use **Saved answers** on its session-start banner in chat history, including after a reload.
2. Read the preview. The pending answer appears first; previously admitted answers remain available below it.
3. Choose **Deliver saved answer**. The server checks the original review, seat identity and current attempt before admitting it.

**Refresh** checks availability again. **Close** restores the review controls. Opening a preview never delivers an answer automatically. Retry remains a separate action that creates a new attempt and can call the model again.

A recovered question waits for your answer through the existing Continue control. It does not silently finish the review.

## Delivery and worker release

Content admission and process lifetime are separate. If the original worker's exit is unproven, its seat stays held while unrelated seats can proceed. **Check worker release** checks the original worker and model lifecycle again. A successful release check clears that hold without another model call.

Repeating an exact admitted delivery acknowledges the existing event, even after a later Stop or Retry. An unadmitted answer from a stopped or superseded attempt is blocked and retained for history. The preview reports the current server decision.

## What is preserved

The original signed identity, exact text, source revision, accepted earlier results and review rules are retained. Recovery uses browser operator authentication; it does not revive a revoked worker bearer or impersonate a replacement seat. Quoted mentions and slash commands in review answers stay display data and cannot wake other agents.

Saved files and separate acknowledgement records remain in the application's private runtime data. Changing a saved file invalidates its seal. Keep the corresponding review data and private brief authority together; this feature is not a standalone file-import mechanism.

## Scope and verification

This applies to managed frozen API review finals and questions. Ordinary chat/jobs, unmanaged wrappers and selected CLI-message recovery are outside this feature.

Windows verification uses local fake providers and actual owned worker processes. Cold final/question delivery, lost acknowledgements, pending Stop refusal and explicit browser delivery pass. Live AI providers, native Omarchy and remote-provider compute cancellation remain unverified.
