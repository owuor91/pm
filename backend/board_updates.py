from __future__ import annotations

import copy
from typing import Any
from uuid import uuid4

from backend.schemas import BoardUpdate, NewCard


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

    if update.updatedColumns:
        for column_update in update.updatedColumns:
            column = column_by_id.get(column_update.id)
            if column is None:
                continue
            if column_update.title is not None:
                column["title"] = column_update.title

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

            if card_update.columnId and card_update.columnId in column_by_id:
                for column in column_by_id.values():
                    column["cardIds"] = [card_id for card_id in column["cardIds"] if card_id != card_update.id]
                target = column_by_id[card_update.columnId]
                if card_update.id not in target["cardIds"]:
                    target["cardIds"].append(card_update.id)

    if update.newCards:
        for new_card in update.newCards:
            title = new_card.title.strip()
            if not title:
                continue

            column_id = new_card.columnId
            if column_id not in column_by_id:
                continue

            card_id = new_card.id
            if not card_id or card_id in cards:
                card_id = f"ai-{uuid4().hex[:12]}"
                while card_id in cards:
                    card_id = f"ai-{uuid4().hex[:12]}"

            details = (new_card.details or "").strip() or "No details yet."
            cards[card_id] = {"id": card_id, "title": title, "details": details}

            target = column_by_id[column_id]
            if card_id not in target["cardIds"]:
                target["cardIds"].append(card_id)

    result["columns"] = columns
    result["cards"] = cards
    return result

