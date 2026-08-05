import { LiveFacilityProfileClient } from "@/components/facility/live-facility-profile-client";

type LegacyFacilityPageProps = {
  params: Promise<{ id: string }>;
};

export default async function LegacyFacilityPage({ params }: LegacyFacilityPageProps) {
  const resolved = await params;
  return <LiveFacilityProfileClient cmsCcn={resolved.id} />;
}
