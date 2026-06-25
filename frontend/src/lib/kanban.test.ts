import { exportBoardToCsv, moveCard, type BoardData, type Column } from "@/lib/kanban";

describe("moveCard", () => {
  const baseColumns: Column[] = [
    { id: "col-a", title: "A", cardIds: ["card-1", "card-2"] },
    { id: "col-b", title: "B", cardIds: ["card-3"] },
  ];

  it("reorders cards in the same column", () => {
    const result = moveCard(baseColumns, "card-2", "card-1");
    expect(result[0].cardIds).toEqual(["card-2", "card-1"]);
  });

  it("moves cards to another column", () => {
    const result = moveCard(baseColumns, "card-2", "card-3");
    expect(result[0].cardIds).toEqual(["card-1"]);
    expect(result[1].cardIds).toEqual(["card-2", "card-3"]);
  });

  it("drops cards to the end of a column", () => {
    const result = moveCard(baseColumns, "card-1", "col-b");
    expect(result[0].cardIds).toEqual(["card-2"]);
    expect(result[1].cardIds).toEqual(["card-3", "card-1"]);
  });
});

import { vi } from "vitest";

describe("exportBoardToCsv", () => {
  const board: BoardData = {
    columns: [
      { id: "col-todo", title: "To Do", cardIds: ["card-1", "card-2"] },
      { id: "col-done", title: "Done", cardIds: [] },
    ],
    cards: {
      "card-1": { id: "card-1", title: "Fix bug", details: "urgent", priority: "high", labels: ["backend"], dueDate: "2026-07-01" },
      "card-2": { id: "card-2", title: 'Card with "quotes"', details: "details with, comma", labels: [], dueDate: undefined },
    },
  };

  let capturedDownload = "";
  let capturedBlobContent = "";

  beforeEach(() => {
    const mockLink = { href: "", download: "", click: vi.fn() } as unknown as HTMLAnchorElement;
    vi.spyOn(document, "createElement").mockReturnValue(mockLink);
    Object.defineProperty(mockLink, "download", {
      set(v: string) { capturedDownload = v; },
      get() { return capturedDownload; },
      configurable: true,
    });

    const OrigBlob = global.Blob;
    global.Blob = class MockBlob extends OrigBlob {
      constructor(parts: BlobPart[], opts?: BlobPropertyBag) {
        super(parts, opts);
        capturedBlobContent = parts.join("");
      }
    } as typeof Blob;

    (global as Record<string, unknown>).URL = {
      createObjectURL: vi.fn().mockReturnValue("blob:mock"),
      revokeObjectURL: vi.fn(),
    };
  });

  afterEach(() => {
    vi.restoreAllMocks();
    delete (global as Record<string, unknown>).URL;
  });

  it("generates CSV with header and one row per card", () => {
    exportBoardToCsv(board, "My Board");
    const lines = capturedBlobContent.split("\n");
    expect(lines[0]).toBe("Column,Title,Details,Priority,Labels,Due Date");
    expect(lines).toHaveLength(3);
    expect(lines[1]).toContain("Fix bug");
    expect(lines[1]).toContain("high");
    expect(lines[2]).toContain('"Card with ""quotes"""');
  });

  it("sanitizes board name for the download filename", () => {
    exportBoardToCsv(board, "Q3 Roadmap!");
    expect(capturedDownload).toBe("Q3_Roadmap__export.csv");
  });
});
