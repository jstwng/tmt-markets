import { describe, it, expect } from "vitest";
import { TOOLS_MANIFEST, CATEGORIES } from "./tools-manifest";

describe("TOOLS_MANIFEST", () => {
  it("exports a non-empty array", () => {
    expect(Array.isArray(TOOLS_MANIFEST)).toBe(true);
    expect(TOOLS_MANIFEST.length).toBeGreaterThan(0);
  });

  it("every tool has required string fields", () => {
    for (const tool of TOOLS_MANIFEST) {
      expect(typeof tool.name).toBe("string");
      expect(tool.name.length).toBeGreaterThan(0);
      expect(typeof tool.description).toBe("string");
      expect(tool.description.length).toBeGreaterThan(0);
      expect(typeof tool.examplePrompt).toBe("string");
      expect(tool.examplePrompt.length).toBeGreaterThan(0);
      expect(typeof tool.category).toBe("string");
    }
  });

  it("every tool's category is a valid ToolCategory", () => {
    const validCategories = new Set<string>(CATEGORIES);
    for (const tool of TOOLS_MANIFEST) {
      expect(validCategories.has(tool.category)).toBe(true);
    }
  });

  it("tool names are unique", () => {
    const names = TOOLS_MANIFEST.map((t) => t.name);
    const unique = new Set(names);
    expect(unique.size).toBe(names.length);
  });

  it("every category has at least one tool", () => {
    for (const category of CATEGORIES) {
      const tools = TOOLS_MANIFEST.filter((t) => t.category === category);
      expect(tools.length).toBeGreaterThan(0);
    }
  });
});
