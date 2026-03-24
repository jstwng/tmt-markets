import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import TextBlock from "./TextBlock";

describe("TextBlock", () => {
  it("renders bold text", () => {
    render(<TextBlock text="**hello world**" />);
    const bold = screen.getByText("hello world");
    expect(bold.tagName).toBe("STRONG");
  });

  it("renders inline code", () => {
    render(<TextBlock text="call `optimize_portfolio` now" />);
    const code = screen.getByText("optimize_portfolio");
    expect(code.tagName).toBe("CODE");
  });

  it("renders bullet list", () => {
    render(<TextBlock text={"- first item\n- second item"} />);
    expect(screen.getByText("first item")).toBeInTheDocument();
    expect(screen.getByText("second item")).toBeInTheDocument();
    expect(document.querySelector("ul")).toBeInTheDocument();
  });

  it("renders numbered list", () => {
    render(<TextBlock text={"1. step one\n2. step two"} />);
    expect(screen.getByText("step one")).toBeInTheDocument();
    expect(screen.getByText("step two")).toBeInTheDocument();
    expect(document.querySelector("ol")).toBeInTheDocument();
  });

  it("renders fenced code block", () => {
    render(<TextBlock text={"```python\nprint('hello')\n```"} />);
    const pre = document.querySelector("pre");
    expect(pre).toBeInTheDocument();
    expect(pre?.textContent).toContain("print('hello')");
  });

  it("strips language hint from fenced code block", () => {
    render(<TextBlock text={"```python\nprint('hi')\n```"} />);
    const pre = document.querySelector("pre");
    expect(pre?.textContent).not.toContain("python");
  });

  it("renders unlabelled fenced code block as block", () => {
    render(<TextBlock text={"```\nraw output\n```"} />);
    const pre = document.querySelector("pre");
    expect(pre).toBeInTheDocument();
    expect(pre?.textContent).toContain("raw output");
  });

  it("renders markdown table", () => {
    const table = "| Metric | Value |\n|---|---|\n| Sharpe | 1.42 |";
    render(<TextBlock text={table} />);
    expect(document.querySelector("table")).toBeInTheDocument();
    expect(screen.getByText("Metric")).toBeInTheDocument();
    expect(screen.getByText("1.42")).toBeInTheDocument();
  });

  it("renders plain paragraph text", () => {
    render(<TextBlock text="This is a plain sentence." />);
    expect(screen.getByText("This is a plain sentence.")).toBeInTheDocument();
  });

  // --- Citation rendering tests ---

  it("renders Unicode superscript digits as styled citation markers", () => {
    render(<TextBlock text="NVDA beat estimates¹ and raised guidance²" />);
    const sups = document.querySelectorAll("sup");
    expect(sups.length).toBe(2);
    expect(sups[0].textContent).toBe("1");
    expect(sups[1].textContent).toBe("2");
  });

  it("renders grouped superscript digits as separate markers", () => {
    render(<TextBlock text="Revenue grew¹² driven by data center" />);
    const sups = document.querySelectorAll("sup");
    expect(sups.length).toBe(2);
    expect(sups[0].textContent).toBe("1");
    expect(sups[1].textContent).toBe("2");
  });

  it("does not alter text without superscript digits", () => {
    render(<TextBlock text="No citations here, just regular text." />);
    const sups = document.querySelectorAll("sup");
    expect(sups.length).toBe(0);
    expect(screen.getByText(/No citations here/)).toBeInTheDocument();
  });

  it("does not replace superscripts inside inline code", () => {
    render(<TextBlock text="Use `x¹` for exponents" />);
    const code = document.querySelector("code");
    expect(code?.textContent).toContain("¹");
    const sups = document.querySelectorAll("sup");
    expect(sups.length).toBe(0);
  });

  it("does not replace superscripts inside fenced code blocks", () => {
    render(<TextBlock text={"```\nresult = x²\n```"} />);
    const pre = document.querySelector("pre");
    expect(pre?.textContent).toContain("²");
    const sups = document.querySelectorAll("sup");
    expect(sups.length).toBe(0);
  });
});
