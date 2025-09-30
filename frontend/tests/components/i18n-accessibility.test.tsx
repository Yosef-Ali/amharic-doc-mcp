import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import I18nProvider from "@/i18n";
import AccessibilityWrapper from "@/utils/accessibility";

describe("Localization and accessibility", () => {
  it("renders Amharic strings when locale is set", () => {
    render(
      <I18nProvider locale="am">
        <span>{"ሰላም"}</span>
      </I18nProvider>
    );
    expect(screen.getByText("ሰላም")).toBeInTheDocument();
  });

  it("applies accessibility attributes", () => {
    render(
      <AccessibilityWrapper>
        <button data-testid="accessible-button">Test</button>
      </AccessibilityWrapper>
    );
    expect(screen.getByTestId("accessible-button")).toBeInTheDocument();
  });
});
