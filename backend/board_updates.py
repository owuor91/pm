from __future__ import annotations

import copy
from typing import Any
from uuid import uuid4

from backend.schemas import VALID_PRIORITIES, BoardUpdate, NewCard


def _unique_id(existing: set[str], prefix: str) -> str:
    candidate = f"{prefix}-{uuid4().hex[:12]}"
    while candidate in existing:
        candidate = f"{prefix}-{uuid4().hex[:12]}"
    return candidate


def apply_board_update(board_state: dict[str, Any], update: BoardUpdate) -> dict[str, Any]:
    result = copy.deepcopy(board_state)
    columns = result.get("columns")
    cards = result.get("cards")

    if not isinstance(columns, list):
        columns = []
    if not isinstance(cards, dict):
        cards = {}

    column_by_id: dict[str, dict[str, Any]] = {}
    for column in columns:
        if isinstance(column, dict) and isinstance(column.get("id"), str):
            column_by_id[column["id"]] = column
            if not isinstance(column.get("cardIds"), list):
                column["cardIds"] = []

    if update.newColumns:
        existing_col_ids = set(column_by_id.keys())
        for new_col in update.newColumns:
            title = (new_col.title or "").strip() or "New Column"
            col_id = new_col.id
            if not col_id or col_id in existing_col_ids:
                col_id = _unique_id(existing_col_ids, "col")
            existing_col_ids.add(col_id)
            col: dict[str, Any] = {"id": col_id, "title": title, "cardIds": []}
            columns.append(col)
            column_by_id[col_id] = col

    if update.deletedColumnIds:
        deleted_cols = set(update.deletedColumnIds)
        columns[:] = [col for col in columns if col.get("id") not in deleted_cols]
        for col_id in deleted_cols:
            column_by_id.pop(col_id, None)

    if update.updatedColumns:
        for column_update in update.updatedColumns:
            column = column_by_id.get(column_update.id)
            if column is None:
                continue
            if column_update.title is not None:
                column["title"] = column_update.title
            if column_update.wipLimit is not None:
                if column_update.wipLimit > 0:
                    column["wipLimit"] = column_update.wipLimit
                else:
                    column.pop("wipLimit", None)

    if update.deletedCardIds:
        deleted = set(update.deletedCardIds)
        for card_id in deleted:
            cards.pop(card_id, None)
        for column in column_by_id.values():
            column["cardIds"] = [card_id for card_id in column["cardIds"] if card_id not in deleted]

    if update.updatedCards:
        for card_update in update.updatedCards:
            card = cards.get(card_update.id)
            if not isinstance(card, dict):
                continue

            if card_update.title is not None:
                card["title"] = card_update.title
            if card_update.details is not None:
                card["details"] = card_update.details
            if card_update.dueDate is not None:
                card["dueDate"] = card_update.dueDate
            if card_update.labels is not None:
                card["labels"] = card_update.labels
            if card_update.priority is not None:
                if card_update.priority in VALID_PRIORITIES:
                    card["priority"] = card_update.priority
                else:
                    card.pop("priority", None)

            if card_update.columnId and card_update.columnId in column_by_id:
                for column in column_by_id.values():
                    column["cardIds"] = [card_id for card_id in column["cardIds"] if card_id != card_update.id]
                target = column_by_id[card_update.columnId]
                if card_update.id not in target["cardIds"]:
                    target["cardIds"].append(card_update.id)

    if update.newCards:
        existing_card_ids = set(cards.keys())
        for new_card in update.newCards:
            title = new_card.title.strip()
            if not title:
                continue

            column_id = new_card.columnId
            if column_id not in column_by_id:
                continue

            card_id = new_card.id
            if not card_id or card_id in existing_card_ids:
                card_id = _unique_id(existing_card_ids, "ai")
            existing_card_ids.add(card_id)

            details = (new_card.details or "").strip() or "No details yet."
            card: dict[str, Any] = {"id": card_id, "title": title, "details": details}
            if new_card.dueDate is not None:
                card["dueDate"] = new_card.dueDate
            if new_card.labels is not None:
                card["labels"] = new_card.labels
            if new_card.priority is not None and new_card.priority in VALID_PRIORITIES:
                card["priority"] = new_card.priority
            cards[card_id] = card

            target = column_by_id[column_id]
            if card_id not in target["cardIds"]:
                target["cardIds"].append(card_id)

    result["columns"] = columns
    result["cards"] = cards
    return result

