import { render, screen } from "@testing-library/react";
import axe from "axe-core";
import { describe, expect, it } from "vitest";

import "../i18n";
import { StatusBadge } from "../components/StatusBadge";

describe("StatusBadge", () => {
  it("renders a translated label for a known status", () => {
    render(<StatusBadge status="completed" />);
    expect(screen.getByText("已完成")).toBeInTheDocument();
  });

  it("humanizes an unknown status instead of crashing", () => {
    render(<StatusBadge status="some_unknown_state" />);
    expect(screen.getByText("some unknown state")).toBeInTheDocument();
  });

  it("has no axe violations", async () => {
    const { container } = render(<StatusBadge status="running" />);
    const results = await axe.run(container);
    expect(results.violations).toEqual([]);
  });
});
