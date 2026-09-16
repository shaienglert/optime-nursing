"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import {
  FacilitySalesCopilotAnswer,
  FacilitySalesCopilotBootstrap,
  FacilityRecord,
  FacilityRecordSearchResult,
  addFacilityRecordDocument,
  addFacilityRecordEvent,
  askFacilitySalesCopilot,
  fetchFacilityRecord,
  fetchFacilitySalesCopilotBootstrap,
  searchFacilityRecords,
} from "@/lib/api";
import { OptimeStaticLogo } from "@/components/brand/optime-static-logo";

const TOKEN_KEY = "oomnik.sales-desk.token";

const CORE_PLAYBOOK = [
  {
    number: "Opening",
    title: "The purpose of every facility conversation",
    summary: "You are introducing Oomnik as the next generation of senior-living decision support: a platform built to help families understand their needs, compare relevant options, and make a successful match with the right community.",
    points: [
      "Opening script: “Hello, this is [NAME] calling from Oomnik. We recently sent an introduction to our Las Vegas Valley senior-living decision and matching service. Did I reach the person responsible for partnerships, admissions, or community marketing?”",
      "If yes: “Thank you. Oomnik helps families clarify their needs and understand which communities may genuinely fit. We are building current, evidence-based facility profiles for Las Vegas Valley, and I would like to explain the launch program and confirm the best next step for your community.”",
      "Lead with the future Oomnik is building, then connect that future to the facility's commercial reality.",
      "The objective is a next step: agreement review, guided profile session, or a scheduled conversation with the decision-maker.",
      "Use the word match deliberately. A lead, listing, or move-in is one step; a sustainable match is the product.",
    ],
  },
  {
    number: "1",
    title: "Your role",
    summary: "Follow Oomnik's introductory outreach, reach the right facility decision-maker, explain the program accurately, answer commercial questions with confidence, and secure the appropriate onboarding step.",
    points: [
      "Ask who owns referral partnerships, admissions, community marketing, and profile information.",
      "Represent the commercial vision while routing clinical, legal, privacy, security, and custom-contract details through the approved follow-up path.",
      "Record the caller's exact question and every agreed action in the facility record.",
    ],
  },
  {
    number: "3",
    title: "The 30-second explanation",
    summary: "Oomnik helps a family define care needs, budget, location, timing, and preferences, then compares relevant communities using current evidence. The result is an explained match: the right community for the resident and a more suitable resident for the community.",
    points: [
      "Complete, current, verified information helps genuine strengths be recognized for the right case.",
      "Missing information remains UNKNOWN; relevant proven information can support a stronger explained match.",
      "Commercial terms and matching decisions stay separate, preserving the credibility of every recommendation.",
    ],
  },
  {
    number: "5",
    title: "Persuasive sales tools",
    summary: "Use one strong idea at a time, tied to the concern the caller just raised. The goal is a conversation, not a speech.",
    points: [
      "Booking.com analogy: hospitality changed when customers could compare options clearly online. Senior living is moving in the same direction, with Oomnik focused on match rather than a simple listing.",
      "Digital matching analogy: technology already helps people make highly personal choices. Oomnik applies that shift to senior living with stronger evidence, transparency, and safeguards.",
      "Aligned incentive: Oomnik earns the standard fee only after 60 days because the commercial objective is a sustained outcome.",
      "Why participate now: early participants can document their real strengths before digital decision support becomes the normal family expectation.",
      "Why fill the profile: Oomnik can recognize only the advantages supported by current, relevant information. Proven information is stronger than UNKNOWN for that specific need.",
    ],
  },
];

const COMPETITORS = [
  {
    name: "A Place for Mom",
    model: "Large national referral marketplace",
    strength: "High consumer awareness and a large advisor network",
  },
  {
    name: "Caring.com",
    model: "Directory, reviews and referral advisors",
    strength: "Broad online discovery and consumer content",
  },
  {
    name: "Seniorly",
    model: "Marketplace with technology-assisted search",
    strength: "Digital experience, pricing context and local advisor support",
  },
  {
    name: "Local placement agencies",
    model: "Relationship-led human referral",
    strength: "Local knowledge and hands-on guidance",
  },
  {
    name: "Direct facility search",
    model: "Families contact communities themselves",
    strength: "Direct contact, but fragmented comparison",
  },
];

