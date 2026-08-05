export type AssessmentRegion = {
  id: string;
  city: string;
  state: string;
  marketName: string;
  regionName: string;
  allAreasValue: string;
  allAreasLabel: string;
  areas: Array<{ value: string; label: string }>;
};

export const ASSESSMENT_REGIONS: Record<string, AssessmentRegion> = {
  "las-vegas": {
    id: "las-vegas",
    city: "Las Vegas",
    state: "Nevada",
    marketName: "Las Vegas, Nevada",
    regionName: "Las Vegas Valley",
    allAreasValue: "LAS_VEGAS_VALLEY",
    allAreasLabel: "Anywhere in the Las Vegas Valley",
    areas: [
      { value: "LAS_VEGAS", label: "Las Vegas" },
      { value: "SUMMERLIN", label: "Summerlin" },
      { value: "HENDERSON", label: "Henderson" },
      { value: "PARADISE", label: "Paradise" },
      { value: "SPRING_VALLEY", label: "Spring Valley" },
      { value: "ENTERPRISE", label: "Enterprise" },
      { value: "NORTH_LAS_VEGAS", label: "North Las Vegas" },
      { value: "CENTENNIAL_HILLS", label: "Centennial Hills" },
      { value: "LAS_VEGAS_VALLEY", label: "Anywhere in the Las Vegas Valley" },
    ],
  },
};

const configuredRegion = process.env.NEXT_PUBLIC_ASSESSMENT_REGION || "las-vegas";
export const ACTIVE_ASSESSMENT_REGION = ASSESSMENT_REGIONS[configuredRegion] || ASSESSMENT_REGIONS["las-vegas"];