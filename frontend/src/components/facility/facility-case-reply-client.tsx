"use client";

import { useState, type FormEvent } from "react";
import type { FacilityCaseLetter } from "@/lib/api";

const FILE_LIMIT = 512 * 1024;
function encodeFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Could not read the attachment."));
    reader.onload = () => resolve(String(reader.result).split(",")[1]);
    reader.readAsDataURL(file);
  });
}

export function FacilityCaseReplyClient({ letter, token, facilityName }: {
  letter: FacilityCaseLetter; token: string; facilityName: string;
}) {
  const [status, setStatus] = useState<"idle" | "saving" | "received">("idle");
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (status !== "idle") return;
    const data = new FormData(event.currentTarget);
    const files = data.getAll("files").filter((file): file is File => file instanceof File && !!file.name);
    if (files.length > 2 || files.some(file => file.size > FILE_LIMIT)) {
      setError("Attach up to two files, 512 KB each.");
      return;
    }
    const answers = Object.fromEntries(letter.items.flatMap((_, index) => {
      const answer = data.get(`item-${index}`);
      return answer ? [[index, answer]] : [];
    }));
    setStatus("saving"); setError("");
    try {
      const response = await fetch(`/api/backend/facility-outreach/${encodeURIComponent(token)}/case-reply`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          answers, availability: data.get("availability") || null,
          monthly_price_cents: data.get("price") ? Math.round(Number(data.get("price")) * 100) : null,
          notes: data.get("notes"),
          files: await Promise.all(files.map(async file => ({ name: file.name, content: await encodeFile(file) }))),
        }),
      });
      if (!response.ok) {
        const detail = (await response.json().catch(() => null))?.detail;
        throw new Error(typeof detail === "string" ? detail : "We could not save your reply. Please try again.");
      }
      setStatus("received");
    } catch (err) {
      setError(err instanceof Error ? err.message : "We could not save your reply.");
      setStatus("idle");
    }
  }
  return <main className="min-h-screen bg-canvas px-5 py-10 text-ink">
    <article className="mx-auto max-w-2xl rounded-3xl border border-line bg-white p-6 sm:p-9">
      <p className="font-semibold text-forest">OOmnik · For {facilityName}</p>
      {status === "received" ? <h1 role="status" className="mt-3 text-3xl font-semibold">Thank you. We received your reply.</h1> : <>
        <h1 className="mt-3 text-3xl font-semibold">Could your community be a fit?</h1>
        <p className="mt-4 text-lg">{letter.summary}</p>
        <p className="mt-2">Please tell us what you can offer so the family can decide on their next step.</p>
        {letter.preferred_date ? <p className="mt-2">Preferred visit date: {letter.preferred_date}</p> : null}
        <form onSubmit={submit} className="mt-6 space-y-5">
          {(["MUST", "NICE"] as const).map(priority => letter.items.some(item => item.priority === priority) && <section key={priority}>
            <h2 className="text-xl font-semibold">{priority === "MUST" ? "What they need" : "What they’d like"}</h2>
            {letter.items.map((item, index) => item.priority === priority && <fieldset key={index} className="mt-3 border-b border-line pb-3">
              <legend className="font-medium">{item.label}</legend>
              <div className="mt-1 flex flex-wrap gap-4">{["yes", "no", "depends"].map(value =>
                <label className="inline-flex items-center gap-2 capitalize" key={value}><input type="radio" name={`item-${index}`} value={value} />{value}</label>)}</div>
            </fieldset>)}
          </section>)}
          <label className="block">Availability for this family
            <select name="availability" className="mt-1 block w-full rounded-lg border border-line p-2">
              <option value="">Choose if known</option><option value="available">Available</option><option value="waitlist">Waitlist</option><option value="unavailable">Unavailable</option><option value="unknown">Still checking</option>
            </select>
          </label>
          <label className="block">Estimated monthly cost including the requested care ($)
            <input name="price" type="number" min="0.01" max="1000000" step="0.01" className="mt-1 block w-full rounded-lg border border-line p-2" />
          </label>
          <label className="block">Anything we should know? <span className="text-muted">(optional)</span>
            <textarea name="notes" rows={3} maxLength={2000} className="mt-1 block w-full rounded-lg border border-line p-2" />
          </label>
          <label className="block">Attach a price sheet or activity calendar <span className="text-muted">(optional)</span>
            <input name="files" type="file" multiple accept=".pdf,.png,.jpg,.jpeg" className="mt-1 block max-w-full" />
            <span className="block text-sm text-muted">PDF, PNG or JPEG. Up to two files, 512 KB each.</span>
          </label>
          {error ? <p role="alert" className="text-[#943b28]">{error}</p> : null}
          <button disabled={status === "saving"} className="rounded-xl bg-forest px-5 py-3 font-semibold text-white disabled:opacity-40">{status === "saving" ? "Saving…" : "Send response to OOmnik"}</button>
        </form>
      </>}
    </article>
  </main>;
}
