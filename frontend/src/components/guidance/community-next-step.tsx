"use client";

import { useState } from "react";
import { useQuestionnaire } from "@/context/questionnaire-context";
import { createClientCase } from "@/lib/api";
import { serviceQuoteQuestions } from "@/lib/service-budget";

export function WelcomeOffer() {
  return <div className="mt-5 rounded-2xl bg-[#f6edf4] p-5 text-lg leading-8"><p className="font-semibold">A little help with your next chapter</p><p>OOmnik offers eligible clients a Welcome package of services valued at $500 to help with the move.</p><details className="mt-2"><summary className="cursor-pointer underline underline-offset-4">Welcome eligibility and costs</summary><p className="mt-2">For an eligible first placement, the community funds the package. For subsequent placements, the community and client each contribute $250. Government-funded placements are excluded. The services available and your eligibility must be confirmed before you commit. This is a service package, not a cash payment.</p></details></div>;
}

export function CommunityNextStep({ facilityId, facilityName, serviceNeeds = [] }: { facilityId: string; facilityName: string; serviceNeeds?: string[] }) {
  const { state } = useQuestionnaire();
  const [intent, setIntent] = useState<"visit" | "pricing" | null>(null);
  const [contact, setContact] = useState({ name: "", email: "", phone: "", date: "", note: "", consent: false });
  const [status, setStatus] = useState<"idle" | "saving" | "sent">("idle");
  const [error, setError] = useState("");
  async function submit() {
    if (!intent || !contact.consent || (!contact.email.trim() && !contact.phone.trim()) || status === "saving") return;
    setStatus("saving"); setError("");
    try {
      const token = window.localStorage.getItem("oomnik.client.case.token") || (await createClientCase({ questionnaire_state: state as unknown as Record<string, unknown>, contact_name: contact.name.trim(), email: contact.email.trim() || undefined, phone: contact.phone.trim() || undefined, terms_accepted: true })).case_token;
      window.localStorage.setItem("oomnik.client.case.token", token);
      const response = await fetch(`/api/backend/api/client-cases/${encodeURIComponent(token)}/events`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ event_type: intent === "visit" ? "VISIT_REQUESTED" : "ROOM_PRICING_REQUESTED", facility_id: facilityId, status: "AWAITING_CONFIRMATION", note: contact.note.trim(), payload: { facility_name: facilityName, preferred_date: intent === "visit" ? contact.date || null : null, contact_name: contact.name.trim(), email: contact.email.trim(), phone: contact.phone.trim(), contact_consent: true, monthly_family_budget: state.budget > 0 ? state.budget : null, residents: state.relationship === "Couple" ? 2 : 1, required_services: serviceNeeds, quote_questions: serviceQuoteQuestions } }) });
      if (!response.ok) throw new Error("We could not save your request. Please try again.");
      setStatus("sent");
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to save your request."); setStatus("idle"); }
  }
  return <section className="mt-8 border-t border-[#e4d8e8] pt-7">
    <h3 className="text-2xl font-semibold">How does this place feel to you?</h3>
    <p className="mt-3 text-lg leading-8">If {facilityName} feels promising, a visit can help you picture daily life there and meet the people who would be part of it. We can also start with the service plan and full cost. What would help you feel ready?</p>
    {status === "sent" ? <p role="status" className="mt-4 text-lg font-semibold">Your {intent === "visit" ? "visit" : "room and pricing"} request is saved in your OOmnik case, pending follow-up. {intent === "visit" ? "Your visit is not booked yet; the community must confirm a date." : "Current room types, care costs and availability still require the community’s reply."}</p> : <>
      <div className="mt-4 flex flex-col gap-3 sm:items-start"><button type="button" onClick={() => setIntent("visit")} className="rounded-full bg-[#675088] px-6 py-4 text-lg font-semibold text-white">Arrange a visit</button><button type="button" onClick={() => setIntent("pricing")} className="rounded-full border border-[#675088] px-6 py-3 text-lg text-[#675088]">Check services and total cost within my budget</button></div>
      {intent ? <form onSubmit={event => { event.preventDefault(); void submit(); }} className="mt-5 space-y-4 text-lg">
        <h4 className="text-xl font-semibold">{intent === "visit" ? "Request a visit" : "Request a complete service and price plan"}</h4>
        {intent === "pricing" ? <div className="rounded-xl bg-white p-4"><p className="font-semibold">The request includes your {state.budget > 0 ? `$${state.budget.toLocaleString()} monthly` : "unconfirmed"} family budget{state.relationship === "Couple" ? " for both residents" : ""}.</p><details className="mt-3"><summary className="cursor-pointer underline">What the written quote will cover</summary><p className="mt-3 leading-8">{serviceQuoteQuestions.join(" ")}</p></details></div> : null}
        {intent === "visit" ? <><p className="leading-8">A live appointment calendar is not connected. Choose your preferred date; the visit will require confirmation.</p><label className="block">Preferred date<input type="date" min={new Date().toLocaleDateString("en-CA")} value={contact.date} onChange={e => setContact(v => ({ ...v, date: e.target.value }))} className="mt-2 block w-full rounded-xl border bg-white p-3" /></label></> : <p className="leading-8">Ask for a current quote covering the room and care services you need.</p>}
        <label className="block">Name<input value={contact.name} onChange={e => setContact(v => ({ ...v, name: e.target.value }))} autoComplete="name" className="mt-2 block w-full rounded-xl border p-3" /></label>
        <label className="block">Email<input type="email" value={contact.email} onChange={e => setContact(v => ({ ...v, email: e.target.value }))} autoComplete="email" className="mt-2 block w-full rounded-xl border p-3" /></label>
        <label className="block">Phone<input type="tel" value={contact.phone} onChange={e => setContact(v => ({ ...v, phone: e.target.value }))} autoComplete="tel" className="mt-2 block w-full rounded-xl border p-3" /></label>
        <label className="block">Anything we should know?<textarea value={contact.note} onChange={e => setContact(v => ({ ...v, note: e.target.value }))} rows={3} className="mt-2 block w-full rounded-xl border p-3" /></label>
        <label className="flex items-start gap-3"><input type="checkbox" checked={contact.consent} onChange={e => setContact(v => ({ ...v, consent: e.target.checked }))} className="mt-1 size-5 shrink-0" /><span>I agree to the Terms of Use and allow OOmnik to save this request and contact me about it.</span></label>
        <p className="text-base">Provide an email address or phone number so we can follow up.</p>
        {error ? <p role="alert" className="text-[#943b28]">{error}</p> : null}
        <button disabled={status === "saving" || !contact.consent || (!contact.email.trim() && !contact.phone.trim())} className="rounded-full bg-[#675088] px-6 py-4 font-semibold text-white disabled:opacity-40">{status === "saving" ? "Saving…" : "Save my request"}</button>
      </form> : null}
    </>}
    {intent ? <WelcomeOffer /> : null}
  </section>;
}
