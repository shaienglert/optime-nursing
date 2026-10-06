import { describe, expect, it } from "vitest";
import { budgetChoices } from "../src/lib/budget-choices";

describe("area budget choices", () => {
  it("retains an irregular local minimum with exact $500 increments", () => {
    expect(budgetChoices(4328, 6000)).toEqual([4328, 4828, 5328, 5828]);
  });
  it("does not duplicate a minimum already on the $500 grid", () => {
    expect(budgetChoices(5000, 6500)).toEqual([5000, 5500, 6000, 6500]);
  });
  it("never rounds a fractional minimum below the known price", () => {
    expect(budgetChoices(4500.5, 5500)).toEqual([4500.5, 5000.5]);
  });
});
