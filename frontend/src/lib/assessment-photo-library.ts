export type AssessmentPhotoCategory =
  | "Modern Assisted Living"
  | "Skilled Nursing"
  | "Luxury Assisted Living"
  | "Boutique Community"
  | "Urban Community"
  | "Nature Campus"
  | "Garden Courtyard"
  | "Dining"
  | "Lobby"
  | "Rehabilitation"
  | "Walking Trails";

export type AssessmentPhotoAsset = {
  id: string;
  category: AssessmentPhotoCategory;
  imageUrl: string;
  sourcePageUrl: string;
  alt: string;
  marketTags: string[];
};

const pexelsAsset = (id: string, category: AssessmentPhotoCategory, alt: string, marketTags: string[]): AssessmentPhotoAsset => ({
  id,
  category,
  imageUrl: `https://images.pexels.com/photos/${id}/pexels-photo-${id}.jpeg?auto=compress&cs=tinysrgb&w=2200`,
  sourcePageUrl: `https://www.pexels.com/photo/${id}/`,
  alt,
  marketTags,
});

export const ASSESSMENT_PHOTO_LIBRARY: AssessmentPhotoAsset[] = [
  pexelsAsset("31656168", "Garden Courtyard", "Contemporary residential community surrounding a landscaped courtyard", ["universal"]),
  pexelsAsset("27075286", "Modern Assisted Living", "Modern residential community with an accessible landscaped entrance", ["universal"]),
  pexelsAsset("27307400", "Walking Trails", "Landscaped walking route between contemporary community buildings", ["universal"]),
  pexelsAsset("12029117", "Luxury Assisted Living", "Contemporary community architecture with broad windows and gardens", ["desert", "las-vegas"]),
  pexelsAsset("12029123", "Garden Courtyard", "Accessible garden path with seating in a modern residential setting", ["desert", "las-vegas"]),
  pexelsAsset("37763332", "Urban Community", "Contemporary urban residential community in natural light", ["urban"]),
  pexelsAsset("5894319", "Lobby", "Warm modern shared interior with natural materials", ["universal"]),
  pexelsAsset("7329702", "Dining", "Refined communal dining interior with natural light", ["universal"]),
  pexelsAsset("7544978", "Rehabilitation", "Bright contemporary wellness and movement space", ["universal"]),
  pexelsAsset("7545207", "Skilled Nursing", "Calm accessible community interior with modern finishes", ["universal"]),
  pexelsAsset("7729133", "Boutique Community", "Intimate contemporary shared lounge", ["universal"]),
  pexelsAsset("8086759", "Nature Campus", "Modern community architecture integrated with planted grounds", ["universal"]),
  pexelsAsset("18429307", "Walking Trails", "Residents walking through a landscaped community environment", ["desert", "las-vegas"]),
  pexelsAsset("27307397", "Modern Assisted Living", "Modern apartment-style community with balconies in daylight", ["urban"]),
  pexelsAsset("29174528", "Urban Community", "Contemporary residential buildings framed by seasonal landscaping", ["urban"]),
  pexelsAsset("34360409", "Garden Courtyard", "Modern residential complex with a landscaped garden", ["desert", "las-vegas"]),
  pexelsAsset("29174529", "Luxury Assisted Living", "Contemporary community exterior with glass balconies", ["universal"]),
  pexelsAsset("31656175", "Urban Community", "Contemporary high-rise residential community with balconies", ["urban"]),
  pexelsAsset("31656170", "Boutique Community", "White modern residential buildings with greenery", ["universal"]),
  pexelsAsset("31640048", "Nature Campus", "Contemporary architecture arranged around a quiet courtyard", ["universal"]),
];

export const DEVELOPMENT_PHOTO_FALLBACK = "/images/assessment/modern-community-31656168.jpg";
export const PEXELS_LICENSE_URL = "https://www.pexels.com/license/";
