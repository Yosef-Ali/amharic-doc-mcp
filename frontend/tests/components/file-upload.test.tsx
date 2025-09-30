import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import FileUpload from "@/components/FileUpload";

describe("FileUpload component", () => {
  it("renders dropzone text", () => {
    render(<FileUpload />);
    expect(screen.getByText(/upload documents/i)).toBeInTheDocument();
  });

  it("invokes upload handler on file drop", () => {
    const onUpload = vi.fn();
    render(<FileUpload onUpload={onUpload} />);
    const input = screen.getByTestId("file-input");

    const file = new File(["content"], "test.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [file] } });

    expect(onUpload).toHaveBeenCalled();
  });
});
