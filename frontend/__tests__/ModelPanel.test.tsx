import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ModelPanel from "../components/ModelPanel";

const mockModels = [
  { name: "qwen3.5:9b", size_gb: 5.2, modified: "2024-01-01T00:00:00Z", active: true },
  { name: "deepseek-r1:8b", size_gb: 4.8, modified: "2024-01-01T00:00:00Z", active: false },
];

beforeEach(() => {
  vi.clearAllMocks();
});

function mockFetch(data: unknown, ok = true) {
  (global as any).fetch = vi.fn().mockResolvedValue({
    ok,
    json: vi.fn().mockResolvedValue(data),
  });
}

describe("ModelPanel — loading state", () => {
  it("shows the loading state before fetch resolves", () => {
    // Use a fetch that never resolves during this check
    (global as any).fetch = vi.fn().mockReturnValue(new Promise(() => {}));
    render(<ModelPanel onModelChange={() => {}} />);
    expect(screen.getByText(/Loading models/)).toBeInTheDocument();
  });
});

describe("ModelPanel — model list", () => {
  it("renders model labels after successful fetch", async () => {
    mockFetch(mockModels);
    render(<ModelPanel onModelChange={() => {}} />);
    await waitFor(() => {
      expect(screen.getByText("Qwen 3.5 9B")).toBeInTheDocument();
    });
    expect(screen.getByText("DeepSeek R1 8B")).toBeInTheDocument();
  });

  it("shows ACTIF badge for the active model", async () => {
    mockFetch(mockModels);
    render(<ModelPanel onModelChange={() => {}} />);
    await waitFor(() => {
      expect(screen.getByText("ACTIVE")).toBeInTheDocument();
    });
  });

  it("shows model size in GB", async () => {
    mockFetch(mockModels);
    render(<ModelPanel onModelChange={() => {}} />);
    await waitFor(() => {
      expect(screen.getByText("5.2GB")).toBeInTheDocument();
    });
    expect(screen.getByText("4.8GB")).toBeInTheDocument();
  });

  it("shows Activate button for inactive model only", async () => {
    mockFetch(mockModels);
    render(<ModelPanel onModelChange={() => {}} />);
    await waitFor(() => {
      expect(screen.getByText("DeepSeek R1 8B")).toBeInTheDocument();
    });
    // Only one "Activer" button (for the inactive model)
    expect(screen.getAllByText("Activate")).toHaveLength(1);
  });

  it("does not show Activate button for the active model", async () => {
    mockFetch([{ name: "qwen3.5:9b", size_gb: 5.2, modified: "", active: true }]);
    render(<ModelPanel onModelChange={() => {}} />);
    await waitFor(() => {
      expect(screen.getByText("Qwen 3.5 9B")).toBeInTheDocument();
    });
    expect(screen.queryByText("Activate")).toBeNull();
  });

  it("shows delete button for inactive models", async () => {
    mockFetch(mockModels);
    render(<ModelPanel onModelChange={() => {}} />);
    await waitFor(() => {
      expect(screen.getByText("DeepSeek R1 8B")).toBeInTheDocument();
    });
    // Delete button (🗑) exists for the inactive model
    expect(screen.getByTitle("Delete this model")).toBeInTheDocument();
  });

  it("does not show delete button for the active model", async () => {
    mockFetch([{ name: "qwen3.5:9b", size_gb: 5.2, modified: "", active: true }]);
    render(<ModelPanel onModelChange={() => {}} />);
    await waitFor(() => {
      expect(screen.getByText("Qwen 3.5 9B")).toBeInTheDocument();
    });
    expect(screen.queryByTitle("Supprimer ce modèle")).toBeNull();
  });

  it("renders tags for known models", async () => {
    mockFetch([{ name: "deepseek-r1:8b", size_gb: 4.8, modified: "", active: false }]);
    render(<ModelPanel onModelChange={() => {}} />);
    await waitFor(() => {
      expect(screen.getByText("raisonnement")).toBeInTheDocument();
    });
    expect(screen.getByText("8B")).toBeInTheDocument();
  });

  it("uses model name as label for unknown models", async () => {
    mockFetch([{ name: "unknown-model:3b", size_gb: 2.0, modified: "", active: false }]);
    render(<ModelPanel onModelChange={() => {}} />);
    await waitFor(() => {
      expect(screen.getByText("Unknown-model 3B")).toBeInTheDocument();
    });
  });
});

describe("ModelPanel — error state", () => {
  it("shows error message when backend is unreachable", async () => {
    (global as any).fetch = vi.fn().mockRejectedValue(new Error("Network error"));
    render(<ModelPanel onModelChange={() => {}} />);
    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });
});

describe("ModelPanel — model activation", () => {
  it("calls onModelChange with model name when Activer is clicked", async () => {
    const onModelChange = vi.fn();
    mockFetch(mockModels);
    render(<ModelPanel onModelChange={onModelChange} />);
    await waitFor(() => screen.getByText("Activate"));
    fireEvent.click(screen.getByText("Activate"));
    await waitFor(() => {
      expect(onModelChange).toHaveBeenCalledWith("deepseek-r1:8b");
    });
  });

  it("calls fetch POST /models/select when Activer is clicked", async () => {
    mockFetch(mockModels);
    render(<ModelPanel onModelChange={() => {}} />);
    await waitFor(() => screen.getByText("Activate"));
    fireEvent.click(screen.getByText("Activate"));
    await waitFor(() => {
      const calls = (global as any).fetch.mock.calls;
      const selectCall = calls.find((c: unknown[]) =>
        typeof c[0] === "string" && c[0].includes("/models/select")
      );
      expect(selectCall).toBeDefined();
    });
  });
});

describe("ModelPanel — pull new model", () => {
  it("shows pull input and button", async () => {
    mockFetch([]);
    render(<ModelPanel onModelChange={() => {}} />);
    await waitFor(() => {
      expect(
        screen.getByPlaceholderText(/phi4-mini/)
      ).toBeInTheDocument();
    });
    expect(screen.getByText("↓ Download")).toBeInTheDocument();
  });

  it("Pull button is disabled when input is empty", async () => {
    mockFetch([]);
    render(<ModelPanel onModelChange={() => {}} />);
    await waitFor(() => screen.getByText("↓ Download"));
    expect(screen.getByText("↓ Download")).toBeDisabled();
  });

  it("Pull button is enabled when input has text", async () => {
    mockFetch([]);
    render(<ModelPanel onModelChange={() => {}} />);
    await waitFor(() => screen.getByPlaceholderText(/phi4-mini/));
    const input = screen.getByPlaceholderText(/phi4-mini/);
    fireEvent.change(input, { target: { value: "llama3.2:3b" } });
    expect(screen.getByText("↓ Download")).not.toBeDisabled();
  });
});

describe("ModelPanel — update (↻) button", () => {
  it("shows update button for each model", async () => {
    mockFetch(mockModels);
    render(<ModelPanel onModelChange={() => {}} />);
    await waitFor(() => screen.getByText("Qwen 3.5 9B"));
    const updateButtons = screen.getAllByTitle(
      "Check and download updates"
    );
    expect(updateButtons).toHaveLength(2);
  });
});
