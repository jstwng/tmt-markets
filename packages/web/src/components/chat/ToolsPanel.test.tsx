import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ToolsPanel from "./ToolsPanel";

describe("ToolsPanel", () => {
  it("does not render panel content when closed", () => {
    render(<ToolsPanel open={false} onClose={vi.fn()} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders the panel header when open", () => {
    render(<ToolsPanel open={true} onClose={vi.fn()} />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Research Tools")).toBeInTheDocument();
  });

  it("renders all category headings when open with no search", () => {
    render(<ToolsPanel open={true} onClose={vi.fn()} />);
    expect(screen.getByText("Data")).toBeInTheDocument();
    expect(screen.getByText("Portfolio")).toBeInTheDocument();
    expect(screen.getByText("Risk")).toBeInTheDocument();
    expect(screen.getByText("Backtesting")).toBeInTheDocument();
    expect(screen.getByText("Covariance & Returns")).toBeInTheDocument();
    expect(screen.getByText("Scenarios")).toBeInTheDocument();
    expect(screen.getByText("Attribution")).toBeInTheDocument();
    expect(screen.getByText("Charts & Reports")).toBeInTheDocument();
  });

  it("renders tool names, descriptions, and example prompts", () => {
    render(<ToolsPanel open={true} onClose={vi.fn()} />);
    expect(screen.getByText("Price History")).toBeInTheDocument();
    expect(
      screen.getByText(/Fetch historical adjusted close prices/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Fetch daily prices for AAPL/)
    ).toBeInTheDocument();
  });

  it("filters tools by name when searching", () => {
    render(<ToolsPanel open={true} onClose={vi.fn()} />);
    const input = screen.getByPlaceholderText("Search tools…");
    fireEvent.change(input, { target: { value: "backtest" } });
    expect(screen.getByText("Backtest Portfolio")).toBeInTheDocument();
    expect(screen.queryByText("Price History")).not.toBeInTheDocument();
  });

  it("shows empty state when search has no matches", () => {
    render(<ToolsPanel open={true} onClose={vi.fn()} />);
    const input = screen.getByPlaceholderText("Search tools…");
    fireEvent.change(input, { target: { value: "zzznomatch" } });
    expect(screen.getByText("No tools match.")).toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", () => {
    const onClose = vi.fn();
    render(<ToolsPanel open={true} onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when backdrop is clicked", () => {
    const onClose = vi.fn();
    render(<ToolsPanel open={true} onClose={onClose} />);
    fireEvent.click(screen.getByTestId("tools-backdrop"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when Escape key is pressed", () => {
    const onClose = vi.fn();
    render(<ToolsPanel open={true} onClose={onClose} />);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("resets search query when panel closes", () => {
    const { rerender } = render(<ToolsPanel open={true} onClose={vi.fn()} />);
    const input = screen.getByPlaceholderText("Search tools…");
    fireEvent.change(input, { target: { value: "risk" } });
    expect((input as HTMLInputElement).value).toBe("risk");

    rerender(<ToolsPanel open={false} onClose={vi.fn()} />);
    rerender(<ToolsPanel open={true} onClose={vi.fn()} />);
    const freshInput = screen.getByPlaceholderText("Search tools…");
    expect((freshInput as HTMLInputElement).value).toBe("");
  });
});
