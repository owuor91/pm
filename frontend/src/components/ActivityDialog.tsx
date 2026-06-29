"use client";

import { useEffect, useState } from "react";
import { ModalShell } from "@/components/ModalShell";
import { getActivity, type ActivityEntry } from "@/lib/api";

type ActivityDialogProps = {
  boardId: number;
  onClose: () => void;
};

const describeAction = (entry: ActivityEntry): string => {
  switch (entry.action) {
    case "board_state_saved":
      return "updated the board";
    case "ai_update":
      return "used the AI assistant";
    case "member_added":
      return "added a member";
    case "member_removed":
      return "removed a member";
    case "member_left":
      return "left the board";
    default:
      return entry.action;
  }
};

export const ActivityDialog = ({ boardId, onClose }: ActivityDialogProps) => {
  const [entries, setEntries] = useState<ActivityEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    getActivity(boardId)
      .then(setEntries)
      .finally(() => setIsLoading(false));
  }, [boardId]);

  return (
    <ModalShell title="Activity" closeLabel="Close activity dialog" onClose={onClose}>
      {isLoading ? (
        <p className="mt-4 text-sm text-[var(--gray-text)]">Loading...</p>
      ) : entries.length === 0 ? (
        <p className="mt-4 text-sm text-[var(--gray-text)]">No activity yet.</p>
      ) : (
        <ul className="mt-4 max-h-[50vh] space-y-2 overflow-y-auto">
          {entries.map((entry) => (
            <li
              key={entry.id}
              className="rounded-2xl border border-[var(--stroke)] px-4 py-2 text-sm text-[var(--navy-dark)]"
            >
              <span className="font-semibold">{entry.username ?? "Someone"}</span>{" "}
              {describeAction(entry)}
              <p className="mt-1 text-xs text-[var(--gray-text)]">{entry.created_at}</p>
            </li>
          ))}
        </ul>
      )}
    </ModalShell>
  );
};
