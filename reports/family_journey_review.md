# Family Journey Review

## Part 3: End-to-End Family Journey

Journey:

Family -> Questionnaire -> Matching -> Narrative -> Verification -> Provider Response -> Updated Recommendation -> Contact Provider -> Move In -> Outcome Learning

## Journey Stage Review

| Stage | What Works | Weak Points | Impact |
| --- | --- | --- | --- |
| Questionnaire | Rich need capture and preference logic | Limited save-and-resume/session continuity APIs | Drop-off risk in longer flows |
| Matching | Deterministic scoring and audit traces | Heavy client-side execution and policy fragmentation | Reproducibility and support burden risk |
| Narrative | Family language improving | Evidence-link runtime enforcement incomplete | Trust risk for clinical claims |
| Verification | Unknown handling and request flow present | Inbox SLA + reminder UX incomplete | Delayed decision velocity |
| Provider Response | Memory persistence and conflict handling exists | Full operational turnaround workflow missing | Slower recommendation updates |
| Updated Recommendation | Simulation supports re-ranking | Event-level lifecycle not fully productized | Harder to explain changes over time |
| Contact Provider | Basic pathways exist | No full contact orchestration and CRM sync | Conversion leakage |
| Move In | Outcome model exists | Real workflow instrumentation uneven | Weak attribution confidence |
| Outcome Learning | Benchmarks and reports are strong | Need production telemetry scale and deployment gates | Slow model improvement cadence |

## High-Impact Journey Breakpoints

1. Long questionnaire sessions without strong persistence and handoff.
2. Verification wait periods with limited family-facing status transparency.
3. Contact and move-in step tracking not tightly integrated into recommendation lifecycle.
4. Outcome learning not yet tightly coupled to controlled production model/policy release.

## Recommended Family Experience Improvements

1. Save-resume and household collaboration for questionnaire.
2. Family-visible verification timeline with expected response windows.
3. Updated recommendation change-log view with explanation deltas.
4. Contact-provider orchestration panel with reminders and status.
5. Move-in and post-move-in outcome capture with privacy-safe prompts.
6. Personalized explanation style options (concise, detailed, clinical).

## Family Value Assessment

Current family value proposition is strong in transparency and recommendation rationale, but conversion and confidence can increase substantially with stronger verification visibility, lifecycle tracking, and closed-loop feedback integration.
