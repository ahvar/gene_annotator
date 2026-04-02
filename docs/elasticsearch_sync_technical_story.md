# Keeping SQLAlchemy + Elasticsearch in Sync in Gene Annotator

## A technical story you can rehearse aloud

> **Audience:** engineers who know Flask/SQLAlchemy and want to understand the indexing lifecycle.
>
> **Format:** spoken script with cues, as if you are presenting at a whiteboard.

---

## Scene 1 — The core idea

**Speaker:**

“Let me tell the story of how Gene Annotator keeps two data worlds coordinated:

- the **source of truth** in SQL (SQLite/Postgres via SQLAlchemy), and
- the **search-optimized copy** in Elasticsearch.

This follows the same architecture from Miguel Grinberg’s full-text search pattern, but let me walk you through the exact implementation in this codebase, including where it matches and where it diverges.”

**Pause and draw this flow:**

1. App starts.
2. Elasticsearch client is attached to the Flask app.
3. A model opts into search using `SearchableMixin`.
4. SQLAlchemy session commit events capture changed objects.
5. After successful commit, changed searchable objects are indexed or removed.
6. Search requests hit Elasticsearch for ranked IDs, then hydrate from SQL.

---

## Scene 2 — Bootstrapping the Elasticsearch connection

**Speaker:**

“Everything begins in `create_app`. If `ELASTICSEARCH_URL` exists, the app creates an Elasticsearch client and stores it at `app.elasticsearch`; otherwise it sets this to `None`.

That ‘None fallback’ is important: all indexing/search functions check for this and no-op gracefully if Elasticsearch is unavailable. So the app can still run without search infrastructure.”

**Point to code facts:**

- App wiring for Elasticsearch in `src/app/__init__.py`.
- URL configured from environment in `src/config.py`.

**Why this matters:**

“It gives us an explicit feature toggle through configuration, and makes local/test scenarios predictable.”

---

## Scene 3 — The model contract: `__searchable__`

**Speaker:**

“Now, how does a model become searchable? It inherits from `SearchableMixin` and declares a list of fields in `__searchable__`.

In this repo, that model is `Post`.

So `Post` says: index my `body` field. That’s the contract the indexing code relies on.”

**Contrast with assumptions:**

“Even though the project is gene-focused, the Elasticsearch integration currently targets microblog `Post` search, not the `Gene` tables.”

---

## Scene 4 — The synchronization mechanism (heart of the story)

**Speaker:**

“Now comes the critical transaction-aware sync logic.

The mixin registers two SQLAlchemy session event listeners:

- `before_commit`
- `after_commit`

### Step A: `before_commit`

Right before commit, the code snapshots three buckets from the session:

- `session.new` → additions
- `session.dirty` → updates
- `session.deleted` → removals

These are stored on the session as `_changes`.

### Step B: actual database commit

SQL transaction is persisted first.

### Step C: `after_commit`

After a successful commit, the code iterates those snapshots:

- objects in `add` and `update` are sent to `search.add_to_index`
- objects in `delete` are sent to `search.remove_from_index`

But only if each object is an instance of `SearchableMixin`.

So this is a selective pipeline, not a blanket indexing of all models.”

**Key architectural point to emphasize aloud:**

“This is not eventual sync through a background queue. It’s commit-hook-driven synchronization right after DB persistence. That keeps SQL and ES tightly aligned at commit boundaries.”

---

## Scene 5 — What exactly gets sent to Elasticsearch

**Speaker:**

“`search.add_to_index` constructs a payload by iterating `model.__searchable__`.

For each declared field, it pulls the attribute value from the model and writes a document to Elasticsearch using:

- index name = SQL table name (`model.__tablename__`)
- document ID = SQL row ID (`model.id`)
- document body = searchable fields payload

Deletion mirrors this by index + ID.

So identity across systems is deterministic: SQL primary key becomes Elasticsearch document ID.”

---

## Scene 6 — Query path: search first, hydrate second

**Speaker:**

“Search requests do not directly render Elasticsearch documents.

Instead, query execution has two phases:

1. `query_index` runs an Elasticsearch `multi_match` against all indexed fields and returns ordered hit IDs + total.
2. `SearchableMixin.search` runs a SQL query for those IDs, and reorders results with a SQL `CASE` expression to preserve Elasticsearch ranking.

That second step is crucial. Without rank-preserving reordering, SQL `IN (...)` could return rows in arbitrary order.”

**Audience takeaway:**

“Elasticsearch decides relevance, SQL provides authoritative records.”

---

## Scene 7 — Where this implementation aligns with Miguel’s tutorial

**Speaker:**

“Now let’s compare with the Flask Mega-Tutorial pattern.

The DNA is the same:

- searchable mixin
- `__searchable__` fields
- before/after commit hooks
- add/update/delete index operations
- two-phase search (ES IDs → SQL rows)
- rank-preserving `CASE` ordering

So conceptually this app is a direct descendant of that architecture.”

---

## Scene 8 — Practical differences in this repository

**Speaker:**

“Here are meaningful local differences:

1. **Scope of indexed models:** currently `Post` is the searchable model, not gene entities.
2. **Initialization style:** Elasticsearch client is attached in app factory with environment-driven optionality.
3. **Operational helper:** there is a CLI command (`create-search-indices`) that retries cluster connection and then indexes existing posts.
4. **Graceful fallback:** all search helper functions return harmless defaults when Elasticsearch is disabled.

So the mechanism is familiar, but operational ergonomics are tailored for this project.”

---

## Scene 9 — Failure modes and behavioral nuances

**Speaker:**

“Let’s think like production engineers.

- If commit never happens, index never updates. Good: avoids indexing uncommitted data.
- If Elasticsearch is unreachable, helper methods currently no-op (when client is absent) or may raise during calls (if client exists but fails at runtime).
- Since indexing happens after commit, a transient ES failure can create temporary SQL/ES drift.
- Reindex support (`reindex` + CLI) is the recovery valve for drift.

So this design is strong for consistency at normal commit flow, with manual/operational reindex as repair strategy.”

---

## Scene 10 — End-to-end walkthrough (spoken example)

**Speaker:**

“Let’s walk one concrete lifecycle:

1. A researcher submits a new microblog post.
2. Flask route adds `Post(...)` to SQLAlchemy session.
3. `db.session.commit()` is called.
4. `before_commit` captures that post in `add`.
5. SQL commit succeeds.
6. `after_commit` sees the post is `SearchableMixin`.
7. It indexes the post body into Elasticsearch under index `post`, doc id equal to SQL `post.id`.
8. Later, user searches `/search?q=...`.
9. Elasticsearch returns ranked matching post IDs.
10. SQL query fetches those posts and preserves ES ordering.
11. UI renders canonical SQL model objects in relevance order.

That is the synchronization story in one transaction and one query round-trip.”

---

## Scene 11 — Close with the architecture in one sentence

**Speaker:**

“Gene Annotator treats SQL as the system of record and Elasticsearch as a derived, commit-synchronized search projection, maintained through SQLAlchemy session hooks and consumed through ID-based hydration back into SQL models.”

---

## Optional rehearsal notes

- Spend most time on Scenes 4, 6, and 9.
- If audience is junior, define `session.new/dirty/deleted` with examples.
- If audience is senior, emphasize drift handling and reindex strategy.
- Whiteboard shorthand: **Commit hooks → ES projection → ID hydrate → rank preserved**.
