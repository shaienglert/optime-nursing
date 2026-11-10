import { FacilityOutreachResponseClient } from "@/components/facility/facility-outreach-response-client";

export const metadata = { referrer: "no-referrer", robots: { index: false, follow: false } };

type FacilityOutreachResponsePageProps = {
  params: Promise<{ token: string }>;
};

export default async function FacilityOutreachResponsePage({ params }: FacilityOutreachResponsePageProps) {
  const resolved = await params;
  return <FacilityOutreachResponseClient responseToken={resolved.token} />;
}
