import { describe, expect, it } from "vitest";
import { parseOomnikerQuantities } from "../src/lib/oomniker-quantity";

describe("OOmniker numeric dimensions", () => {
  it.each(["up to 10 miles", "maximum 20 miles", "budget up to 10 miles"])("never reads distance as money: %s", text => {
    expect(parseOomnikerQuantities(text).budget).toBeUndefined();
  });
  it.each(["budget 8000", "up to $8,000", "maximum 8000 dollars", "USD 8000"])("retains explicit prices: %s", text => {
    expect(parseOomnikerQuantities(text).budget).toBe(8000);
  });
  it("keeps both dimensions in a combined request", () => {
    expect(parseOomnikerQuantities("up to 10 miles, budget $8,000")).toMatchObject({ miles: "10", budget: 8000 });
  });
  it.each(["radius is not important", "remove radius limit", "distance no longer important"])("clears a withdrawn radius: %s", text => {
    expect(parseOomnikerQuantities(text).clearRadius).toBe(true);
  });
  it("does not invent budget for a dimensionless number", () => {
    expect(parseOomnikerQuantities("maximum 10").budget).toBeUndefined();
  });
});
