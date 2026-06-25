from backend.board_updates import apply_board_update
from backend.schemas import BoardUpdate, CardUpdate, ColumnUpdate, NewColumn


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


def test_apply_board_update_sets_due_date_and_labels():
    board = {
        "columns": [{"id": "col-todo", "title": "To Do", "cardIds": ["card-1"]}],
        "cards": {"card-1": {"id": "card-1", "title": "Old", "details": "d"}},
    }

    update = BoardUpdate(
        newCards=[
            {
                "title": "New card",
                "details": "",
                "columnId": "col-todo",
                "dueDate": "2026-07-01",
                "labels": ["bug"],
            }
        ],
        updatedCards=[CardUpdate(id="card-1", dueDate="2026-08-01", labels=["urgent"])],
    )

    next_board = apply_board_update(board, update)

    assert next_board["cards"]["card-1"]["dueDate"] == "2026-08-01"
    assert next_board["cards"]["card-1"]["labels"] == ["urgent"]

    new_card_id = next(card_id for card_id in next_board["cards"] if card_id != "card-1")
    assert next_board["cards"][new_card_id]["dueDate"] == "2026-07-01"
    assert next_board["cards"][new_card_id]["labels"] == ["bug"]


def test_priority_on_new_and_updated_cards():
    board = {
        "columns": [{"id": "col-todo", "title": "To Do", "cardIds": ["card-1"]}],
        "cards": {"card-1": {"id": "card-1", "title": "Old", "details": "d"}},
    }

    update = BoardUpdate(
        newCards=[{"title": "Urgent task", "columnId": "col-todo", "priority": "high"}],
        updatedCards=[CardUpdate(id="card-1", priority="critical")],
    )

    next_board = apply_board_update(board, update)

    assert next_board["cards"]["card-1"]["priority"] == "critical"
    new_id = next(cid for cid in next_board["cards"] if cid != "card-1")
    assert next_board["cards"][new_id]["priority"] == "high"


def test_invalid_priority_is_ignored():
    board = {
        "columns": [{"id": "col-todo", "title": "To Do", "cardIds": ["card-1"]}],
        "cards": {"card-1": {"id": "card-1", "title": "Old", "details": "d", "priority": "high"}},
    }

    update = BoardUpdate(
        updatedCards=[CardUpdate(id="card-1", priority="urgent")],
    )

    next_board = apply_board_update(board, update)
    assert "priority" not in next_board["cards"]["card-1"]


def test_add_and_delete_columns():
    board = {
        "columns": [
            {"id": "col-todo", "title": "To Do", "cardIds": ["card-1"]},
            {"id": "col-done", "title": "Done", "cardIds": []},
        ],
        "cards": {"card-1": {"id": "card-1", "title": "Task", "details": "d"}},
    }

    update = BoardUpdate(
        newColumns=[NewColumn(title="In Review")],
        deletedColumnIds=["col-done"],
    )

    next_board = apply_board_update(board, update)
    col_titles = [c["title"] for c in next_board["columns"]]
    assert "In Review" in col_titles
    assert "Done" not in col_titles
    assert len(next_board["columns"]) == 2


def test_add_column_with_explicit_id():
    board = {
        "columns": [{"id": "col-todo", "title": "To Do", "cardIds": []}],
        "cards": {},
    }

    update = BoardUpdate(
        newColumns=[NewColumn(id="col-staging", title="Staging")],
    )

    next_board = apply_board_update(board, update)
    ids = [c["id"] for c in next_board["columns"]]
    assert "col-staging" in ids
    assert len(next_board["columns"]) == 2


def test_wip_limit_set_and_clear():
    board = {
        "columns": [{"id": "col-todo", "title": "To Do", "cardIds": []}],
        "cards": {},
    }

    update = BoardUpdate(updatedColumns=[ColumnUpdate(id="col-todo", wipLimit=3)])
    next_board = apply_board_update(board, update)
    assert next_board["columns"][0]["wipLimit"] == 3

    update_clear = BoardUpdate(updatedColumns=[ColumnUpdate(id="col-todo", wipLimit=0)])
    cleared = apply_board_update(next_board, update_clear)
    assert "wipLimit" not in cleared["columns"][0]

