// Reuse small decisions, but let the server rebuild large ones from the original
// questionnaire instead of uploading the complete diagnostic/evidence graph.
export function boundPersonalReportRequest<T extends { decision_result?: Record<string, unknown> }>(payload: T): T {
  if (!payload.decision_result || new TextEncoder().encode(JSON.stringify(payload)).byteLength <= 512 * 1024) return payload;
  const { decision_result: _decision, ...request } = payload;
  return request as T;
}
