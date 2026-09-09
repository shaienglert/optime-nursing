import type { Metadata } from "next";
import Link from "next/link";

import { LAS_VEGAS_MARKET_FACTS } from "@/content/public-market-content";

export const metadata: Metadata = {
  title: "Las Vegas Senior Living Market Data",
  description: "Evidence-backed senior-care supply and nursing-home market statistics for Las Vegas and Nevada, with definitions and primary sources.",
  alternates: { canonical: "/las-vegas-senior-living" },
};

const CMS_PROVIDER_URL = "https://data.cms.gov/provider-data/dataset/4pq5-n9py";
const CMS_MDS_URL = "https://data.cms.gov/provider-data/dataset/djen-97ju";
const CMS_CLAIMS_URL = "https://data.cms.gov/provider-data/dataset/ijh5-nb2v";
const NEVADA_LICENSE_URL = "https://nvdpbh.aithent.com/Protected/LIC/LicenseeSearch.aspx?Program=HF&PubliSearch=Y";
const NIC_URL = "https://www.nic.org/news-press/senior-living-occupancy-grows-amid-construction-slowdown-limiting-options-for-older-adults/";

function FactCards({ facts }: { facts: ReadonlyArray<{ value: string; label: string; detail?: string }> }) {
  return <div className="mt-7 grid gap-4 sm:grid-cols-2">{facts.map((fact) => <div key={fact.label} className="rounded-3xl border border-[#d8e7e1] bg-white p-6 shadow-sm"><p className="text-4xl font-semibold tracking-[-0.04em] text-[#1e4f43]">{fact.value}</p><h3 className="mt-2 font-semibold text-[#22332d]">{fact.label}</h3>{fact.detail ? <p className="mt-2 text-sm leading-6 text-[#62736c]">{fact.detail}</p> : null}</div>)}</div>;
}

export default function LasVegasSeniorLivingPage() {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    name: "Las Vegas and Nevada senior-care market snapshot",
    description: "Source-labelled descriptive senior-care and skilled-nursing market facts. Not facility availability or a ranking input.",
    spatialCoverage: ["Las Vegas Valley", "Nevada", "United States"],
    temporalCoverage: "2026-08/2026-09",
    creator: { "@type": "Organization", name: "OPTIME" },
  };
  return <main className="min-h-screen bg-[#f8f5ef] text-[#21312b]"><section className="border-b border-[#dbe4df] bg-[#edf6f1]"><div className="mx-auto max-w-6xl px-5 py-16 sm:px-8 lg:px-12"><p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#3a7969]">Market transparency</p><h1 className="mt-4 max-w-4xl text-4xl font-semibold tracking-[-0.04em] sm:text-6xl">Las Vegas senior living market data</h1><p className="mt-5 max-w-3xl text-lg leading-8 text-[#52645d]">A source-labelled view of the evidence we currently have — so families can understand the market without confusing market data with a personal recommendation.</p><p className="mt-5 text-sm text-[#60716a]">Updated {LAS_VEGAS_MARKET_FACTS.updatedLabel}. Values are descriptive and never used as a facility ranking input.</p></div></section><section className="mx-auto max-w-6xl px-5 py-16 sm:px-8 lg:px-12"><h2 className="text-3xl font-semibold tracking-[-0.035em]">Current evidence-backed local supply</h2><FactCards facts={LAS_VEGAS_MARKET_FACTS.supply} /><p className="mt-5 max-w-4xl text-sm leading-6 text-[#62736c]">The local location count is a coverage inventory, not a statement that every property has an opening or fits every person. It includes state-licensed care records and separately verified independent-living properties.</p><h2 className="mt-16 text-3xl font-semibold tracking-[-0.035em]">CMS skilled-nursing comparison</h2><p className="mt-3 max-w-3xl leading-7 text-[#52645d]">These values apply only to Medicare/Medicaid-certified nursing homes. They should not be generalized to all senior living.</p><div className="mt-7 grid gap-8 lg:grid-cols-2"><div><h3 className="text-xl font-semibold">Nevada</h3><FactCards facts={LAS_VEGAS_MARKET_FACTS.skilledNursing} /></div><div><h3 className="text-xl font-semibold">United States</h3><FactCards facts={LAS_VEGAS_MARKET_FACTS.national} /></div></div><section className="mt-16 rounded-3xl border border-[#d8e7e1] bg-white p-7 sm:p-10"><h2 className="text-2xl font-semibold">What is not shown as a number</h2><p className="mt-4 max-w-4xl leading-7 text-[#52645d]">We do not publish a statewide Nevada occupancy rate, construction pipeline or population projection until a source supports the exact measure and geography. The public NIC release reports Q1 2026 senior-housing occupancy of 87.0% for Las Vegas and 89.5% nationally; that is market context, not a claim of vacancy at an individual community.</p><a className="mt-4 inline-block text-sm font-semibold text-[#285f51] underline underline-offset-4" href={NIC_URL} target="_blank" rel="noreferrer">Read the NIC public release</a></section><section className="mt-16"><h2 className="text-2xl font-semibold">Sources and definitions</h2><ul className="mt-5 space-y-3 text-sm leading-6 text-[#52645d]"><li><a className="text-[#285f51] underline underline-offset-4" href={NEVADA_LICENSE_URL} target="_blank" rel="noreferrer">Nevada HCQC / ALiS license registry</a> — licensed-care coverage only.</li><li><a className="text-[#285f51] underline underline-offset-4" href={CMS_PROVIDER_URL} target="_blank" rel="noreferrer">CMS Provider Information</a> — CMS-certified nursing-home count and certified beds.</li><li><a className="text-[#285f51] underline underline-offset-4" href={CMS_MDS_URL} target="_blank" rel="noreferrer">CMS MDS Quality Measures</a> — falls with major injury.</li><li><a className="text-[#285f51] underline underline-offset-4" href={CMS_CLAIMS_URL} target="_blank" rel="noreferrer">CMS Medicare Claims Quality Measures</a> — short-stay rehospitalization.</li></ul></section><section className="mt-16 border-t border-[#dbe4df] pt-10"><h2 className="text-2xl font-semibold">Planning a move?</h2><p className="mt-3 text-[#52645d]">Use the market facts as context, then start with the person&apos;s needs and verify every material facility claim.</p><div className="mt-5 flex flex-wrap gap-4"><Link href="/" className="rounded-full bg-[#285f51] px-5 py-3 text-sm font-semibold text-white">Start a guided search</Link><Link href="/guides" className="rounded-full border border-[#8fb4a8] px-5 py-3 text-sm font-semibold text-[#285f51]">Read family guides</Link></div></section></section><script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} /></main>;
}
