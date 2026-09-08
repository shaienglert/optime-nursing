import { FacilityOutreachResponseClient } from "@/components/facility/facility-outreach-response-client";

type FacilityOutreachResponsePageProps = {
  params: Promise<{ token: string }>;
};

export default async function FacilityOutreachResponsePage({ params }: FacilityOutreachResponsePageProps) {
  const resolved = await params;
  return <FacilityOutreachResponseClient responseToken={resolved.token} />;
}
