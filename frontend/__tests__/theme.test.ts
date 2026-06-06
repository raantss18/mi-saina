import { describe, it, expect, beforeEach, vi } from "vitest";
import { nextTheme, readTheme, applyTheme, THEME_KEY } from "../lib/theme";

describe("nextTheme", () => {
  it("cycles auto → light → dark → auto", () => {
    expect(nextTheme("auto")).toBe("light");
    expect(nextTheme("light")).toBe("dark");
    expect(nextTheme("dark")).toBe("auto");
  });
});

describe("readTheme / applyTheme", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
  });

  it("defaults to auto when nothing is stored", () => {
    expect(readTheme()).toBe("auto");
  });

  it("reads a stored explicit theme", () => {
    localStorage.setItem(THEME_KEY, "dark");
    expect(readTheme()).toBe("dark");
  });

  it("ignores an invalid stored value", () => {
    localStorage.setItem(THEME_KEY, "neon");
    expect(readTheme()).toBe("auto");
  });

  it("applyTheme sets the attribute and persists for explicit themes", () => {
    applyTheme("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    expect(localStorage.getItem(THEME_KEY)).toBe("light");
  });

  it("applyTheme('auto') clears the attribute and the stored key", () => {
    applyTheme("dark");
    applyTheme("auto");
    expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
    expect(localStorage.getItem(THEME_KEY)).toBeNull();
  });
});
