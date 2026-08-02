"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
  ApiRequestError,
  fetchLiveFacilityProfile,
  type LiveFacilityAction,
  type LiveFacilityFact,
  type LiveFacilityProfile,
} from "@/lib/api";

type TabId =
  | "overview"
  | "clinical"
  | "rehabilitation"
  | "staffing"
  | "quality"
  | "experience"
  | "lifestyle"
  | "pricing"
  | "evidence"
  | "actions";

type RequestedField = { label: string; ids: string[] };

const TABS: Array<{ id: TabId; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "clinical", label: "Clinical Care" },
  { id: "rehabilitation", label: "Rehabilitation" },
  { id: "staffing", label: "Staffing" },
  { id: "quality", label: "Quality & Safety" },
  { id: "experience", label: "Resident Experience" },
  { id: "lifestyle", label: "Lifestyle & Amenities" },
  { id: "pricing", label: "Pricing & Availability" },
  { id: "evidence", label: "Evidence & Sources" },
  { id: "actions", label: "Actions" },
];

const FIELDS: Record<Exclude<TabId, "overview" | "experience" | "evidence" | "actions">, RequestedField[]> = {
  clinical: [
    ["Skilled nursing", "skilled_nursing_capabilities"], ["24/7 nursing", "nursing_24_7"],
    ["Long-term care", "long_term_care"], ["Short-term rehabilitation", "short_term_rehab"],
    ["Post-acute care", "post_acute_care"], ["Memory care", "memory_care"],
    ["Stroke rehabilitation", "post_stroke_neuro_evidence"], ["Neurological rehabilitation", "post_stroke_neuro_evidence"],
    ["Cardiac rehabilitation", "cardiac_rehabilitation"], ["Orthopedic rehabilitation", "orthopedic_rehabilitation"],
    ["Respiratory care", "respiratory_trach_vent"], ["Wound care", "wound_care"], ["IV therapy", "iv_therapy"],
    ["Medication management", "medication_support"], ["ADL assistance", "adl_support"],
    ["Transfer assistance", "transfer_assistance"], ["Fall management", "fall_management"],
    ["Dementia support", "dementia_alz_programs"], ["Hospice", "hospice_palliative_arrangements"],
    ["Respite care", "respite_care"],
  ].map(([label, id]) => ({ label, ids: [id] })),
  rehabilitation: [
    ["Physical therapy", "pt"], ["Occupational therapy", "ot"], ["Speech therapy", "speech_therapy"],
    ["Therapy days per week", "therapy_days_per_week"], ["Therapy frequency", "therapy_frequency"],
    ["Therapy staffing", "therapy_staffing"], ["In-house or contracted therapy", "therapy_delivery_model"],
    ["Therapy gym", "therapy_gym"], ["Stroke-specific program", "post_stroke_neuro_evidence"],
    ["Neurological rehabilitation", "post_stroke_neuro_evidence"], ["Rehabilitation outcomes", "hospital_claims_outcomes"],
    ["Functional improvement", "functional_adl_outcome_signal"],
    ["Successful discharge to community", "successful_discharge_community"],
  ].map(([label, id]) => ({ label, ids: [id] })),
  staffing: [
    ["RN hours per resident day", "rn_hours_per_resident_day"], ["LPN/LVN hours", "lpn_lvn_hours"],
    ["CNA hours", "cna_hours"], ["Total nurse staffing", "total_nurse_hours_per_resident_day"],
    ["Weekend staffing", "weekend_staffing"], ["Staff turnover", "staffing_turnover"],
    ["Administrator turnover", "administrator_turnover"], ["Therapy staffing", "therapy_staffing"],
    ["Medical director", "medical_director"], ["Nurse practitioner coverage", "nurse_practitioner_coverage"],
    ["Staffing rating", "staffing_rating"], ["Agency staffing reliance", "agency_staffing_reliance"],
    ["Staffing shortages", "staffing_shortages"],
  ].map(([label, id]) => ({ label, ids: [id] })),
  quality: [
    ["Overall CMS rating", "overall_cms_rating"], ["Health inspection rating", "inspection_rating"],
    ["Staffing rating", "staffing_rating"], ["Quality measures rating", "quality_measures"],
    ["Short-stay quality", "short_stay_quality"], ["Long-stay quality", "long_stay_quality"],
    ["Hospitalization measures", "hospital_claims_outcomes"], ["Rehospitalization", "rehospitalization"],
    ["Emergency-room visits", "emergency_room_visits"], ["Successful discharge", "successful_discharge_community"],
    ["Pressure ulcers", "pressure_ulcers"], ["Falls", "falls"], ["Medication issues", "medication_issues"],
    ["Infection measures", "infection_control_findings"], ["Weight loss", "weight_loss"],
    ["Vaccination measures", "hospital_claims_outcomes"], ["Inspection history", "deficiency_count"],
    ["Deficiencies", "deficiency_count"], ["Deficiency tags", "deficiency_tags"],
    ["Severity", "deficiency_severity"], ["Immediate-jeopardy findings", "deficiency_severity"],
    ["Complaint inspections", "complaint_related_findings"], ["Infection-control citations", "infection_control_findings"],
    ["Abuse findings", "abuse_findings"], ["Fire-safety findings", "fire_safety_deficiencies"],
    ["Fines", "penalties_fines"], ["Payment denials", "payment_denials"],
    ["Enforcement actions", "sanctions_final_orders"],
  ].map(([label, id]) => ({ label, ids: [id] })),
  lifestyle: [
    ["Room types", "private_shared_rooms"], ["Private rooms", "private_shared_rooms"],
    ["Shared rooms", "private_shared_rooms"], ["Bathrooms", "bathrooms"], ["Dining", "dietary_capabilities"],
    ["Kosher food", "kosher"], ["Gluten-free accommodation", "gluten_free"], ["Special diets", "dietary_capabilities"],
    ["Dietitian support", "dietary_capabilities"], ["Activities", "activities"], ["Movies", "movies"],
    ["Music", "music"], ["Religious services", "religious_cultural_services"],
    ["Jewish cultural support", "religious_cultural_services"], ["Hebrew-speaking staff", "languages"],
    ["Spanish-speaking staff", "languages"], ["Outdoor space", "outdoor_space"],
    ["Transportation", "transportation"], ["Visiting hours", "visiting_hours"],
    ["Family engagement", "family_engagement"],
  ].map(([label, id]) => ({ label, ids: [id] })),
  pricing: [
    ["Current availability", "current_availability"], ["Available beds", "current_availability"],
    ["Waiting list", "waiting_list"], ["Private-pay price", "current_price"],
    ["Medicare eligibility", "medicare_attributes"], ["Medicaid eligibility", "medicaid_attributes"],
    ["Accepted insurance", "payer_information"], ["Deposit", "deposit"], ["Additional fees", "fees"],
    ["Contract terms", "contract_terms"], ["Admission requirements", "admission_requirements"],
    ["Last pricing verification", "current_price"], ["Last availability verification", "current_availability"],
  ].map(([label, id]) => ({ label, ids: [id] })),
};

