import { expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { DistanceScope } from "../src/app/results/distance-scope";
it("does not describe geographically counted communities as verified matches", () => {
  const html = renderToStaticMarkup(<DistanceScope scope={{ applied: true, reason: "RADIUS_APPLIED", requested_miles: 10, effective_miles: 10, expansion_offer: { miles: 15, additional_count: 128, nearest_excluded_miles: 10.1 } }} onWiden={() => {}} />);
  expect(html).toContain("more in the wider area");
  expect(html).toContain("still need to pass your care requirements and budget checks");
  expect(html).not.toContain("more fit");
});
