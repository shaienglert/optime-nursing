import { redirect } from "next/navigation";

type LegacyFacilityPageProps = {
  params: Promise<{ id: string }>;
};

export default async function LegacyFacilityPage({ params }: LegacyFacilityPageProps) {
  const resolved = await params;
  redirect(`/facility/${resolved.id}`);
}
