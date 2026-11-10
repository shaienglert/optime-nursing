# Case-specific facility reply

Prototype: [community response](oomnik-facility-reply.html). Fictional data only; the demo does not send email, upload files or persist responses.

## Integrated flow

1. From their results, the family selects a community and previews the details they authorize OOmnik to share. The summary uses their confirmed functional needs and preferences; omit identifying and unrelated medical information.
2. Reuse the facility outreach draft and staff approval flow. The email links to a scoped, expiring reply; show the full case summary in the reply view. Keep the generic room inquiry available for requests without a family case.
3. Generate checklist rows from the approved snapshot. Each row has a stable need ID, MUST/NICE classification and an optional answer: Yes, No or Depends. Blank means unanswered. Allow notes, optional attachments and a partial response. Limit attachments and keep them private.
4. Store the response against the original request, family case and facility. Acknowledge only after it has been saved. Do not report a complete match while any MUST remains unanswered or conditional. A negative MUST rules out this option for the case under existing evidence rules.
5. Keep case-specific price and availability private. Keep facility claims in the case with the reply date and provider-reported status. Publishing reusable claims through the facility evidence workflow requires a separate review integration. Unverified claims do not change ranking. Do not copy case notes or attachments into public profiles.

Principle impact: no change to consent, evidence handling, or ranking. Implementation completion under existing outreach and evidence rules.
