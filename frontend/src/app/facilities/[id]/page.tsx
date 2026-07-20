import { redirect } from "next/navigation";

type LegacyFacilityPageProps = {
  params: { id: string };
};

export default async function LegacyFacilityPage({ params }: LegacyFacilityPageProps) {
  redirect(`/facility/${params.id}`);
}
