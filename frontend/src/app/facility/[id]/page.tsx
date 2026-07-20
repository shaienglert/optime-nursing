import { FacilityProfileClient } from "@/components/facility/facility-profile-client";

type FacilityPageProps = {
  params: { id: string };
};

export default async function FacilityPage({ params }: FacilityPageProps) {
  return <FacilityProfileClient facilityId={String(params.id || "")} backHref="/results" backLabel="Back to results" />;
}
