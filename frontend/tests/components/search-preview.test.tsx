import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import SearchPreview from "@/components/SearchPreview";

describe("SearchPreview", () => {
  it("renders search results with highlights", () => {
    render(
      <SearchPreview
        results={[
          {
            id: "1",
            title: "ኢትዮጵያ",
            snippet: "<mark>ኢትዮጵያ</mark> ታሪክ",
            metadata: { author: "Tester" },
          },
        ]}
      />
    );
    expect(screen.getByText(/ኢትዮጵያ/)).toBeInTheDocument();
  });
});
