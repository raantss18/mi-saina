import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import CommandPalette, { Command } from "../components/CommandPalette";

const make = (run = vi.fn()): Command[] => [
  { id: "new", icon: "✏", label: "Nouvelle conversation", run },
  { id: "term", icon: "▣", label: "Afficher le terminal", keywords: "shell", run },
  { id: "cfg", icon: "⚙", label: "Ouvrir Config", hint: "réglages", run },
];

describe("CommandPalette", () => {
  it("renders nothing when closed", () => {
    const { container } = render(
      <CommandPalette open={false} commands={make()} onClose={() => {}} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("lists all commands when open", () => {
    render(<CommandPalette open commands={make()} onClose={() => {}} />);
    expect(screen.getByText("Nouvelle conversation")).toBeInTheDocument();
    expect(screen.getByText("Ouvrir Config")).toBeInTheDocument();
  });

  it("filters by label, keyword and hint", () => {
    render(<CommandPalette open commands={make()} onClose={() => {}} />);
    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "shell" } });
    expect(screen.getByText("Afficher le terminal")).toBeInTheDocument();
    expect(screen.queryByText("Nouvelle conversation")).not.toBeInTheDocument();
  });

  it("runs the selected command on Enter and closes", () => {
    const run = vi.fn();
    const onClose = vi.fn();
    render(<CommandPalette open commands={make(run)} onClose={onClose} />);
    fireEvent.keyDown(screen.getByRole("textbox"), { key: "Enter" });
    expect(run).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("closes on Escape without running", () => {
    const run = vi.fn();
    const onClose = vi.fn();
    render(<CommandPalette open commands={make(run)} onClose={onClose} />);
    fireEvent.keyDown(screen.getByRole("textbox"), { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(run).not.toHaveBeenCalled();
  });

  it("runs a command on click", () => {
    const run = vi.fn();
    const onClose = vi.fn();
    render(<CommandPalette open commands={make(run)} onClose={onClose} />);
    fireEvent.click(screen.getByText("Ouvrir Config"));
    expect(run).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("shows an empty state when nothing matches", () => {
    render(<CommandPalette open commands={make()} onClose={() => {}} />);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "zzzzz" } });
    // langue par défaut = anglais (i18n)
    expect(screen.getByText(/No action matches/)).toBeInTheDocument();
  });
});