const DIFFERENCES = [
  [
    "Primary goal",
    "Find the right match for the person's actual needs",
    "Generate or capture a referral",
  ],
  [
    "Ranking",
    "Commercial payment never buys position",
    "Commercial models may vary by provider",
  ],
  [
    "Facility information",
    "Complete, current, case-relevant information creates more matching opportunities",
    "Often directory-level or advisor-collected information",
  ],
  [
    "Unknown information",
    "Shown as unknown; it is not invented and is not automatically negative",
    "Treatment of missing information varies",
  ],
  [
    "Explanation",
    "Shows why a community fits, where gaps remain and what must be verified",
    "Often presents a list, profile or advisor recommendation",
  ],
  [
    "Commercial alignment",
    "Standard fee is earned only after 60 days",
    "Many referral fees are triggered at move-in",
  ],
  [
    "Welcome Package",
    "$500 of eligible services for qualifying private-pay placements at participating communities",
    "Not a standard market feature",
  ],
];

export default function FacilitySalesCopilotPage() {
  const [token, setToken] = useState("");
  const [tokenInput, setTokenInput] = useState("");
  const [question, setQuestion] = useState("");
  const [facilityName, setFacilityName] = useState("");
  const [facilityResults, setFacilityResults] = useState<
    FacilityRecordSearchResult[]
  >([]);
  const [selectedFacilityId, setSelectedFacilityId] = useState("");
  const [facilityRecord, setFacilityRecord] = useState<FacilityRecord | null>(
    null,
  );
  const [eventSummary, setEventSummary] = useState("");
  const [eventType, setEventType] = useState("CALL");
  const [contactName, setContactName] = useState("");
  const [documentTitle, setDocumentTitle] = useState("");
  const [documentType, setDocumentType] = useState("CONTRACT");
  const [documentUrl, setDocumentUrl] = useState("");
  const [callStage, setCallStage] = useState("FOLLOW_UP_AFTER_EMAIL");
  const [bootstrap, setBootstrap] =
    useState<FacilitySalesCopilotBootstrap | null>(null);
  const [answer, setAnswer] = useState<FacilitySalesCopilotAnswer | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.resolve().then(() => {
      try {
        const saved = window.sessionStorage.getItem(TOKEN_KEY) || "";
        setToken(saved);
        setTokenInput(saved);
      } catch {
        // The representative may enter the dedicated Sales Desk code.
      }
    });
  }, []);

  useEffect(() => {
    if (!token) return;
    let active = true;
    fetchFacilitySalesCopilotBootstrap(token)
      .then((value) => {
        if (active) {
          setBootstrap(value);
          setError(null);
        }
      })
      .catch(
        (err) =>
          active &&
          setError(
            err instanceof Error
              ? err.message
              : "Unable to unlock the copilot.",
          ),
      );
    return () => {
      active = false;
    };
  }, [token]);

  useEffect(() => {
    if (!token || facilityName.trim().length < 2 || selectedFacilityId) return;
    const timer = window.setTimeout(() => {
      searchFacilityRecords(facilityName.trim(), token)
        .then(setFacilityResults)
        .catch(() => setFacilityResults([]));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [facilityName, selectedFacilityId, token]);

  useEffect(() => {
    if (!token || !selectedFacilityId) return;
    fetchFacilityRecord(selectedFacilityId, token)
      .then(setFacilityRecord)
      .catch((err) =>
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load facility record.",
        ),
      );
  }, [selectedFacilityId, token]);

  function unlock() {
    const value = tokenInput.trim();
    if (!value) return;
    try {
      window.sessionStorage.setItem(TOKEN_KEY, value);
    } catch {}
    setToken(value);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setAnswer(
        await askFacilitySalesCopilot(
          {
            question: question.trim(),
            canonical_facility_id: selectedFacilityId || undefined,
            facility_name: facilityName.trim() || undefined,
            call_stage: callStage,
          },
          token,
        ),
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "The copilot could not answer.",
      );
    } finally {
      setLoading(false);
    }
  }

  function selectFacility(facility: FacilityRecordSearchResult) {
    setSelectedFacilityId(facility.canonical_facility_id);
    setFacilityName(facility.facility_name);
    setFacilityResults([]);
  }

  async function saveEvent() {
    if (!selectedFacilityId || !eventSummary.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setFacilityRecord(
        await addFacilityRecordEvent(
          selectedFacilityId,
          {
            event_type: eventType,
            channel:
              eventType === "EMAIL"
                ? "EMAIL"
                : eventType === "WEBSITE"
                  ? "WEBSITE"
                  : "PHONE",
            direction: eventType === "NOTE" ? "INTERNAL" : "OUTBOUND",
            summary: eventSummary.trim(),
            contact_name: contactName.trim() || undefined,
          },
          token,
        ),
      );
      setEventSummary("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save activity.");
    } finally {
      setLoading(false);
    }
  }

  async function saveDocument() {
    if (!selectedFacilityId || !documentTitle.trim() || !documentUrl.trim())
      return;
    setLoading(true);
    setError(null);
    try {
      setFacilityRecord(
        await addFacilityRecordDocument(
          selectedFacilityId,
          {
            title: documentTitle.trim(),
            document_type: documentType,
            document_url: documentUrl.trim(),
          },
          token,
        ),
      );
      setDocumentTitle("");
      setDocumentUrl("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save document.");
    } finally {
      setLoading(false);
    }
  }

  if (!token || !bootstrap) {
    return (
      <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,#dff7ed_0,#f7fbf9_38%,#e7eef8_100%)] px-6 py-14 text-[#0b2850]">
        <section className="mx-auto max-w-md space-y-5 rounded-[2rem] border border-white/80 bg-white/85 p-8 shadow-[0_30px_90px_rgba(11,40,80,.18)] backdrop-blur-xl">
          <div className="scale-[1.55] origin-left">
            <OptimeStaticLogo href="/partner-desk" />
          </div>
          <p className="pt-4 text-xs font-bold uppercase tracking-[0.24em] text-emerald-700">
            Partner desk · Staff only
          </p>
          <h1 className="text-3xl font-black tracking-tight">
            Your live facility sales command center.
          </h1>
          <p className="text-sm leading-6 text-slate-600">
            Approved answers, commercial terms, market evidence, and objection
            handling—built for the team introducing the next generation of
            senior-living matching.
          </p>
          <label className="block text-sm font-semibold text-slate-700">
            Sales Desk access code
            <input
              type="password"
              autoComplete="current-password"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && unlock()}
              placeholder="Sales access code"
              className="mt-2 w-full rounded-xl border border-[#d8e7e1] bg-white px-4 py-3 text-[#0b2850]"
            />
          </label>
          <button
            type="button"
            onClick={unlock}
            className="w-full rounded-xl bg-[#0b2850] px-4 py-3 font-semibold text-white shadow-lg hover:bg-[#123b70]"
          >
            Enter Partner Desk
          </button>
          {error ? <p className="text-sm text-rose-300">{error}</p> : null}
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,#dff7ed_0,#ffffff_42%,#eef4fb_100%)] px-5 py-8 text-lg text-[#173f35] sm:px-10 [&_.text-sm]:text-lg [&_.text-xs]:text-base">
      <section className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="order-1 overflow-hidden rounded-[2rem] border border-[#d8e7e1] bg-white/95 p-7 shadow-[0_24px_70px_rgba(11,40,80,.10)] backdrop-blur-xl sm:p-10">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <div className="inline-block rounded-2xl bg-white px-5 py-3 shadow-xl">
                <div className="scale-[1.45] origin-left pr-24">
                  <OptimeStaticLogo href="/partner-desk" />
                </div>
              </div>
              <p className="mt-8 text-xs font-bold uppercase tracking-[0.25em] text-emerald-700">
                Oomnik Partner Desk · Las Vegas
              </p>
              <h1 className="mt-3 max-w-4xl text-4xl font-black leading-tight tracking-[-0.04em] sm:text-6xl">
                Build the matching platform every community will want to join.
              </h1>
              <p className="mt-4 max-w-3xl text-lg text-[#48645b]">
                Finding You the Right Way. Give every facility conversation the
                confidence, evidence, and polish of a category-defining company.
              </p>
            </div>
            <Link
              href="/"
              className="rounded-full border border-[#c9ded6] bg-white px-5 py-2 text-sm text-[#0b2850] hover:bg-[#eef7f3]"
            >
              Oomnik Home
            </Link>
          </div>
        </header>

        <section className="order-2 rounded-[2rem] border border-emerald-400/30 bg-emerald-400/[.08] p-7 sm:p-10">
          <p className="font-bold uppercase tracking-[0.2em] text-emerald-700">
            Facility outreach playbook · Read this first
          </p>
          <h2 className="mt-3 text-4xl font-black tracking-tight sm:text-5xl">
            Understand the story before using the answer engine.
          </h2>
          <div className="mt-6 rounded-3xl border-2 border-amber-400/70 bg-amber-400/10 p-6">
            <p className="font-black uppercase tracking-[.18em] text-amber-700">Non-negotiable language rule</p>
            <p className="mt-3 text-2xl font-black text-[#0b2850]">Keep every customer-facing answer affirmative and moving forward.</p>
            <p className="mt-3 text-xl leading-8 text-amber-950">Never say “no,” “not,” “can’t,” “I don’t know,” “I’m unfamiliar,” “the system isn’t built for that,” “I need to check,” “let me verify,” “I’ll come back to you,” or any equivalent refusal or delay. State what Oomnik can confirm, explain the positive commercial direction, and give the next action.</p>
            <p className="mt-4 rounded-2xl bg-[#f7fbf9] p-4 text-xl text-[#0b2850]"><span className="font-bold text-emerald-700">Use instead:</span> “That is an important point. What I can confirm today is… The best next step is…”</p>
          </div>
          <div className="mt-7 grid gap-5 lg:grid-cols-2">
            {CORE_PLAYBOOK.map((section) => (
              <article key={section.number} className="rounded-3xl border border-[#d8e7e1] bg-white p-6">
                <p className="font-bold uppercase tracking-[.18em] text-emerald-700">{section.number === "Opening" ? section.number : `Section ${section.number}`}</p>
                <h3 className="mt-2 text-3xl font-black">{section.title}</h3>
                <p className="mt-3 text-xl leading-8 text-[#274a40]">{section.summary}</p>
                <ul className="mt-4 space-y-3 text-lg leading-7 text-[#48645b]">
                  {section.points.map((point) => <li key={point} className="rounded-xl bg-[#f7fbf9] p-3">{point}</li>)}
                </ul>
              </article>
            ))}
          </div>
        </section>

        <section className="order-2 rounded-[2rem] border border-emerald-300/25 bg-gradient-to-br from-emerald-400/15 via-white/[.07] to-sky-400/10 p-7 sm:p-10">
          <p className="font-bold uppercase tracking-[0.2em] text-emerald-700">
            Start here · The Oomnik story
          </p>
          <h2 className="mt-3 max-w-5xl text-4xl font-black leading-tight tracking-[-0.03em] sm:text-5xl">
            Senior living has plenty of listings. Families need a better
            decision.
          </h2>
          <div className="mt-6 grid gap-6 text-xl leading-9 text-[#274a40] lg:grid-cols-2">
            <p>
              Oomnik is building the decision and matching platform for senior
              living. We turn a family's needs, priorities, budget and risks
              into a clear, explainable comparison of relevant communities.
            </p>
            <p>
              Our interest is a successful match—not the fastest referral and
              not the highest-paying facility. That is why payment cannot
              influence ranking, and why our standard fee is earned only after
              the resident has remained for 60 days.
            </p>
          </div>
          <p className="mt-6 rounded-2xl border border-[#d8e7e1] bg-white p-5 text-2xl font-bold text-[#0b2850]">
            The more complete and current a community's information is, the
            better Oomnik can identify the right person for it. Missing
            information is never invented—but the engine cannot match on facts
            it does not know.
          </p>
        </section>

        <section className="order-3 rounded-[2rem] border border-[#d8e7e1] bg-white p-7 sm:p-10">
          <p className="font-bold uppercase tracking-[0.2em] text-sky-700">
            Know the market
          </p>
          <h2 className="mt-2 text-4xl font-black">
            What facilities already encounter
          </h2>
          <p className="mt-4 max-w-5xl text-xl leading-8 text-[#48645b]">
            The representative should never dismiss competitors. Each model
            solves part of the problem. The commercial conversation is about the
            meaningful difference Oomnik adds: explainable, information-led
            matching with protected objectivity.
          </p>
          <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {COMPETITORS.map((competitor) => (
              <article
                key={competitor.name}
                className="rounded-2xl border border-[#d8e7e1] bg-white p-5"
              >
                <h3 className="text-2xl font-bold text-[#0b2850]">
                  {competitor.name}
                </h3>
                <p className="mt-2 font-semibold text-sky-700">
                  {competitor.model}
                </p>
                <p className="mt-3 leading-7 text-[#48645b]">
                  {competitor.strength}
                </p>
              </article>
            ))}
          </div>
        </section>

        <section className="order-4 rounded-[2rem] border border-violet-400/25 bg-violet-50 p-7 sm:p-10">
          <p className="font-bold uppercase tracking-[0.2em] text-violet-700">
            The Oomnik difference
          </p>
          <h2 className="mt-2 text-4xl font-black">
            The points that matter in a sales conversation
          </h2>
          <div className="mt-6 overflow-x-auto rounded-2xl border border-[#d8e7e1]">
            <table className="w-full min-w-[800px] text-left text-lg">
              <thead className="bg-[#eef7f3]">
                <tr>
                  <th className="p-4">Topic</th>
                  <th className="p-4 text-emerald-700">Oomnik</th>
                  <th className="p-4 text-[#48645b]">Common market approach</th>
                </tr>
              </thead>
              <tbody>
                {DIFFERENCES.map(([topic, oomnik, market]) => (
                  <tr key={topic} className="border-t border-[#d8e7e1]">
                    <th className="p-4 align-top text-[#0b2850]">{topic}</th>
                    <td className="p-4 align-top leading-7 text-[#173f35]">
                      {oomnik}
                    </td>
                    <td className="p-4 align-top leading-7 text-[#48645b]">
                      {market}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="order-5 grid gap-4 md:grid-cols-3">
          <article className="rounded-3xl border border-emerald-400/30 bg-emerald-400/10 p-6">
            <p className="text-xs font-bold uppercase tracking-[.18em] text-emerald-700">
              Founding offer
            </p>
            <p className="mt-3 text-3xl font-black">$0 Oomnik fee</p>
            <p className="mt-2 text-sm text-[#48645b]">
              First placement for qualifying communities onboarding in the
              90-day launch window. Facility funds the $500 Welcome Package.
            </p>
          </article>
          <article className="rounded-3xl border border-sky-400/30 bg-sky-400/10 p-6">
            <p className="text-xs font-bold uppercase tracking-[.18em] text-sky-700">
              Standard placement
            </p>
            <p className="mt-3 text-3xl font-black">$1,999 after 60 days</p>
            <p className="mt-2 text-sm text-[#48645b]">
              Outcome-aligned fee. From placement two onward, the Welcome
              Package is split $250 facility / $250 Oomnik.
            </p>
          </article>
          <article className="rounded-3xl border border-violet-400/30 bg-violet-400/10 p-6">
            <p className="text-xs font-bold uppercase tracking-[.18em] text-violet-700">
              Participating · Private pay only
            </p>
            <p className="mt-3 text-3xl font-black">$500 Welcome Package</p>
            <p className="mt-2 text-sm text-[#48645b]">
              Requires a registered participating facility and an eligible
              private-pay placement. Not available for Medicare, Medicaid, VA,
              or other government-funded placements.
            </p>
          </article>
        </section>

        <section className="order-8 rounded-3xl border border-sky-300/70 bg-sky-50 p-6 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-700">
            How to use the Oomnik engine
          </p>
          <h2 className="mt-2 text-xl font-semibold">
            Write the caller's question exactly as it was asked
          </h2>
          <ol className="mt-4 grid gap-2 text-sm text-[#274a40] sm:grid-cols-2">
            {bootstrap.how_to_use.map((step, index) => (
              <li key={step} className="rounded-xl bg-[#f7fbf9] p-3">
                <span className="mr-2 font-semibold text-sky-700">
                  {index + 1}.
                </span>
                {step}
              </li>
            ))}
          </ol>
          <p className="mt-4 rounded-xl border border-amber-300/50 bg-amber-50 p-3 text-sm text-amber-900">
            Example: “The facility says it has no employee available to maintain
            its profile. What should I offer?”
          </p>
        </section>

        {facilityRecord ? (
          <section className="order-10 rounded-3xl border border-emerald-500/30 bg-white p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[.2em] text-emerald-700">
                  Facility Record
                </p>
                <h2 className="mt-2 text-3xl font-black">
                  {facilityRecord.facility.name}
                </h2>
                <p className="mt-1 text-sm text-[#48645b]">
                  {[
                    facilityRecord.facility.address,
                    facilityRecord.facility.city,
                    facilityRecord.facility.state,
                  ]
                    .filter(Boolean)
                    .join(", ")}
                </p>
              </div>
              <div className="flex gap-2 text-sm">
                <span className="rounded-full bg-sky-100 px-4 py-2 text-sky-800">
                  {facilityRecord.counts.timeline_events} activities
                </span>
                <span className="rounded-full bg-violet-100 px-4 py-2 text-violet-800">
                  {facilityRecord.counts.documents} documents
                </span>
              </div>
            </div>
            <div className="mt-6 grid gap-5 lg:grid-cols-2">
              <div className="rounded-2xl border border-[#d8e7e1] bg-[#f7fbf9] p-5">
                <h3 className="font-semibold">Record a call, email or note</h3>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <select
                    value={eventType}
                    onChange={(e) => setEventType(e.target.value)}
                    className="rounded-xl border border-[#d8e7e1] bg-white px-3 py-2"
                  >
                    <option>CALL</option>
                    <option>EMAIL</option>
                    <option>WEBSITE</option>
                    <option>MEETING</option>
                    <option>NOTE</option>
                  </select>
                  <input
                    value={contactName}
                    onChange={(e) => setContactName(e.target.value)}
                    placeholder="Facility contact"
                    className="rounded-xl border border-[#d8e7e1] bg-white px-3 py-2"
                  />
                </div>
                <textarea
                  value={eventSummary}
                  onChange={(e) => setEventSummary(e.target.value)}
                  rows={3}
                  placeholder="What happened, what was agreed, and the next step"
                  className="mt-3 w-full rounded-xl border border-[#d8e7e1] bg-white px-3 py-2"
                />
                <button
                  type="button"
                  onClick={saveEvent}
                  disabled={loading || !eventSummary.trim()}
                  className="mt-3 rounded-full bg-[#0b6b57] px-5 py-2 font-semibold text-white disabled:opacity-50"
                >
                  Save activity
                </button>
              </div>
              <div className="rounded-2xl border border-[#d8e7e1] bg-[#f7fbf9] p-5">
                <h3 className="font-semibold">Attach a document</h3>
                <p className="mt-1 text-xs text-[#647c73]">
                  Add a secure Drive, Dropbox or document-system link. File
                  upload will follow encrypted storage.
                </p>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <select
                    value={documentType}
                    onChange={(e) => setDocumentType(e.target.value)}
                    className="rounded-xl border border-[#d8e7e1] bg-white px-3 py-2"
                  >
                    <option>CONTRACT</option>
                    <option>ADDENDUM</option>
                    <option>LICENSE</option>
                    <option>CORRESPONDENCE</option>
                    <option>PRICING</option>
                    <option>INSURANCE</option>
                    <option>OTHER</option>
                  </select>
                  <input
                    value={documentTitle}
                    onChange={(e) => setDocumentTitle(e.target.value)}
                    placeholder="Document title"
                    className="rounded-xl border border-[#d8e7e1] bg-white px-3 py-2"
                  />
                </div>
                <input
                  value={documentUrl}
                  onChange={(e) => setDocumentUrl(e.target.value)}
                  placeholder="https:// secure document link"
                  className="mt-3 w-full rounded-xl border border-[#d8e7e1] bg-white px-3 py-2"
                />
                <button
                  type="button"
                  onClick={saveDocument}
                  disabled={
                    loading || !documentTitle.trim() || !documentUrl.trim()
                  }
                  className="mt-3 rounded-full bg-[#0b2850] px-5 py-2 font-semibold text-white disabled:opacity-50"
                >
                  Attach to record
                </button>
              </div>
            </div>
            <div className="mt-5 grid gap-5 lg:grid-cols-2">
              <div>
                <h3 className="font-semibold">Complete history</h3>
                <div className="mt-3 max-h-80 space-y-3 overflow-y-auto">
                  {facilityRecord.timeline.length ? (
                    facilityRecord.timeline.map((item) => (
                      <article
                        key={item.id}
                        className="rounded-xl border border-[#d8e7e1] bg-[#f7fbf9] p-4"
                      >
                        <div className="flex justify-between gap-3 text-xs text-[#647c73]">
                          <span>
                            {item.event_type} · {item.direction}
                          </span>
                          <time>
                            {new Date(item.occurred_at).toLocaleString()}
                          </time>
                        </div>
                        {item.subject ? (
                          <p className="mt-2 font-semibold">{item.subject}</p>
                        ) : null}
                        <p className="mt-1 whitespace-pre-wrap text-sm text-[#274a40]">
                          {item.summary}
                        </p>
                        {item.contact_name ? (
                          <p className="mt-2 text-xs text-sky-700">
                            Contact: {item.contact_name}
                          </p>
                        ) : null}
                      </article>
                    ))
                  ) : (
                    <p className="text-sm text-[#647c73]">
                      No activity recorded yet.
                    </p>
                  )}
                </div>
              </div>
              <div>
                <h3 className="font-semibold">Documents</h3>
                <div className="mt-3 max-h-80 space-y-3 overflow-y-auto">
                  {facilityRecord.documents.length ? (
                    facilityRecord.documents.map((item) => (
                      <a
                        key={item.id}
                        href={item.document_url}
                        target="_blank"
                        rel="noreferrer"
                        className="block rounded-xl border border-[#d8e7e1] bg-[#f7fbf9] p-4 hover:border-violet-500"
                      >
                        <span className="text-xs text-violet-700">
                          {item.document_type} · {item.status}
                        </span>
                        <span className="mt-1 block font-semibold">
                          {item.title}
                        </span>
                        <span className="mt-1 block text-xs text-[#647c73]">
                          Added {new Date(item.created_at).toLocaleString()}
                        </span>
                      </a>
                    ))
                  ) : (
                    <p className="text-sm text-[#647c73]">
                      No documents attached yet.
                    </p>
                  )}
                </div>
              </div>
            </div>
          </section>
        ) : null}

        <section className="order-6 rounded-[2rem] border border-emerald-400/30 bg-emerald-50 p-7 sm:p-10">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="font-bold uppercase tracking-[0.2em] text-emerald-700">
                Sales lines
              </p>
              <h2 className="mt-2 text-4xl font-black">
                Use one strong line, then listen
              </h2>
            </div>
            <p className="max-w-xl text-lg text-[#48645b]">
              Click any line to copy it. Use the idea naturally—never recite the
              entire list.
            </p>
          </div>
          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            {bootstrap.sales_lines.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => navigator.clipboard?.writeText(item.line)}
                className="rounded-2xl border border-emerald-300/70 bg-white p-6 text-left transition hover:-translate-y-0.5 hover:border-emerald-400"
              >
                <span className="block font-bold uppercase tracking-[0.12em] text-emerald-700">
                  {item.title}
                </span>
                <span className="mt-3 block text-xl leading-8 text-[#0b2850]">
                  “{item.line}”
                </span>
              </button>
            ))}
          </div>
        </section>

        <section className="order-7 rounded-[2rem] border border-amber-400/30 bg-amber-50 p-7 sm:p-10">
          <p className="font-bold uppercase tracking-[0.2em] text-amber-700">
            Call rules · Read before using the engine
          </p>
          <div className="mt-5 grid gap-6 lg:grid-cols-2">
            <div className="rounded-2xl border border-[#d8e7e1] bg-white p-6">
              <h2 className="text-3xl font-black text-[#0b2850]">Call rules</h2>
              <ol className="mt-5 space-y-4 text-lg leading-8 text-[#274a40]">
                {bootstrap.rules.map((rule, index) => (
                  <li key={rule} className="flex gap-3">
                    <span className="font-bold text-amber-700">
                      {index + 1}.
                    </span>
                    <span>{rule}</span>
                  </li>
                ))}
              </ol>
            </div>
            <div className="rounded-2xl border border-[#d8e7e1] bg-white p-6">
              <h2 className="text-3xl font-black text-[#0b2850]">
                Professional bridge phrases
              </h2>
              <p className="mt-2 text-lg text-[#48645b]">
                Use one of these to keep the conversation positive and moving
                toward a concrete next step. Click to copy.
              </p>
              <div className="mt-5 grid gap-3">
                {bootstrap.bridge_phrases.map((phrase) => (
                  <button
                    key={phrase}
                    type="button"
                    onClick={() => navigator.clipboard?.writeText(phrase)}
                    className="w-full rounded-xl border border-[#d8e7e1] p-4 text-left text-lg leading-7 text-[#274a40] hover:border-amber-500"
                  >
                    “{phrase}”
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>

        <div className="order-9">
          <div className="space-y-5">
            <form
              onSubmit={submit}
              className="space-y-4 rounded-3xl border border-[#d8e7e1] bg-white p-6"
            >
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="relative text-sm text-[#48645b]">
                  Facility record
                  <input
                    value={facilityName}
                    onChange={(e) => {
                      setFacilityName(e.target.value);
                      setSelectedFacilityId("");
                      setFacilityRecord(null);
                    }}
                    placeholder="Search a Las Vegas facility"
                    className="mt-1 w-full rounded-xl border border-[#d8e7e1] bg-white px-4 py-3 text-[#0b2850]"
                  />
                  {facilityResults.length ? (
                    <div className="absolute z-20 mt-1 max-h-64 w-full overflow-y-auto rounded-xl border border-[#d8e7e1] bg-white shadow-2xl">
                      {facilityResults.map((facility) => (
                        <button
                          key={facility.canonical_facility_id}
                          type="button"
                          onClick={() => selectFacility(facility)}
                          className="block w-full border-b border-[#d8e7e1] px-4 py-3 text-left hover:bg-[#eef7f3]"
                        >
                          <span className="block font-semibold text-[#0b2850]">
                            {facility.facility_name}
                          </span>
                          <span className="text-xs text-[#647c73]">
                            {facility.city}, {facility.state} ·{" "}
                            {facility.canonical_type || "Type unknown"}
                          </span>
                        </button>
                      ))}
                    </div>
                  ) : null}
                </label>
                <label className="text-sm text-[#48645b]">
                  Call stage
                  <select
                    value={callStage}
                    onChange={(e) => setCallStage(e.target.value)}
                    className="mt-1 w-full rounded-xl border border-[#d8e7e1] bg-white px-4 py-3 text-[#0b2850]"
                  >
                    <option value="FOLLOW_UP_AFTER_EMAIL">
                      Follow-up after email
                    </option>
                    <option value="INTRODUCTION">Introduction</option>
                    <option value="COMMERCIAL_REVIEW">Commercial review</option>
                    <option value="ONBOARDING">Onboarding</option>
                    <option value="OBJECTION_HANDLING">
                      Objection handling
                    </option>
                  </select>
                </label>
              </div>
              <label className="block text-sm text-[#48645b]">
                What did the facility ask?
                <textarea
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  rows={5}
                  placeholder="Example: “Does paying Oomnik improve our ranking?”"
                  className="mt-1 w-full rounded-2xl border border-[#d8e7e1] bg-white px-4 py-3 text-[#0b2850]"
                />
              </label>
              <button
                disabled={loading || !question.trim()}
                className="rounded-full bg-[#0b6b57] px-6 py-3 font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
              >
                {loading ? "Preparing answer…" : "Get approved answer"}
              </button>
            </form>

            {error ? (
              <p className="rounded-2xl border border-rose-300 bg-rose-50 p-4 text-sm text-rose-800">
                {error}
              </p>
            ) : null}
            {answer ? (
              <article className="space-y-4 rounded-3xl border border-emerald-300 bg-emerald-50 p-6">
                <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.16em]">
                  <span className="rounded-full bg-emerald-800 px-3 py-1 text-emerald-100">
                    {answer.confidence} confidence
                  </span>
                  {answer.escalation ? (
                    <span className="rounded-full bg-amber-800 px-3 py-1 text-amber-100">
                      Escalate: {answer.escalation.replaceAll("_", " ")}
                    </span>
                  ) : null}
                </div>
                <section>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700">
                    Say this
                  </p>
                  <p className="mt-2 text-xl leading-relaxed text-[#0b2850]">
                    “{answer.say_this}”
                  </p>
                </section>
                {answer.bridge_phrase ? (
                  <section className="rounded-2xl border border-amber-300/60 bg-amber-50 p-4">
                    <p className="text-xs uppercase tracking-[0.18em] text-amber-700">
                      If you need time
                    </p>
                    <p className="mt-2 text-amber-950">
                      “{answer.bridge_phrase}”
                    </p>
                  </section>
                ) : null}
                {answer.evidence ? (
                  <section
                    className={`rounded-2xl border p-4 ${answer.evidence.verification_status === "VERIFIED" ? "border-emerald-300/60 bg-emerald-50" : "border-amber-300/60 bg-amber-50"}`}
                  >
                    <p className="text-xs font-semibold uppercase tracking-[0.18em]">
                      Agent evidence ·{" "}
                      {answer.evidence.verification_status.replaceAll("_", " ")}
                    </p>
                    <p className="mt-2 text-sm">
                      {answer.evidence.value_display} —{" "}
                      {answer.evidence.metric_definition}
                    </p>
                    <p className="mt-1 text-xs text-[#48645b]">
                      Data period: {answer.evidence.data_period} · Geography:{" "}
                      {answer.evidence.geography} · Checked:{" "}
                      {answer.evidence.checked_at}
                    </p>
                    <a
                      href={answer.evidence.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2 inline-block text-sm underline"
                    >
                      {answer.evidence.source_title} —{" "}
                      {answer.evidence.source_publisher}
                    </a>
                  </section>
                ) : null}
                {answer.objection_guidance?.supporting.length ? (
                  <section className="rounded-2xl border border-sky-300/60 bg-sky-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">
                      Use only if needed
                    </p>
                    <div className="mt-2 space-y-2">
                      {answer.objection_guidance.supporting.map((item) => (
                        <p key={item.id} className="text-sm text-[#274a40]">
                          “{item.line}”
                        </p>
                      ))}
                    </div>
                  </section>
                ) : null}
                <section>
                  <p className="text-xs uppercase tracking-[0.18em] text-[#647c73]">
                    Next step
                  </p>
                  <p className="mt-1 text-[#274a40]">{answer.next_step}</p>
                </section>
              </article>
            ) : null}
          </div>
        </div>
      </section>
    </main>
  );
}
