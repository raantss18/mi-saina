import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ShellOutput from "../components/ShellOutput";

const makeEntry = (command: string, output: string, status = "ok") => ({
  command,
  output,
  status,
  timestamp: new Date().toISOString(),
});

describe("ShellOutput", () => {
  it("renders nothing when entries array is empty", () => {
    const { container } = render(<ShellOutput entries={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("shows SHELL header label", () => {
    render(<ShellOutput entries={[makeEntry("ls", "output")]} />);
    expect(screen.getByText("SHELL")).toBeInTheDocument();
  });

  it("displays command with dollar-sign prefix", () => {
    render(<ShellOutput entries={[makeEntry("ls -la", "total 8")]} />);
    expect(screen.getByText("$ ls -la")).toBeInTheDocument();
  });

  it("displays command output", () => {
    render(<ShellOutput entries={[makeEntry("echo hello", "hello")]} />);
    expect(screen.getByText("hello")).toBeInTheDocument();
  });

  it("renders multiple entries", () => {
    const entries = [
      makeEntry("cmd1", "output1"),
      makeEntry("cmd2", "output2"),
    ];
    render(<ShellOutput entries={entries} />);
    expect(screen.getByText("$ cmd1")).toBeInTheDocument();
    expect(screen.getByText("$ cmd2")).toBeInTheDocument();
  });

  it("shows at most the last 5 entries when given more than 5", () => {
    const entries = Array.from({ length: 10 }, (_, i) =>
      makeEntry(`cmd${i}`, `output${i}`)
    );
    render(<ShellOutput entries={entries} />);
    // First 5 entries should not appear
    expect(screen.queryByText("$ cmd0")).toBeNull();
    expect(screen.queryByText("$ cmd4")).toBeNull();
    // Last 5 entries should appear
    expect(screen.getByText("$ cmd5")).toBeInTheDocument();
    expect(screen.getByText("$ cmd9")).toBeInTheDocument();
  });

  it("renders exactly 5 entries when given exactly 5", () => {
    const entries = Array.from({ length: 5 }, (_, i) =>
      makeEntry(`cmd${i}`, `out${i}`)
    );
    render(<ShellOutput entries={entries} />);
    entries.forEach((_, i) => {
      expect(screen.getByText(`$ cmd${i}`)).toBeInTheDocument();
    });
  });

  it("renders ok and error status entries together", () => {
    const entries = [
      makeEntry("good-cmd", "success output", "ok"),
      makeEntry("bad-cmd", "error output", "error"),
    ];
    render(<ShellOutput entries={entries} />);
    expect(screen.getByText("success output")).toBeInTheDocument();
    expect(screen.getByText("error output")).toBeInTheDocument();
  });
});