const REVIEW_SOURCES = ["Google", "Facebook", "Yelp", "Seniorly", "Caring.com", "A Place for Mom", "SeniorAdvisor", "Facility-owned testimonials", "News", "Staff review sites"];
const STATUS_FILTERS = ["VERIFIED", "PARTIALLY_VERIFIED", "CLAIMED_BY_FACILITY", "INFERRED", "CONTRADICTED", "STALE", "UNKNOWN"];

function statusClass(status: string): string {
  const normalized = status.toUpperCase();
  if (normalized === "VERIFIED") return "border-emerald-200 bg-emerald-50 text-emerald-800";
  if (normalized === "PARTIALLY_VERIFIED") return "border-amber-200 bg-amber-50 text-amber-800";
  if (normalized === "CLAIMED_BY_FACILITY") return "border-sky-200 bg-sky-50 text-sky-800";
  if (normalized === "CONTRADICTED") return "border-red-200 bg-red-50 text-red-800";
  if (normalized === "STALE") return "border-zinc-300 bg-zinc-100 text-zinc-700";
  if (normalized === "INFERRED") return "border-violet-200 bg-violet-50 text-violet-800";
  return "border-zinc-300 bg-white text-zinc-600";
}

function StatusBadge({ status }: { status: string }) {
  return <span className={`inline-flex whitespace-nowrap rounded-full border px-2 py-1 text-[10px] font-bold tracking-[0.06em] ${statusClass(status)}`}>{status}</span>;
}

function normalizeValue(value: unknown): string {
  const text = String(value ?? "").trim();
  return text && !text.toUpperCase().startsWith("UNKNOWN") ? text : "UNKNOWN";
}

function fallbackFact(field: RequestedField): LiveFacilityFact {
  return {
    parameter_id: field.ids[0], parameter: field.label, value: "UNKNOWN", evidence_status: "UNKNOWN", confidence: "UNKNOWN",
    source_category: "UNKNOWN", source_name: "Not verified", source_url_or_local_file: "database/florida_facility_parameter_evidence.json",
    dataset_name: "UNKNOWN", dataset_field: "UNKNOWN", record_identifier: "CMS-105719", retrieval_date: "", publication_date: "",
    evidence_quote: "No evidence row available for this requested field.", normalized_value: "UNKNOWN", scope: "FACILITY", recency: "UNKNOWN",
    contradictory_sources: "NONE_DETECTED", used_by_decision_engine: "NO", used_in_eligibility: "NO", used_in_ranking: "NO",
    displayed_in_ui: "YES", ACTION: "REQUEST_PRIMARY_EVIDENCE", Priority: "MEDIUM", "Recipient department": "Administration / Compliance",
    "Suggested recipient role": "Facility Administrator", "Required evidence": `Current dated documentation for ${field.label}.`,
    "Suggested question": `Can you verify ${field.label} for CMS CCN 105719 and provide current supporting documentation?`,
    "Request status": "NOT_DRAFTED", "Last request date": "", "Follow-up date": "", "Ranking impact": "Improves profile completeness and may affect patient fit when relevant.",
  };
}

