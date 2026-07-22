import { describe, expect, it } from "vitest";

import { fuzzyScore } from "../lib/fuzzy";

describe("fuzzyScore", () => {
  it("returns a score for a subsequence match", () => {
    expect(fuzzyScore("wkb", "Workbench")).not.toBeNull();
  });

  it("is case-insensitive", () => {
    expect(fuzzyScore("TASK", "tasks")).not.toBeNull();
  });

  it("returns null when characters are missing or out of order", () => {
    expect(fuzzyScore("xyz", "Workbench")).toBeNull();
    expect(fuzzyScore("hc", "chat")).toBeNull();
  });

  it("scores consecutive runs higher than scattered matches", () => {
    const consecutive = fuzzyScore("work", "workbench");
    const scattered = fuzzyScore("wbch", "workbench");
    expect(consecutive).not.toBeNull();
    expect(scattered).not.toBeNull();
    expect(consecutive!).toBeGreaterThan(scattered!);
  });

  it("returns a score for an empty query", () => {
    expect(fuzzyScore("", "anything")).not.toBeNull();
  });
});
