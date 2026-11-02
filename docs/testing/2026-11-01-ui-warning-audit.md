# Scoped UI warning audit

Owner: Luna inspection worker. Date: 2026-11-01. Read-only source inspection and one scoped Impeccable detector pass; no styling changes or suppressions.

| Finding | Evidence | Disposition |
| --- | --- | --- |
| White text on orange count badges | style.css pending token #da7756 and unread/count badges; about 3.1:1 | Real contrast failure. Consider dark text while preserving orange fill. |
| White text on delete confirmation | style.css error token #f87171, .delete-bar-confirm; about 2.8:1 | Real contrast failure. Consider dark text or a darker red fill. |
| Purple accent text on dark surfaces | #7c3aed text, detector pairs about 3.1/3.2:1 | Requires selector-level rendered attribution before changing shared tokens. Lighter text token already exists. |
| Channels sidebar label | .channel-sidebar-header, 10px functional heading | Real match to the skill's legibility rule. Minimal proposed size is 11px. |
| Two cramped-padding reports | Detector line 0 generic divs, one hidden | Unresolved attribution. Do not add padding blindly. Hidden-state finding may be non-rendered. |
| Blue hover glow | .update-pill:hover, 8px shadow at 15% color | Real rule match, possibly intentional hover feedback. Low priority; no suppression applied. |

The contrast detector returned five records, including repeated orange results. Counts are detector records, not five independently attributed defects. User authorized investigation only; functional send/reply recovery remains the active implementation scope.
