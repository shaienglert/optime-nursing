import { CanonicalFacilityProfileClient } from "@/components/facility/canonical-facility-profile-client";
import { FacilityProfileClient } from "@/components/facility/facility-profile-client";

type FacilityPageProps = {
  params: Promise<{ id: string }>;
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

function firstValue(value: string | string[] | undefined): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

export default async function FacilityPage({ params, searchParams }: FacilityPageProps) {
  const resolved = await params;
  const resolvedSearchParams = searchParams ? await searchParams : {};
  const backHref = firstValue(resolvedSearchParams.back) || firstValue(resolvedSearchParams.returnTo) || "/results";
  const canonicalFacilityId = firstValue(resolvedSearchParams.canonical)?.trim();

  if (String(resolved.id || "") === "canonical" && canonicalFacilityId) {
    return (
      <CanonicalFacilityProfileClient
        canonicalFacilityId={canonicalFacilityId}
        backHref={backHref}
        backLabel="Back to results"
      />
    );
  }

  return <FacilityProfileClient facilityId={String(resolved.id || "")} backHref={backHref} backLabel="Back to results" />;
}
