# Database Design for Project Management MVP

## Goals

- Define a SQLite schema for users and board state.
- Support multiple users with one board per user.
- Persist Kanban state as JSON for MVP simplicity.
- Ensure the backend can initialize the database automatically when missing.

## Schema

### users

- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `username` TEXT NOT NULL UNIQUE
- `password` TEXT NOT NULL
- `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP

Rationale: store a simple user model so the backend supports multiple users later. For MVP, the app can continue using the hardcoded credentials `user` / `password`.

### boards

- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `user_id` INTEGER NOT NULL REFERENCES users(id)
- `name` TEXT NOT NULL DEFAULT 'Default Board'
- `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
- `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP

Rationale: keep board metadata separate from the JSON blob. This allows one board per user and makes later board metadata changes easier.

### board_state

- `board_id` INTEGER PRIMARY KEY REFERENCES boards(id)
- `state` TEXT NOT NULL
- `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP

Rationale: storing the board JSON in a dedicated table keeps the state schema simple and makes updates atomic.

## Data model behavior

- Each user can have one board.
- The board state is stored as a JSON string in `board_state.state`.
- The backend can evolve the board shape without changing the SQL schema.

## Initialization strategy

- On first backend startup, create `backend/pm.db` if it does not exist.
- Create required tables using `CREATE TABLE IF NOT EXISTS`.
- Seed the database with a default user record for the MVP credentials:
  - `username`: `user`
  - `password`: `password`
- Create a default board record for the seeded user.
- Create an empty board state record if one is missing.

## File locations

- Database file: `backend/pm.db`
- Backend initialization code: `backend/db.py`
- FastAPI app entrypoint: `backend/app.py`

## Next steps

- Implement backend endpoints to read and update board state.
- Add tests for database initialization and state persistence.
- Connect the frontend login experience to the backend user model.
