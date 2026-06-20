from backend.board_updates import apply_board_update
from backend.schemas import BoardUpdate, CardUpdate, ColumnUpdate


def test_apply_board_update_creates_card_and_moves_updates_and_deletes():
    board = {
        "columns": [
            {"id": "col-todo", "title": "To Do", "cardIds": ["card-1"]},
            {"id": "col-done", "title": "Done", "cardIds": []},
        ],
        "cards": {
            "card-1": {"id": "card-1", "title": "Old", "details": "d"},
            "card-2": {"id": "card-2", "title": "Delete", "details": "d"},
        },
    }

    update = BoardUpdate(
        newCards=[{"title": "New card", "details": "", "columnId": "col-done"}],
        updatedCards=[CardUpdate(id="card-1", title="Renamed", columnId="col-done")],
        deletedCardIds=["card-2"],
        updatedColumns=[ColumnUpdate(id="col-todo", title="Backlog")],
    )

    next_board = apply_board_update(board, update)

    assert next_board["columns"][0]["title"] == "Backlog"
    assert "card-2" not in next_board["cards"]
    assert "card-2" not in next_board["columns"][0]["cardIds"]
    assert "card-1" in next_board["columns"][1]["cardIds"]
    assert next_board["cards"]["card-1"]["title"] == "Renamed"

    created_ids = [card_id for card_id in next_board["cards"].keys() if card_id not in {"card-1"}]
    assert len(created_ids) == 1
    assert created_ids[0] in next_board["columns"][1]["cardIds"]
    assert next_board["cards"][created_ids[0]]["title"] == "New card"

