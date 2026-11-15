"use client";

import { useState } from "react";

const rooms = [
  { name: "One-bedroom suite", price: 7711, status: "1 unit available", photo: "/pilot-media/private-room.svg" },
  { name: "Private studio", price: 6811, status: "Waitlist · 0 available", photo: "/pilot-media/private-room.svg" },
];
const gallery = [
  { src: "/pilot-media/community-exterior.svg", title: "Community exterior" },
  { src: "/pilot-media/garden.svg", title: "Gardens & outdoor spaces" },
  { src: "/pilot-media/dining-room.svg", title: "Dining room" },
  { src: "/pilot-media/community-lounge.svg", title: "Community lounge" },
  { src: "/pilot-media/private-room.svg", title: "Room illustration" },
];
const services = [
  ["Care coordination", "Physician coordination, medication support, ADL assistance"],
  ["Clinical support", "Nursing, oxygen support, daily wound care"],
  ["Rehabilitation", "PT / OT and rehabilitation services"],
  ["Dialysis", "3 sessions per week and transport support"],
  ["Mobility", "Walker- and wheelchair-accessible routes"],
  ["Community", "Daily organized music, classes and social activities"],
];
const sampleEvents = [
  { day: "MON", time: "10:00 AM", name: "Morning movement class" },
  { day: "TUE", time: "2:00 PM", name: "Music & social hour" },
  { day: "WED", time: "11:00 AM", name: "Garden gathering" },
  { day: "THU", time: "3:00 PM", name: "Creative workshop" },
];
export default function RedRockShowcase() {
  const [image, setImage] = useState(gallery[0]);
  const [tab, setTab] = useState("Overview");
  const [notice, setNotice] = useState("");
  const btn = "rounded-full bg-[#34574a] px-6 py-3 font-semibold text-white hover:bg-[#254237]";
  return (
    <main className="min-h-screen bg-[#fdfbf7] text-[#263c34]">
      <div className="border-b border-[#e5e7df] bg-[#eef1e8] px-5 py-2 text-center text-xs font-semibold tracking-wide">FICTIONAL COMMUNITY · SYNTHETIC PILOT DATA · ILLUSTRATIVE PHOTOGRAPHY · NOT A REAL FACILITY</div>
      <div className="mx-auto max-w-7xl px-5 py-6">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <a href="/" className="text-2xl font-bold tracking-tight">OO<span className="font-normal">mnik</span></a>
          <span className="text-sm text-[#69786e]">Senior living, with clarity</span>
          <button className={btn} onClick={() => document.getElementById("tour")?.scrollIntoView({behavior:"smooth"})}>Request a tour</button>
        </header>
        <div className="mt-8 text-sm text-[#718076]">Las Vegas, Nevada / Continuing care / Community profile</div>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-5">
          <div><h1 className="text-4xl font-semibold tracking-tight md:text-5xl">Red Rock Village</h1><p className="mt-2 text-lg text-[#65786c]">Continuing Care Community · 1359 Pilot Mesa Avenue, Las Vegas, NV 89101</p></div>
          <div className="rounded-2xl border border-[#dce2d9] bg-white p-4"><div className="text-xs uppercase tracking-wider text-[#708175]">Monthly accommodation from</div><div className="text-3xl font-semibold">$6,811<span className="text-sm font-normal"> / month</span></div><div className="text-xs text-[#7c887d]">Synthetic pricing · subject to confirmation</div></div>
        </div>
        <div className="mt-7 grid gap-3 md:grid-cols-[1.7fr_1fr]">
          <div className="relative overflow-hidden rounded-3xl bg-[#e4e8e0]"><img src={image.src} alt={image.title} className="h-[380px] w-full object-cover"/><div className="absolute bottom-4 left-4 rounded-full bg-white/90 px-4 py-2 text-xs">{image.title} · Synthetic illustration</div></div>
          <div className="grid grid-cols-2 gap-3">{gallery.slice(1).map(g=><button key={g.src} onClick={()=>setImage(g)} className="overflow-hidden rounded-2xl bg-[#e4e8e0]"><img src={g.src} alt={g.title} className="h-[183px] w-full object-cover hover:scale-105 transition-transform"/></button>)}</div>
        </div>
        <nav className="mt-7 flex gap-2 overflow-x-auto border-b border-[#e0e4dc] pb-3">{["Overview","Care & services","Rooms & pricing","Activities","Transparency"].map(x=><button key={x} onClick={()=>{setTab(x);document.getElementById(x.replaceAll(" ","-"))?.scrollIntoView({behavior:"smooth"})}} className={"whitespace-nowrap rounded-full px-5 py-2 text-sm "+(tab===x?"bg-[#34574a] text-white":"bg-white text-[#34574a]")}>{x}</button>)}</nav>
        <section id="Overview" className="grid gap-8 py-12 lg:grid-cols-[1.5fr_1fr]">
          <div><div className="text-sm font-semibold uppercase tracking-widest text-[#8d997f]">A place to call home</div><h2 className="mt-3 text-3xl font-semibold">Support for changing needs, in one community.</h2><p className="mt-5 max-w-2xl leading-8 text-[#5c6b60]">This fictional continuing-care community demonstrates how OOmnik can present provider-supplied details, room options, clinical capabilities and supporting evidence in one transparent experience. All data on this page is synthetic and must not be used for a real placement decision.</p><div className="mt-7 grid grid-cols-2 gap-3 sm:grid-cols-4">{[["239","Licensed capacity"],["62+","Minimum age"],["Yes","Couples accepted"],["EN · HE","Languages"]].map(([n,l])=><div key={l} className="rounded-2xl bg-[#edf0e8] p-4"><div className="text-2xl font-semibold">{n}</div><div className="mt-1 text-xs text-[#66766c]">{l}</div></div>)}</div></div>
          <aside className="rounded-3xl bg-white p-7 shadow-sm"><h3 className="text-xl font-semibold">At a glance</h3><dl className="mt-5 space-y-4 text-sm">{[["Community type","Continuing care (CCRC archetype)"],["Synthetic licence","SYNTHETIC_PILOT_ACTIVE"],["Licence expiry (test)","Dec 31, 2030"],["Memory-care classification","Confirmed in synthetic fixture"],["Couples","Accepted"],["Entrance fee (test)","$92,500"]].map(([k,v])=><div key={k} className="flex justify-between gap-4 border-b border-[#edf0e8] pb-3"><dt className="text-[#6b786d]">{k}</dt><dd className="text-right font-medium">{v}</dd></div>)}</dl></aside>
        </section>
        <section id="Care-&-services" className="py-10"><h2 className="text-3xl font-semibold">Care & services</h2><p className="mt-2 text-[#718076]">Reported capabilities from the synthetic pilot dataset — not real-world verification.</p><div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">{services.map(([title,description])=><div key={title} className="rounded-2xl border border-[#e2e7dd] bg-white p-6"><div className="mb-3 text-2xl text-[#72917c]">✦</div><h3 className="font-semibold">{title}</h3><p className="mt-2 text-sm leading-6 text-[#66766b]">{description}</p></div>)}</div><p className="mt-4 rounded-xl bg-[#f2ede4] p-4 text-sm">Important: Continuing care and memory-care classification are present in the fixture, but individual IL / AL / MC / SNF departments are not separately enumerated. They must be confirmed before displaying a real department-by-department inventory. Kosher meals are not verified.</p></section>
        <section id="Rooms-&-pricing" className="py-10"><h2 className="text-3xl font-semibold">Rooms & monthly pricing</h2><p className="mt-2 text-[#718076]">Synthetic provider-reported room types. Prices are starting points, not binding offers.</p><div className="mt-6 grid gap-5 md:grid-cols-2">{rooms.map(r=><article key={r.name} className="overflow-hidden rounded-3xl border border-[#e2e7dd] bg-white"><img src={r.photo} alt={"Synthetic illustration of "+r.name} className="h-52 w-full object-cover"/><div className="p-6"><div className="flex items-start justify-between gap-4"><h3 className="text-xl font-semibold">{r.name}</h3><span className="text-lg font-semibold">${r.price.toLocaleString()}/mo</span></div><p className="mt-2 text-sm text-[#68786d]">{r.status}</p><button onClick={()=>document.getElementById("tour")?.scrollIntoView({behavior:"smooth"})} className="mt-5 rounded-full border border-[#34574a] px-5 py-2 text-sm font-semibold">Ask about this room</button></div></article>)}</div><p className="mt-4 text-sm text-[#6e796f]">Additional resident: $750/month (synthetic). Entrance fee: $92,500 (synthetic). Final rates and inclusions require facility confirmation.</p></section>
        <section id="Activities" className="py-10"><div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-3xl font-semibold">Life at Red Rock Village</h2><p className="mt-2 text-[#718076]">The dataset confirms a general daily activity schedule. Individual events below are illustrative placeholders.</p></div><span className="rounded-full bg-[#eef1e9] px-4 py-2 text-sm">Calendar integration: demo mode</span></div><div className="mt-6 grid gap-4 md:grid-cols-4">{sampleEvents.map(e=><div key={e.day} className="rounded-2xl bg-white p-5 shadow-sm"><div className="text-xs font-semibold tracking-widest text-[#7e977c]">{e.day}</div><div className="mt-4 text-xl font-semibold">{e.name}</div><div className="mt-3 text-sm text-[#6d7b70]">{e.time}</div><div className="mt-4 text-xs text-[#a07750]">Example · not a confirmed event</div></div>)}</div><div className="mt-6 rounded-2xl border border-dashed border-[#a6b5a8] p-5 text-sm text-[#64776a]">Future live integration: provider-managed calendar or iCal feed, event updates, RSVP, cancellation notices and accessible family view. No external calendar is connected in this demo.</div></section>
        <section id="Transparency" className="py-10"><h2 className="text-3xl font-semibold">Transparency & evidence</h2><div className="mt-5 grid gap-4 md:grid-cols-3">{[["Facility data","Synthetic provider fixture · Oct 3, 2026"],["Media","OOmnik-owned illustrations · not photographs"],["Licence & availability","Synthetic only · not government-verified"]].map(([a,b])=><div key={a} className="rounded-2xl bg-[#edf0e8] p-5"><h3 className="font-semibold">{a}</h3><p className="mt-2 text-sm text-[#65746b]">{b}</p></div>)}</div></section>
        <section id="tour" className="my-12 rounded-3xl bg-[#34574a] p-8 text-white md:p-12"><h2 className="text-3xl font-semibold">Experience the community</h2><p className="mt-3 max-w-xl text-[#e4ece4]">Tour scheduling is a demonstration only. No real facility will be contacted.</p><div className="mt-6 flex flex-wrap gap-3"><button className="rounded-full bg-white px-6 py-3 font-semibold text-[#34574a]" onClick={()=>setNotice("Demo only: tour scheduling will connect to provider availability once configured.")}>Request a tour</button><button className="rounded-full border border-white px-6 py-3" onClick={()=>setNotice("Demo only: provider questions will be routed through OOmnik after integration.")}>Ask OOmnik a question</button></div>{notice&&<p role="status" className="mt-4 text-sm text-white">{notice}</p>}</section>
      </div>
    </main>
  );
}
