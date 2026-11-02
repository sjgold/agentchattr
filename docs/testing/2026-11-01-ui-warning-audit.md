# Scoped UI warning audit

Owner: Luna inspection worker. Date: 2026-11-01. Initial pass: read-only source inspection and one scoped Impeccable detector pass. The authorized follow-up below changed one label; no suppressions were added.

| Finding | Evidence | Disposition |
| --- | --- | --- |
| White text on orange count badges | style.css pending token #da7756 and unread/count badges; about 3.1:1 | Real contrast failure. Consider dark text while preserving orange fill. |
| White text on delete confirmation | style.css error token #f87171, .delete-bar-confirm; about 2.8:1 | Real contrast failure. Consider dark text or a darker red fill. |
| Purple accent text on dark surfaces | #7c3aed text, detector pairs about 3.1/3.2:1 | Requires selector-level rendered attribution before changing shared tokens. Lighter text token already exists. |
| Channels sidebar label | .channel-sidebar-header, formerly 10px | Fixed to 12px after Seth authorized judgment. Actual browser computed 12px, visible, no horizontal overflow; screenshot inspected. Sonnet source review PASS. |
| Two cramped-padding reports | Detector line 0 generic divs, one hidden | Unresolved attribution. Do not add padding blindly. Hidden-state finding may be non-rendered. |
| Blue hover glow | .update-pill:hover, 8px shadow at 15% color | Real rule match, possibly intentional hover feedback. Low priority; no suppression applied. |

The contrast detector returned five records, including repeated orange results. Counts are detector records, not five independently attributed defects. The two padding reports remain unmapped and unsuppressed; no speculative spacing changes were made. Other contrast and hover findings remain open for a separately bounded pass.
