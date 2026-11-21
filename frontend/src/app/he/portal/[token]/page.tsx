"use client";

import { useRouter } from "next/navigation";
import { use, useEffect, useState } from "react";

import { redeemPortalLink } from "@/lib/provider-api";
import { saveProviderSession } from "@/lib/provider-session";

/**
 * A facility's personal OOMNIK link. Opening it signs the browser in to that facility's
 * portal and moves on, so the secret token does not stay in the address bar or history.
 */
export default function PortalLinkPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    redeemPortalLink(token)
      .then((session) => {
        if (cancelled) return;
        saveProviderSession(session);
        router.replace(`/provider/${session.facility_id}/israel`);
      })
      .catch((redeemError) => {
        if (!cancelled) setError(redeemError instanceof Error ? redeemError.message : "הקישור אינו בתוקף.");
      });
    return () => {
      cancelled = true;
    };
  }, [token, router]);

  return (
    <main dir="rtl" lang="he" className="mx-auto max-w-xl p-6">
      <h1 className="text-2xl font-semibold">הפורטל של המוסד ב-OOMNIK</h1>
      {error ? (
        <p role="alert" className="mt-4 rounded-xl border p-3">{error}</p>
      ) : (
        <p role="status" className="mt-4">מתחברים…</p>
      )}
    </main>
  );
}
