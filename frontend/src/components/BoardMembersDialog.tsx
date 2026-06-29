"use client";

import { useEffect, useState, type FormEvent } from "react";
import { ModalShell } from "@/components/ModalShell";
import {
  addBoardMember,
  listBoardMembers,
  removeBoardMember,
  type BoardMember,
  type BoardRole,
} from "@/lib/api";

type BoardMembersDialogProps = {
  boardId: number;
  role: BoardRole;
  onClose: () => void;
};

export const BoardMembersDialog = ({ boardId, role, onClose }: BoardMembersDialogProps) => {
  const [members, setMembers] = useState<BoardMember[]>([]);
  const [username, setUsername] = useState("");
  const [memberRole, setMemberRole] = useState<BoardRole>("editor");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  const refresh = () => {
    setIsLoading(true);
    listBoardMembers(boardId)
      .then(setMembers)
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [boardId]);

  const handleAdd = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!username.trim()) return;
    setError("");
    try {
      await addBoardMember(boardId, username.trim(), memberRole);
      setUsername("");
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add member.");
    }
  };

  const handleRemove = async (userId: number) => {
    setError("");
    try {
      await removeBoardMember(boardId, userId);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove member.");
    }
  };

  const ownerCount = members.filter((member) => member.role === "owner").length;

  return (
    <ModalShell title="Board members" closeLabel="Close board members dialog" onClose={onClose}>
      {isLoading ? (
        <p className="mt-4 text-sm text-[var(--gray-text)]">Loading...</p>
      ) : (
        <ul className="mt-4 space-y-2">
          {members.map((member) => (
            <li
              key={member.user_id}
              className="flex items-center justify-between rounded-2xl border border-[var(--stroke)] px-4 py-2 text-sm"
            >
              <span className="font-semibold text-[var(--navy-dark)]">
                {member.username}{" "}
                <span className="font-normal text-[var(--gray-text)]">({member.role})</span>
              </span>
              {role === "owner" && (member.role !== "owner" || ownerCount > 1) ? (
                <button
                  type="button"
                  onClick={() => handleRemove(member.user_id)}
                  className="text-xs font-semibold uppercase tracking-wide text-red-600 hover:underline"
                >
                  Remove
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      {role === "owner" ? (
        <form onSubmit={handleAdd} className="mt-5 flex flex-wrap items-center gap-2">
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            placeholder="Username"
            aria-label="Username to add"
            className="min-w-0 flex-1 rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm outline-none focus:border-[var(--primary-blue)]"
          />
          <select
            value={memberRole}
            onChange={(event) => setMemberRole(event.target.value as BoardRole)}
            aria-label="Member role"
            className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm outline-none focus:border-[var(--primary-blue)]"
          >
            <option value="editor">editor</option>
            <option value="owner">owner</option>
          </select>
          <button
            type="submit"
            className="rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white"
          >
            Add
          </button>
        </form>
      ) : null}
      {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
    </ModalShell>
  );
};
