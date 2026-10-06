import type { PublicQuality } from "./api";

export type QualityLine = { label: string; text: string };

const stars = (value: number | null | undefined) => (typeof value === "number" ? `${value} of 5` : "no rating");

/**
 * Plain-language lines for a community's public regulator record. Display only: nothing here
 * ranks or scores. A missing record is stated as "no record", never as a low grade or rating.
 */
export function publicQualityLines(quality: PublicQuality | null | undefined): QualityLine[] {
  if (!quality) return [];
  if (quality.kind === "NV_STATE_INSPECTION") {
    const lines: QualityLine[] = [];
    if (quality.latest_grade) {
      const below = Object.entries(quality.grades_below_a || {}).map(([g, n]) => `${n} × ${g}`).join(", ");
      lines.push({
        label: "State inspection",
        text: `Latest grade ${quality.latest_grade}${quality.latest_grade_date ? ` (${quality.latest_grade_date})` : ""}; ${quality.graded_inspections} graded inspection${quality.graded_inspections === 1 ? "" : "s"} on record${below ? `, of which below A: ${below}` : ""}.`,
      });
    } else {
      lines.push({ label: "State inspection", text: "No graded inspection on record yet. This is not a negative finding." });
    }
    if (quality.disciplinary_action_on_record) lines.push({ label: "State sanction", text: "A state disciplinary action is on record; see the source for details." });
    lines.push({ label: "Source", text: `${quality.source_label}. ${quality.caveat}` });
    return lines;
  }
  if (quality.kind === "CMS_FIVE_STAR") {
    return [
      { label: "Medicare Five-Star", text: `Overall ${stars(quality.overall)} — inspections ${stars(quality.health_inspection)}, staffing ${stars(quality.staffing)}, quality measures ${stars(quality.quality_measures)}${quality.as_of ? ` (as of ${quality.as_of})` : ""}.` },
      { label: "Source", text: `${quality.source_label}. ${quality.caveat}` },
    ];
  }
  return [{ label: "Public record", text: quality.statement || "No public inspection or rating record was found. This is not a negative finding." }];
}

export function publicQualityLink(quality: PublicQuality | null | undefined): string | null {
  const url = quality && "source_url" in quality ? quality.source_url : null;
  return url && /^https?:\/\//i.test(url) ? url : null;
}
