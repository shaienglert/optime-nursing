"use client";

import { useEffect, useRef } from "react";

export type EvidenceDetailRecord = {
  title?: string;
  eventType?: string;
  date?: string;
  amount?: string;
  severityScope?: string;
  description?: string;
  status?: string;
  identifier?: string;
  reportingPeriod?: string;
  sourceOrganization?: string;
  sourceDate?: string;
  sourceUrl?: string;
};

export type EvidenceDetailsPayload = {
  facilityName: string;
  parameterLabel: string;
  summary: string;
  records: EvidenceDetailRecord[];
  unavailableDetailsMessage?: string;
};

type EvidenceDetailsModalProps = {
  isOpen: boolean;
  payload: EvidenceDetailsPayload | null;
  onClose: () => void;
};

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "textarea:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

function maybeLink(url?: string): string | null {
  if (!url) return null;
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  return null;
}

export function EvidenceDetailsModal({ isOpen, payload, onClose }: EvidenceDetailsModalProps) {
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const restoreFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    restoreFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const focusTimer = window.setTimeout(() => {
      closeButtonRef.current?.focus();
    }, 0);

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== "Tab") return;
      const dialog = dialogRef.current;
      if (!dialog) return;

      const focusables = Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
        (node) => !node.hasAttribute("disabled") && node.tabIndex !== -1,
      );
      if (focusables.length === 0) {
        event.preventDefault();
        return;
      }

      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = document.activeElement as HTMLElement | null;

      if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);

    return () => {
      window.clearTimeout(focusTimer);
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
      restoreFocusRef.current?.focus();
    };
  }, [isOpen, onClose]);

  if (!isOpen || !payload) return null;

  return (
    <div
      className="fixed inset-0 z-[90] bg-[#1f2024]/45 px-4 py-4 sm:py-8"
      role="presentation"
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={`${payload.parameterLabel} evidence details`}
        className="mx-auto flex h-full w-full max-w-3xl flex-col overflow-hidden rounded-3xl border border-[#d9e3ec] bg-white shadow-[0_30px_90px_-44px_rgba(17,28,40,0.7)]"
      >
        <header className="flex items-start justify-between gap-3 border-b border-[#e6edf3] px-5 py-4 sm:px-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#4a6076]">Evidence details</p>
            <h2 className="mt-1 text-lg font-semibold text-[#23364a] sm:text-xl">{payload.parameterLabel}</h2>
            <p className="mt-1 text-sm text-[#4f6173]">{payload.facilityName}</p>
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-[#d0dde8] bg-white text-[#294861] hover:bg-[#edf5fb]"
            aria-label="Close evidence details"
          >
            x
          </button>
        </header>

        <div className="overflow-y-auto px-5 py-4 sm:px-6">
          <p className="rounded-2xl border border-[#e6edf3] bg-[#f8fbff] px-4 py-3 text-sm text-[#334e67]">{payload.summary}</p>

          {payload.unavailableDetailsMessage ? (
            <p className="mt-4 rounded-2xl border border-[#f0d9b0] bg-[#fff8ea] px-4 py-3 text-sm text-[#6f4f1f]">
              {payload.unavailableDetailsMessage}
            </p>
          ) : null}

          {payload.records.length > 0 ? (
            <ol className="mt-5 space-y-3">
              {payload.records.map((record, index) => {
                const validSourceUrl = maybeLink(record.sourceUrl);
                return (
                  <li key={`${record.identifier || record.title || record.eventType || "record"}-${index}`} className="rounded-2xl border border-[#e6edf3] bg-white px-4 py-3 text-sm text-[#2e3d4d]">
                    <p className="font-semibold text-[#23364a]">{record.title || record.eventType || `Record ${index + 1}`}</p>
                    {record.date ? <p className="mt-1"><span className="font-medium">Date:</span> {record.date}</p> : null}
                    {record.amount ? <p><span className="font-medium">Amount:</span> {record.amount}</p> : null}
                    {record.severityScope ? <p><span className="font-medium">Severity/scope:</span> {record.severityScope}</p> : null}
                    {record.description ? <p><span className="font-medium">Description:</span> {record.description}</p> : null}
                    {record.status ? <p><span className="font-medium">Status:</span> {record.status}</p> : null}
                    {record.identifier ? <p><span className="font-medium">Identifier:</span> {record.identifier}</p> : null}
                    {record.reportingPeriod ? <p><span className="font-medium">Reporting period:</span> {record.reportingPeriod}</p> : null}
                    {record.sourceOrganization ? <p><span className="font-medium">Source:</span> {record.sourceOrganization}</p> : null}
                    {record.sourceDate ? <p><span className="font-medium">Source date:</span> {record.sourceDate}</p> : null}
                    {validSourceUrl ? (
                      <a href={validSourceUrl} target="_blank" rel="noreferrer" className="mt-2 inline-flex text-[#1f5f94] underline underline-offset-2">
                        View official source
                      </a>
                    ) : null}
                  </li>
                );
              })}
            </ol>
          ) : null}
        </div>
      </div>
    </div>
  );
}
