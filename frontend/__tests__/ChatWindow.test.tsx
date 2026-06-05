import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ChatWindow, { Message } from "../components/ChatWindow";

describe("ChatWindow — empty state", () => {
  it("shows empty-state text when no messages", () => {
    render(<ChatWindow messages={[]} />);
    expect(screen.getByText("mi-saina prêt")).toBeInTheDocument();
  });

  it("shows empty-state subtext", () => {
    render(<ChatWindow messages={[]} />);
    expect(
      screen.getByText(/Commandes exécutées en direct/)
    ).toBeInTheDocument();
  });

  it("does not show empty state when messages exist", () => {
    const messages: Message[] = [{ role: "user", content: "Hello" }];
    render(<ChatWindow messages={messages} />);
    expect(screen.queryByText("mi-saina prêt")).toBeNull();
  });
});

describe("ChatWindow — user messages", () => {
  it("renders user message content", () => {
    const messages: Message[] = [{ role: "user", content: "Hello world!" }];
    render(<ChatWindow messages={messages} />);
    expect(screen.getByText("Hello world!")).toBeInTheDocument();
  });

  it("renders multiple user messages", () => {
    const messages: Message[] = [
      { role: "user", content: "First message" },
      { role: "user", content: "Second message" },
    ];
    render(<ChatWindow messages={messages} />);
    expect(screen.getByText("First message")).toBeInTheDocument();
    expect(screen.getByText("Second message")).toBeInTheDocument();
  });
});

describe("ChatWindow — assistant messages", () => {
  it("renders assistant message content", () => {
    const messages: Message[] = [
      { role: "assistant", content: "I can help with that." },
    ];
    render(<ChatWindow messages={messages} />);
    expect(screen.getByText("I can help with that.")).toBeInTheDocument();
  });

  it("shows model attribution when model is set", () => {
    const messages: Message[] = [
      { role: "assistant", content: "Response text", model: "qwen3.5:9b" },
    ];
    render(<ChatWindow messages={messages} />);
    expect(screen.getByText("qwen3.5:9b")).toBeInTheDocument();
  });

  it("does not show model attribution when model is not set", () => {
    const messages: Message[] = [
      { role: "assistant", content: "Response text" },
    ];
    render(<ChatWindow messages={messages} />);
    expect(screen.queryByText("qwen3.5:9b")).toBeNull();
  });

  it("shows streaming cursor when streaming is true", () => {
    const messages: Message[] = [
      { role: "assistant", content: "Loading...", streaming: true },
    ];
    render(<ChatWindow messages={messages} />);
    // The cursor ▋ should be present
    expect(screen.getByText("▋")).toBeInTheDocument();
  });

  it("does not show streaming cursor when streaming is false", () => {
    const messages: Message[] = [
      { role: "assistant", content: "Done", streaming: false },
    ];
    render(<ChatWindow messages={messages} />);
    expect(screen.queryByText("▋")).toBeNull();
  });
});

