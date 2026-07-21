import { FacilityProfileClient } from "@/components/facility/facility-profile-client";

type FacilityPageProps = {
  params: Promise<{ id: string }>;
};

export default async function FacilityPage({ params }: FacilityPageProps) {
  const resolved = await params;
  return <FacilityProfileClient facilityId={String(resolved.id || "")} backHref="/results" backLabel="Back to results" />;
}
