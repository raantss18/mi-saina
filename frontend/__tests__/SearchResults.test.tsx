import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import SearchResults from "../components/SearchResults";

const results = [
  { title: "Result One", url: "https://example.com", snippet: "First snippet" },
  { title: "Result Two", url: "https://example2.com", snippet: "Second snippet" },
];

describe("SearchResults", () => {
  it("renders nothing when results array is empty", () => {
    const { container } = render(
      <SearchResults results={[]} query="test" onClose={() => {}} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("displays the search query in the header", () => {
    render(<SearchResults results={results} query="Paris weather" onClose={() => {}} />);
    expect(screen.getByText(/RÉSULTATS: Paris weather/)).toBeInTheDocument();
  });

  it("renders each result title as a link", () => {
    render(<SearchResults results={results} query="test" onClose={() => {}} />);
    expect(screen.getByRole("link", { name: "Result One" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Result Two" })).toBeInTheDocument();
  });

  it("renders correct href for each result", () => {
    render(<SearchResults results={results} query="test" onClose={() => {}} />);
    expect(screen.getByRole("link", { name: "Result One" })).toHaveAttribute(
      "href",
      "https://example.com"
    );
  });

  it("opens links in a new tab", () => {
    render(<SearchResults results={results} query="test" onClose={() => {}} />);
    const link = screen.getByRole("link", { name: "Result One" });
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("renders each result URL as visible text", () => {
    render(<SearchResults results={results} query="test" onClose={() => {}} />);
    expect(screen.getByText("https://example.com")).toBeInTheDocument();
    expect(screen.getByText("https://example2.com")).toBeInTheDocument();
  });

  it("renders each result snippet", () => {
    render(<SearchResults results={results} query="test" onClose={() => {}} />);
    expect(screen.getByText("First snippet")).toBeInTheDocument();
    expect(screen.getByText("Second snippet")).toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", () => {
    const onClose = vi.fn();
    render(<SearchResults results={results} query="test" onClose={onClose} />);
    fireEvent.click(screen.getByText("✕"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("renders a single result correctly", () => {
    const single = [{ title: "Only Result", url: "https://only.com", snippet: "Only snippet" }];
    render(<SearchResults results={single} query="only" onClose={() => {}} />);
    expect(screen.getByText("Only Result")).toBeInTheDocument();
    expect(screen.getByText("Only snippet")).toBeInTheDocument();
  });
});
