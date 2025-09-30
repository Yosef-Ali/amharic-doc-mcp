import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import ProcessingDashboard from "@/components/ProcessingDashboard";

describe("ProcessingDashboard", () => {
  it("renders job status timeline", () => {
    render(
      <ProcessingDashboard
        jobs={[{ id: "1", jobName: "Test", status: "running", progress: 50 }]}
      />
    );
    expect(screen.getByText(/Test/)).toBeInTheDocument();
  });
});