function actionFromFact(fact: LiveFacilityFact): LiveFacilityAction {
  return {
    action_id: `UI-${fact.parameter_id}`, parameter_id: fact.parameter_id, parameter: fact.parameter, current_value: normalizeValue(fact.value),
    evidence_status: fact.evidence_status, action: fact.ACTION || "REQUEST_PRIMARY_EVIDENCE", priority: fact.Priority || "MEDIUM",
    recipient_department: fact["Recipient department"] || "Administration / Compliance",
    suggested_recipient_role: fact["Suggested recipient role"] || "Facility Administrator",
    required_evidence: fact["Required evidence"] || `Current dated documentation for ${fact.parameter}.`,
    suggested_question: fact["Suggested question"] || `Can you verify ${fact.parameter} and provide supporting documentation?`,
    request_status: fact["Request status"] || "NOT_DRAFTED", last_request_date: fact["Last request date"] || "",
    follow_up_date: fact["Follow-up date"] || "", ranking_impact: fact["Ranking impact"] || "May improve evidence coverage.",
  };
}

function FactTable({ fields, facts, onEvidence, onAction }: { fields: RequestedField[]; facts: LiveFacilityFact[]; onEvidence: (fact: LiveFacilityFact) => void; onAction: (fact: LiveFacilityFact) => void }) {
  const rows = fields.map((field) => facts.find((fact) => field.ids.includes(fact.parameter_id)) || fallbackFact(field));
  return (
    <div className="overflow-x-auto border-y border-zinc-200">
      <table className="w-full min-w-[980px] text-left text-sm">
        <thead className="bg-zinc-50 text-[11px] uppercase tracking-[0.08em] text-zinc-500"><tr>
          <th className="px-4 py-3 font-semibold">Parameter</th><th className="px-4 py-3 font-semibold">Current value</th>
          <th className="px-4 py-3 font-semibold">Evidence</th><th className="px-4 py-3 font-semibold">Confidence</th>
          <th className="px-4 py-3 font-semibold">Source</th><th className="px-4 py-3 font-semibold">Last verified</th>
          <th className="px-4 py-3 font-semibold">Ranking impact</th><th className="px-4 py-3 font-semibold">Action</th>
        </tr></thead>
        <tbody className="divide-y divide-zinc-100">
          {rows.map((fact, index) => <tr key={`${fact.parameter_id}-${index}`} className="align-top hover:bg-zinc-50/70">
            <td className="px-4 py-3 font-medium text-zinc-900">{fields[index].label}</td>
            <td className="px-4 py-3"><button onClick={() => onEvidence(fact)} className="text-left font-semibold text-[#116a5b] underline decoration-[#b5d8d1] underline-offset-4">{normalizeValue(fact.value)}</button></td>
            <td className="px-4 py-3"><StatusBadge status={fact.evidence_status} /></td><td className="px-4 py-3 text-zinc-600">{fact.confidence}</td>
            <td className="max-w-44 px-4 py-3 text-zinc-600">{fact.source_name}</td><td className="px-4 py-3 text-zinc-600">{fact.publication_date || fact.retrieval_date || "UNKNOWN"}</td>
            <td className="max-w-64 px-4 py-3 text-xs leading-5 text-zinc-600">{fact["Ranking impact"] || (fact.used_in_ranking === "YES" ? "Used in ranking" : "No direct ranking use proven")}</td>
            <td className="px-4 py-3">{fact.evidence_status !== "VERIFIED" ? <button onClick={() => onAction(fact)} className="rounded-md border border-[#9bc8bf] bg-[#eef8f5] px-3 py-2 text-xs font-semibold text-[#145f52] hover:bg-[#dff2ed]">ACTION</button> : <span className="text-xs text-zinc-400">Current</span>}</td>
          </tr>)}
        </tbody>
      </table>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="min-w-0 border-l border-zinc-200 pl-4 first:border-l-0 first:pl-0"><p className="truncate text-[10px] font-bold uppercase tracking-[0.1em] text-zinc-500">{label}</p><p className="mt-1 text-lg font-semibold text-zinc-900">{value}</p></div>;
}

export function LiveFacilityProfileClient({ cmsCcn }: { cmsCcn: string }) {
  const router = useRouter();
  const [profile, setProfile] = useState<LiveFacilityProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [evidence, setEvidence] = useState<LiveFacilityFact | null>(null);
  const [filters, setFilters] = useState<string[]>([]);
  const [panelOpen, setPanelOpen] = useState(false);
  const [selectedActionIds, setSelectedActionIds] = useState<string[]>([]);
  const [saved, setSaved] = useState(false);
  const [deadline, setDeadline] = useState("");
  const [followUp, setFollowUp] = useState("");

  useEffect(() => {
    let active = true;
    fetchLiveFacilityProfile(cmsCcn).then((payload) => { if (active) setProfile(payload); }).catch((reason: unknown) => {
      if (!active) return;
      if (reason instanceof ApiRequestError && reason.status === 404) {
        router.replace(`/facility/${encodeURIComponent(cmsCcn)}`);
        return;
      }
      setError(reason instanceof Error ? reason.message : "Unable to load facility profile.");
    });
    return () => { active = false; };
  }, [cmsCcn, router]);

  const selectedActions = useMemo(() => profile?.actions.filter((action) => selectedActionIds.includes(action.action_id)) || [], [profile, selectedActionIds]);
  const selectedDepartments = [...new Set(selectedActions.map((action) => action.recipient_department))];
  const emailBody = selectedActions.length ? [
    "Hello,", "", `We are verifying current information for ${profile?.facility.display_name} (CMS CCN ${cmsCcn}). Please respond to the questions below and attach the requested documentation.`, "",
    ...selectedDepartments.flatMap((department) => [department, ...selectedActions.filter((action) => action.recipient_department === department).map((action, index) => `${index + 1}. ${action.suggested_question}`), ""]),
    deadline ? `Requested response date: ${deadline}` : "", "Thank you,", "OPTIME Facility Intelligence",
  ].filter(Boolean).join("\n") : "Select one or more unresolved fields to generate a draft.";

  if (error) return <main className="min-h-screen bg-white px-6 py-20 text-center text-red-700"><h1 className="text-2xl font-semibold">Facility profile unavailable</h1><p className="mt-3">{error}</p></main>;
  if (!profile) return <main className="min-h-screen bg-white px-6 py-20 text-center text-zinc-600">Loading verified facility intelligence...</main>;

  const findFact = (id: string) => profile.facts.find((fact) => fact.parameter_id === id);
  const overallRating = findFact("overall_cms_rating");
  const displayName = profile.facility.display_name;
  const openAction = (fact: LiveFacilityFact) => {
    const existing = profile.actions.find((action) => action.parameter_id === fact.parameter_id);
    if (existing) setSelectedActionIds([existing.action_id]);
    else {
      profile.actions.push(actionFromFact(fact));
      setSelectedActionIds([`UI-${fact.parameter_id}`]);
    }
    setPanelOpen(true);
  };
  const saveDraft = () => {
    const auditRecord = { facility: profile.facility.canonical_facility_id, status: "READY_TO_REVIEW", saved_at: new Date().toISOString(), delivery_status: "NOT_SENT", selected_action_ids: selectedActionIds, recipient_departments: selectedDepartments, deadline, follow_up_date: followUp, subject: "Information Verification Request — The Palace Nursing & Rehabilitation Center", body: emailBody };
    const history = JSON.parse(window.localStorage.getItem("optime-facility-draft-audit") || "[]") as unknown[];
    window.localStorage.setItem("optime-facility-draft-audit", JSON.stringify([...history, auditRecord]));
    setSaved(true);
  };

  return <main className="min-h-screen bg-white text-zinc-950">
    <header className="border-b border-zinc-200 bg-[#fbfdfc]">
      <div className="mx-auto max-w-[1500px] px-5 py-9 lg:px-9 lg:py-12">
        <div className="flex flex-col justify-between gap-7 xl:flex-row xl:items-end">
          <div className="max-w-4xl"><div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-[#e7f4f1] px-3 py-1 text-xs font-bold text-[#145f52]">LIVE FACILITY INTELLIGENCE</span><StatusBadge status="PARTIALLY_VERIFIED" /></div>
            <h1 className="mt-5 text-3xl font-semibold tracking-[-0.03em] text-zinc-950 sm:text-5xl">{displayName}</h1>
            <p className="mt-3 text-base text-zinc-600">{profile.facility.city}, {profile.facility.state} <span className="mx-2 text-zinc-300">|</span> {profile.facility.facility_type} <span className="mx-2 text-zinc-300">|</span> CMS CCN {profile.facility.cms_ccn}</p>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-zinc-500">Identity anchored to the CMS record at {profile.facility.address}. NPI {profile.facility.must_not_merge.npi} is explicitly excluded because it belongs to a different Palace facility.</p>
          </div>
          <div className="flex flex-wrap gap-2"><button onClick={() => setActiveTab("actions")} className="rounded-md border border-zinc-300 bg-white px-4 py-2.5 text-sm font-semibold hover:bg-zinc-50">View Recommendation Impact</button><button onClick={() => setPanelOpen(true)} className="rounded-md bg-[#176b5d] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#10584d]">Complete Missing Information</button><button onClick={() => setActiveTab("evidence")} className="rounded-md border border-zinc-300 bg-white px-4 py-2.5 text-sm font-semibold hover:bg-zinc-50">View All Evidence</button></div>
        </div>
        <div className="mt-9 grid grid-cols-2 gap-x-4 gap-y-5 border-t border-zinc-200 pt-6 sm:grid-cols-4 xl:grid-cols-8">
          <Metric label="CMS rating" value={overallRating ? `${overallRating.value}/5` : "UNKNOWN"} /><Metric label="Confidence" value={profile.summary.evidence_confidence} />
          <Metric label="Completeness" value={`${profile.summary.profile_completeness_percent}%`} /><Metric label="Last updated" value={profile.summary.last_updated} />
          <Metric label="Evidence records" value={profile.summary.evidence_record_count} /><Metric label="Verified facts" value={profile.summary.verified_fact_count} />
          <Metric label="Critical unknowns" value={profile.summary.critical_unknown_count} /><Metric label="Sources" value={profile.summary.source_count} />
        </div>
      </div>
    </header>

    <nav className="sticky top-0 z-30 overflow-x-auto border-b border-zinc-200 bg-white/95 backdrop-blur" aria-label="Facility profile sections"><div className="mx-auto flex max-w-[1500px] px-5 lg:px-9">{TABS.map((tab) => <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`whitespace-nowrap border-b-2 px-3 py-4 text-sm font-medium ${activeTab === tab.id ? "border-[#176b5d] text-[#145f52]" : "border-transparent text-zinc-500 hover:text-zinc-900"}`}>{tab.label}</button>)}</div></nav>

    <div className="mx-auto max-w-[1500px] px-5 py-8 lg:px-9 lg:py-10">
      {activeTab === "overview" && <section><div className="grid gap-8 xl:grid-cols-[1.35fr_0.65fr]"><div><h2 className="text-2xl font-semibold tracking-[-0.02em]">Canonical identity</h2><div className="mt-5 grid border-t border-zinc-200 sm:grid-cols-2">{[
        ["Official name", displayName, "official_name"], ["Legal name", profile.facility.canonical_name, "legal_name"], ["Address", `${profile.facility.address}, ${profile.facility.city}, ${profile.facility.state} ${profile.facility.zip}`, "address"], ["Phone", profile.facility.phone, "phone"],
        ["Website", profile.facility.official_website, "website"], ["CMS CCN", profile.facility.cms_ccn, "cms_ccn"], ["NPI", profile.facility.canonical_npi, "npi"], ["State license", profile.facility.license_number, "state_license"],
        ["Facility type", profile.facility.facility_type, "facility_type"], ["Ownership type", profile.facility.ownership_type, "ownership_type"], ["Ownership organization", "UNKNOWN", "ownership_organization"], ["Chain affiliation", "UNKNOWN", "chain_affiliation"],
        ["Certified beds", profile.facility.beds, "certified_beds"], ["Occupancy", "UNKNOWN", "occupancy"], ["Medicare / Medicaid", profile.facility.medicare_medicaid, "medicare_medicaid"], ["Coordinates", profile.facility.coordinates, "coordinates"],
        ["County", profile.facility.county, "county"], ["Nearby hospital distance", "UNKNOWN", "nearby_hospitals"], ["Aliases", profile.facility.aliases.join("; "), "aliases"],
      ].map(([label, value, id]) => { const fact = profile.identity_evidence.find((item) => item.parameter_id === id) as unknown as LiveFacilityFact | undefined; const safeFact = fact || fallbackFact({ label: String(label), ids: [String(id)] }); return <div key={String(id)} className="border-b border-zinc-200 py-4 sm:pr-6"><p className="text-xs font-semibold uppercase tracking-[0.08em] text-zinc-500">{label}</p><button onClick={() => setEvidence(safeFact)} className="mt-1 text-left text-sm font-semibold text-[#116a5b] underline decoration-[#b5d8d1] underline-offset-4">{normalizeValue(value)}</button>{normalizeValue(value) === "UNKNOWN" && <button onClick={() => openAction(safeFact)} className="ml-3 text-xs font-bold text-[#176b5d]">ACTION</button>}</div>; })}</div></div>
        <aside className="border-l-2 border-[#a8d4ca] bg-[#f5faf8] p-6"><p className="text-xs font-bold uppercase tracking-[0.1em] text-[#176b5d]">What OPTIME knows</p><p className="mt-3 text-sm leading-6 text-zinc-700">CMS identity, provider type, ownership class, bed capacity, staffing signals, inspection results, quality evidence, and selected rehabilitation capabilities.</p><p className="mt-6 text-xs font-bold uppercase tracking-[0.1em] text-zinc-500">What remains unknown</p><p className="mt-3 text-sm leading-6 text-zinc-700">{profile.unknown_sections.join("; ")}.</p><p className="mt-6 text-xs font-bold uppercase tracking-[0.1em] text-zinc-500">Patient fit</p><p className="mt-3 text-sm leading-6 text-zinc-700">Skilled nursing and short-term rehabilitation have evidence. Stroke-specific care, direct nursing modality, ADL support, transfers, dietary needs, language support, current price, and availability require verification before a confident patient-specific decision.</p></aside></div></section>}

      {(["clinical", "rehabilitation", "staffing", "quality", "lifestyle", "pricing"] as TabId[]).includes(activeTab) && <section><div className="mb-6"><h2 className="text-2xl font-semibold tracking-[-0.02em]">{TABS.find((tab) => tab.id === activeTab)?.label}</h2><p className="mt-2 text-sm text-zinc-500">Every value opens its evidence record. Missing evidence remains UNKNOWN.</p></div><FactTable fields={FIELDS[activeTab as keyof typeof FIELDS]} facts={profile.facts} onEvidence={setEvidence} onAction={openAction} /></section>}

      {activeTab === "experience" && <section><h2 className="text-2xl font-semibold tracking-[-0.02em]">Resident experience</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-600">No review content, ratings, review counts, or review summaries are present in the governed facility evidence. OPTIME does not generate a summary without source content.</p><div className="mt-6 overflow-x-auto border-y border-zinc-200"><table className="w-full min-w-[900px] text-left text-sm"><thead className="bg-zinc-50 text-xs uppercase text-zinc-500"><tr>{["Source", "Rating", "Reviews", "Retrieved", "Themes", "Recency", "Reliability", "Connected", "Action"].map((label) => <th key={label} className="px-4 py-3">{label}</th>)}</tr></thead><tbody className="divide-y divide-zinc-100">{REVIEW_SOURCES.map((source) => <tr key={source}><td className="px-4 py-3 font-medium">{source}</td>{["UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", "NO EVIDENCE"].map((value, index) => <td key={index} className="px-4 py-3 text-zinc-500">{value}</td>)}<td className="px-4 py-3"><button onClick={() => openAction(fallbackFact({ label: `${source} resident experience`, ids: [`review_${source.toLowerCase().replaceAll(" ", "_")}`] }))} className="rounded-md border border-[#9bc8bf] px-3 py-2 text-xs font-semibold text-[#145f52]">ACTION</button></td></tr>)}</tbody></table></div></section>}

      {activeTab === "evidence" && <section><div className="flex flex-col justify-between gap-4 sm:flex-row"><div><h2 className="text-2xl font-semibold tracking-[-0.02em]">Complete evidence ledger</h2><p className="mt-2 text-sm text-zinc-500">{profile.facts.length} canonical parameter records from {profile.sources.length} named sources.</p></div><div className="flex flex-wrap gap-2">{STATUS_FILTERS.map((status) => <button key={status} onClick={() => setFilters((current) => current.includes(status) ? current.filter((item) => item !== status) : [...current, status])} className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${filters.includes(status) ? statusClass(status) : "border-zinc-200 bg-white text-zinc-600"}`}>{status.replaceAll("_", " ")}</button>)}</div></div><div className="mt-6 space-y-3">{profile.facts.filter((fact) => !filters.length || filters.includes(fact.evidence_status) || filters.includes(fact.recency)).map((fact) => <article key={fact.parameter_id} className="border border-zinc-200 p-4" id={`evidence-${fact.parameter_id}`}><div className="flex flex-col justify-between gap-3 sm:flex-row"><div><p className="font-semibold">{fact.parameter}</p><p className="mt-1 text-sm text-zinc-600">{normalizeValue(fact.value)}</p></div><div className="flex items-start gap-2"><StatusBadge status={fact.evidence_status} /><StatusBadge status={fact.recency} /></div></div><div className="mt-4 grid gap-3 text-xs leading-5 text-zinc-600 md:grid-cols-3"><p><b>Source:</b> {fact.source_category} / {fact.source_name}<br/><b>Dataset:</b> {fact.dataset_name}<br/><b>Record:</b> {fact.record_identifier || "UNKNOWN"}</p><p><b>Retrieved:</b> {fact.retrieval_date || "UNKNOWN"}<br/><b>Published:</b> {fact.publication_date || "UNKNOWN"}<br/><b>Confidence:</b> {fact.confidence}</p><p><b>Contradictions:</b> {fact.contradictory_sources}<br/><b>Eligibility:</b> {fact.used_in_eligibility}<br/><b>Ranking:</b> {fact.used_in_ranking} / <b>UI:</b> {fact.displayed_in_ui}</p></div><p className="mt-3 border-l-2 border-zinc-200 pl-3 text-xs leading-5 text-zinc-600">{fact.evidence_quote}</p><p className="mt-3 break-all text-xs text-[#116a5b]">{fact.source_url_or_local_file}</p></article>)}</div></section>}

      {activeTab === "actions" && <section><div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><h2 className="text-2xl font-semibold tracking-[-0.02em]">Missing-information actions</h2><p className="mt-2 text-sm text-zinc-500">{profile.actions.length} governed actions. No request is sent without separate human review.</p></div><button onClick={() => setPanelOpen(true)} className="rounded-md bg-[#176b5d] px-4 py-2.5 text-sm font-semibold text-white">Build consolidated request</button></div><div className="mt-6 overflow-x-auto border-y border-zinc-200"><table className="w-full min-w-[1500px] text-left text-xs"><thead className="bg-zinc-50 uppercase tracking-[0.05em] text-zinc-500"><tr>{["Parameter", "Value", "Status", "Why it matters", "Priority", "Action", "Department", "Role", "Evidence requested", "Suggested question", "Request status", "Last request", "Follow-up", "Ranking impact", "Action"].map((label) => <th key={label} className="px-3 py-3">{label}</th>)}</tr></thead><tbody className="divide-y divide-zinc-100">{profile.actions.map((action) => <tr key={action.action_id} className="align-top"><td className="px-3 py-3 font-semibold">{action.parameter}</td><td className="px-3 py-3">{normalizeValue(action.current_value)}</td><td className="px-3 py-3"><StatusBadge status={action.evidence_status} /></td><td className="max-w-52 px-3 py-3">{action.ranking_impact}</td><td className="px-3 py-3 font-semibold">{action.priority}</td><td className="px-3 py-3">{action.action.replaceAll("_", " ")}</td><td className="px-3 py-3">{action.recipient_department}</td><td className="px-3 py-3">{action.suggested_recipient_role}</td><td className="max-w-56 px-3 py-3">{action.required_evidence}</td><td className="max-w-64 px-3 py-3">{action.suggested_question}</td><td className="px-3 py-3">{action.request_status}</td><td className="px-3 py-3">{action.last_request_date || "—"}</td><td className="px-3 py-3">{action.follow_up_date || "—"}</td><td className="max-w-56 px-3 py-3">{action.ranking_impact}</td><td className="px-3 py-3"><button onClick={() => { setSelectedActionIds([action.action_id]); setPanelOpen(true); }} className="rounded-md border border-[#9bc8bf] px-3 py-2 font-semibold text-[#145f52]">Request Information</button></td></tr>)}</tbody></table></div></section>}
    </div>

    {evidence && <div className="fixed inset-0 z-50 flex items-end justify-end bg-black/30" onClick={() => setEvidence(null)}><aside role="dialog" aria-modal="true" aria-label="Evidence record" onClick={(event) => event.stopPropagation()} className="h-full w-full max-w-xl overflow-y-auto bg-white p-6 shadow-2xl sm:p-8"><div className="flex justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-[0.1em] text-[#176b5d]">Evidence record</p><h2 className="mt-2 text-2xl font-semibold">{evidence.parameter}</h2></div><button onClick={() => setEvidence(null)} aria-label="Close evidence" className="h-9 w-9 rounded-full border border-zinc-300 text-sm">X</button></div><div className="mt-6 flex gap-2"><StatusBadge status={evidence.evidence_status} /><StatusBadge status={evidence.recency} /></div><p className="mt-6 text-3xl font-semibold">{normalizeValue(evidence.value)}</p><dl className="mt-8 grid grid-cols-[140px_1fr] gap-x-4 gap-y-4 border-t border-zinc-200 pt-6 text-sm">{[["Confidence", evidence.confidence], ["Source category", evidence.source_category], ["Source name", evidence.source_name], ["Dataset", evidence.dataset_name], ["Record ID", evidence.record_identifier || "UNKNOWN"], ["Retrieval date", evidence.retrieval_date || "UNKNOWN"], ["Publication date", evidence.publication_date || "UNKNOWN"], ["Contradictions", evidence.contradictory_sources], ["Used in eligibility", evidence.used_in_eligibility], ["Used in ranking", evidence.used_in_ranking], ["Displayed in UI", evidence.displayed_in_ui]].map(([label, value]) => <div className="contents" key={label}><dt className="font-medium text-zinc-500">{label}</dt><dd className="break-words text-zinc-800">{value}</dd></div>)}</dl><div className="mt-8 border-l-2 border-[#9bc8bf] bg-[#f5faf8] p-4"><p className="text-xs font-bold uppercase text-zinc-500">Extracted evidence</p><p className="mt-2 text-sm leading-6 text-zinc-700">{evidence.evidence_quote}</p></div><p className="mt-6 break-all text-xs text-[#116a5b]">{evidence.source_url_or_local_file}</p>{evidence.evidence_status !== "VERIFIED" && <button onClick={() => { openAction(evidence); setEvidence(null); }} className="mt-8 w-full rounded-md bg-[#176b5d] px-4 py-3 text-sm font-semibold text-white">Take action on this field</button>}</aside></div>}

    {panelOpen && <div className="fixed inset-0 z-50 bg-black/35 p-3 sm:p-6" onClick={() => setPanelOpen(false)}><div role="dialog" aria-modal="true" aria-label="Complete missing information" onClick={(event) => event.stopPropagation()} className="mx-auto flex h-full max-w-6xl flex-col overflow-hidden bg-white shadow-2xl"><header className="flex items-start justify-between border-b border-zinc-200 p-5 sm:p-7"><div><p className="text-xs font-bold uppercase tracking-[0.1em] text-[#176b5d]">READY_TO_REVIEW</p><h2 className="mt-2 text-2xl font-semibold">Complete missing information</h2><p className="mt-1 text-sm text-zinc-500">Select unresolved fields. This workflow saves drafts only and cannot send email.</p></div><button onClick={() => setPanelOpen(false)} aria-label="Close request panel" className="h-9 w-9 rounded-full border border-zinc-300 text-sm">X</button></header><div className="grid flex-1 overflow-hidden lg:grid-cols-[0.9fr_1.1fr]"><section className="overflow-y-auto border-r border-zinc-200 p-5 sm:p-7"><div className="flex flex-wrap gap-2"><button onClick={() => setSelectedActionIds(profile.actions.filter((action) => action.priority === "CRITICAL").map((action) => action.action_id))} className="rounded-md border border-zinc-300 px-3 py-2 text-xs font-semibold">All critical fields</button><button onClick={() => setSelectedActionIds(profile.actions.map((action) => action.action_id))} className="rounded-md border border-zinc-300 px-3 py-2 text-xs font-semibold">All actionable fields</button><button onClick={() => setSelectedActionIds([])} className="rounded-md border border-zinc-300 px-3 py-2 text-xs font-semibold">Clear</button></div>{[...new Set(profile.actions.map((action) => action.recipient_department))].map((department) => <div key={department} className="mt-6"><div className="flex items-center justify-between"><h3 className="font-semibold">{department}</h3><button onClick={() => { const ids = profile.actions.filter((action) => action.recipient_department === department).map((action) => action.action_id); setSelectedActionIds((current) => [...new Set([...current, ...ids])]); }} className="text-xs font-semibold text-[#176b5d]">Select category</button></div><div className="mt-2 space-y-2">{profile.actions.filter((action) => action.recipient_department === department).map((action) => <label key={action.action_id} className="flex cursor-pointer gap-3 border border-zinc-200 p-3 hover:bg-zinc-50"><input type="checkbox" checked={selectedActionIds.includes(action.action_id)} onChange={() => setSelectedActionIds((current) => current.includes(action.action_id) ? current.filter((id) => id !== action.action_id) : [...current, action.action_id])} className="mt-1 h-4 w-4 accent-[#176b5d]"/><span><span className="block text-sm font-medium">{action.parameter}</span><span className="mt-1 block text-xs text-zinc-500">{action.priority} · {action.suggested_recipient_role}</span></span></label>)}</div></div>)}</section><section className="overflow-y-auto bg-[#fafbfa] p-5 sm:p-7"><div className="grid gap-4 sm:grid-cols-2"><label className="text-xs font-semibold text-zinc-600">Recipient<input readOnly value={selectedDepartments.join("; ") || "Select fields to determine recipients"} className="mt-2 w-full border border-zinc-300 bg-white px-3 py-2.5 text-sm font-normal"/></label><label className="text-xs font-semibold text-zinc-600">Subject<input readOnly value="Information Verification Request — The Palace Nursing & Rehabilitation Center" className="mt-2 w-full border border-zinc-300 bg-white px-3 py-2.5 text-sm font-normal"/></label><label className="text-xs font-semibold text-zinc-600">Response deadline<input type="date" value={deadline} onChange={(event) => setDeadline(event.target.value)} className="mt-2 w-full border border-zinc-300 bg-white px-3 py-2.5 text-sm font-normal"/></label><label className="text-xs font-semibold text-zinc-600">Follow-up date<input type="date" value={followUp} onChange={(event) => setFollowUp(event.target.value)} className="mt-2 w-full border border-zinc-300 bg-white px-3 py-2.5 text-sm font-normal"/></label></div><div className="mt-5"><p className="text-xs font-semibold text-zinc-600">Selected questions ({selectedActions.length})</p><div className="mt-2 max-h-40 overflow-y-auto border border-zinc-200 bg-white p-3 text-xs leading-5 text-zinc-700">{selectedActions.length ? selectedActions.map((action) => <p key={action.action_id} className="mb-2">{action.suggested_question}</p>) : "No questions selected."}</div></div><div className="mt-5"><p className="text-xs font-semibold text-zinc-600">Requested documents</p><p className="mt-2 border border-zinc-200 bg-white p-3 text-xs leading-5 text-zinc-700">{selectedActions.length ? [...new Set(selectedActions.map((action) => action.required_evidence))].join("; ") : "No documents selected."}</p></div><div className="mt-5"><p className="text-xs font-semibold text-zinc-600">Preview</p><pre className="mt-2 whitespace-pre-wrap border border-zinc-200 bg-white p-4 font-sans text-xs leading-6 text-zinc-700">{emailBody}</pre></div><div className="mt-5 flex items-center justify-between gap-4"><p className="text-xs text-zinc-500">Delivery: NOT_SENT · Automatic sending disabled</p><button disabled={!selectedActions.length} onClick={saveDraft} className="rounded-md bg-[#176b5d] px-5 py-2.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-zinc-300">Save Draft</button></div>{saved && <p className="mt-3 border border-emerald-200 bg-emerald-50 p-3 text-sm font-medium text-emerald-800">Draft saved to this browser’s audit history. No email was sent.</p>}</section></div></div></div>}
  </main>;
}