describe("ChatWindow — shell stream blocks", () => {
  it("renders shell block command with dollar prefix", () => {
    const messages: Message[] = [
      {
        role: "shell",
        content: "file.txt",
        command: "ls -la",
        shellDone: true,
        returncode: 0,
      },
    ];
    render(<ChatWindow messages={messages} />);
    expect(screen.getByText("$ ls -la")).toBeInTheDocument();
  });

  it("shows success indicator when returncode is 0", () => {
    const messages: Message[] = [
      {
        role: "shell",
        content: "output",
        command: "echo ok",
        shellDone: true,
        returncode: 0,
      },
    ];
    render(<ChatWindow messages={messages} />);
    expect(screen.getByText("succès")).toBeInTheDocument();
  });

  it("shows failure indicator when returncode is non-zero", () => {
    const messages: Message[] = [
      {
        role: "shell",
        content: "error",
        command: "bad-cmd",
        shellDone: true,
        returncode: 127,
      },
    ];
    render(<ChatWindow messages={messages} />);
    expect(screen.getByText("rc=127")).toBeInTheDocument();
  });

  it("shows running indicator when shell is streaming", () => {
    const messages: Message[] = [
      {
        role: "shell",
        content: "...",
        command: "long-cmd",
        shellStreaming: true,
        shellDone: false,
      },
    ];
    render(<ChatWindow messages={messages} />);
    expect(screen.getByText("en cours...")).toBeInTheDocument();
  });

  it("does NOT render raw terminal output in chat (details live in the Terminal panel)", () => {
    const messages: Message[] = [
      {
        role: "shell",
        content: "line1\nline2\nline3",
        command: "cat file.txt",
        shellDone: true,
        returncode: 0,
      },
    ];
    render(<ChatWindow messages={messages} />);
    // La sortie brute ne doit plus apparaître dans le chat…
    expect(screen.queryByText(/line1/)).toBeNull();
    // …seulement un résumé d'état lisible.
    expect(screen.getByText(/Commande terminée/)).toBeInTheDocument();
  });

  it("shows a compact failure summary instead of the raw error", () => {
    const messages: Message[] = [
      {
        role: "shell",
        content: "",
        command: "fail",
        shellDone: true,
        returncode: -1,
        error: "Command not found",
      },
    ];
    render(<ChatWindow messages={messages} />);
    // L'erreur brute n'est plus affichée dans le chat…
    expect(screen.queryByText("Command not found")).toBeNull();
    // …mais un résumé pointant le panneau Terminal l'est.
    expect(screen.getByText(/Échec/)).toBeInTheDocument();
  });

  it("shows interactive input controls when waitingInput is true", () => {
    const messages: Message[] = [
      {
        role: "shell",
        content: "Continue? [Y/n]",
        command: "install-pkg",
        shellStreaming: true,
        shellDone: false,
        waitingInput: true,
      },
    ];
    render(<ChatWindow messages={messages} onShellInput={() => {}} />);
    expect(screen.getByTitle("Répondre Oui")).toBeInTheDocument();
    expect(screen.getByTitle("Répondre Non")).toBeInTheDocument();
  });

  it("calls onShellInput with 'y' when Y button clicked", () => {
    const onShellInput = vi.fn();
    const messages: Message[] = [
      {
        role: "shell",
        content: "Continue?",
        command: "install",
        shellStreaming: true,
        shellDone: false,
        waitingInput: true,
      },
    ];
    render(<ChatWindow messages={messages} onShellInput={onShellInput} />);
    fireEvent.click(screen.getByTitle("Répondre Oui"));
    expect(onShellInput).toHaveBeenCalledWith("y");
  });

  it("calls onShellInput with 'n' when N button clicked", () => {
    const onShellInput = vi.fn();
    const messages: Message[] = [
      {
        role: "shell",
        content: "Continue?",
        command: "install",
        shellStreaming: true,
        shellDone: false,
        waitingInput: true,
      },
    ];
    render(<ChatWindow messages={messages} onShellInput={onShellInput} />);
    fireEvent.click(screen.getByTitle("Répondre Non"));
    expect(onShellInput).toHaveBeenCalledWith("n");
  });

  it("calls onShellInput with '' when Enter button clicked", () => {
    const onShellInput = vi.fn();
    const messages: Message[] = [
      {
        role: "shell",
        content: "Continue?",
        command: "install",
        shellStreaming: true,
        shellDone: false,
        waitingInput: true,
      },
    ];
    render(<ChatWindow messages={messages} onShellInput={onShellInput} />);
    fireEvent.click(screen.getByTitle("Envoyer Entrée vide"));
    expect(onShellInput).toHaveBeenCalledWith("");
  });
});

describe("ChatWindow — attachments", () => {
  it("renders image attachment badge", () => {
    const messages: Message[] = [
      {
        role: "user",
        content: "Look at this",
        attachments: [{ type: "image", name: "photo.png" }],
      },
    ];
    render(<ChatWindow messages={messages} />);
    expect(screen.getByText(/photo\.png/)).toBeInTheDocument();
  });

  it("renders text file attachment badge", () => {
    const messages: Message[] = [
      {
        role: "user",
        content: "Analyze this",
        attachments: [{ type: "text", name: "notes.txt" }],
      },
    ];
    render(<ChatWindow messages={messages} />);
    expect(screen.getByText(/notes\.txt/)).toBeInTheDocument();
  });
});

describe("ChatWindow — plan messages", () => {
  it("renders plan message content", () => {
    const messages = [
      { role: "plan" as any, content: "Step 1: Find files\nStep 2: Process" },
    ] as Message[];
    render(<ChatWindow messages={messages} />);
    expect(screen.getByText(/Step 1: Find files/)).toBeInTheDocument();
  });
});
