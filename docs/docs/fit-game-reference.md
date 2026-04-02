## Fit game reference (Square and Rectangle)

This page documents the main game flow and key functions used in the Fit client.
It focuses on:

- Square mode behavior
- Rectangle mode behavior
- What each important function does
- Where each function is used

---

## 1. Main game flow

The Fit game loads in this order:

1. Template sets `window.FIT_VARIANT` (`square` or `rectangle`) in `game.html`.
2. `fit-constants.js` initializes shared state and mode-specific settings.
3. Geometry, transform, CRUD, data editor, and input files attach helpers and event handlers.
4. `fit-main.js` checks `?load=<submission_id>` and loads a saved submission when present.
5. User interaction updates in-memory shapes, then updates DOM and stats.
6. Submit sends payload to backend (`/api/fit/submit`) with variant and shape geometry.

---

## 2. Square mode vs rectangle mode

Both modes use the same board/camera/collision pipeline.

Differences:

- Square mode
  - New shapes default to `56 x 56` pixels.
  - Minimum submit count is 11.
  - Payload uses corner points per shape.

- Rectangle mode
  - New shapes use toolbar width/height inputs (in square units, scaled by 56 px).
  - Minimum submit count is 1.
  - Payload includes corners plus width/height metadata.
  - Saved submissions keep width/height so View in Fit and Explore render true rectangles.

---

## 3. Frontend function reference

### A) `fit-constants.js`

- `fitShapeWord(count)`
  - Does: Returns `square/squares` or `rectangle/rectangles` by active variant.
  - Used by: submit rules/status text.

- `getCurrentShapeSizePx()`
  - Does: Returns shape size for creation.
  - Used by: pointer create flow (`onPointerDown` in `fit-input.js`).

- `getShapeWidthPx(sq)` and `getShapeHeightPx(sq)`
  - Does: Returns shape dimensions from object; falls back to square size.
  - Used by: geometry, rendering, collision, loading, and editing.

- `pushUndoState()`
  - Does: Saves current shapes snapshot and clears redo branch.
  - Used by: move/rotate/delete/clear operations before mutation.

- `snapPos(px)`
  - Does: Snaps board coordinate to current position grid step.
  - Used by: add/move/paste.

- `snapRotation(deg)`
  - Does: Snaps rotation angle to configured angle step when enabled.
  - Used by: rotate drag and input edits.

### B) `fit-transform.js`

- `applyTransform()`
  - Does: Applies pan/zoom, scales board/grid, updates shape DOM positions/sizes, then refreshes stats.
  - Used by: pan/zoom handlers and view centering.

- `centerViewOnGrid()`
  - Does: Centers camera on board center.
  - Used by: initial startup and empty board resets.

- `clientToBoard(clientX, clientY)`
  - Does: Converts screen coordinates to board coordinates.
  - Used by: pointer create/move/rotate.

- `isInsideBoardViewport(clientX, clientY)`
  - Does: Checks if pointer is inside board area.
  - Used by: create drop validation.

- `getBoardSize()`
  - Does: Returns board dimensions.
  - Used by: move clamp and add clamp.

### C) `fit-geometry.js`

- `getRotatedSquareBounds(sq)`
  - Does: Returns axis-aligned bounds for current shape at rotation.
  - Used by: stats/bounding box and camera focus after load.

- `getSquareCorners(sq)`
  - Does: Returns four rotated corners of a shape.
  - Used by: submit payload and SAT checks.

- `squaresOverlap(sq1, sq2)`
  - Does: SAT overlap test (touching edges are treated as non-overlap).
  - Used by: local collision checks.

- `wouldCollide(testSq, excludeId)`
  - Does: Checks test shape against all current shapes except optional id.
  - Used by: add, move, rotate, paste.

- `roundDecimal`, `formatSquareUnit`, `formatRotation`
  - Does: numeric formatting helpers for stable display and payload values.
  - Used by: stats and selection editor.

- Coordinate helpers: `pixelToCenterX/Y`, `centerToPixelX/Y`
  - Does: convert between board pixels and center-based unit display.
  - Used by: selection editor fields.

- `roundCornersForSubmit(corners)`
  - Does: rounds payload corner coordinates for stable submit values.
  - Used by: submit handler.

### D) `fit-squares.js`

- `updateSubmitButtonState()`
  - Does: enables/disables submit based on min count and known-optimal count rules.
  - Used by: stats updates and startup.

- `updateSubmitRulesPanel(n, isOptimal)`
  - Does: updates visible rule lines for user guidance.
  - Used by: submit state updates.

- `updateStats()`
  - Does: updates count, bounds text, and bounding box overlay.
  - Used by: almost every mutation and transform update.

- `createSquareEl(sq)`
  - Does: builds DOM node for one shape.
  - Used by: add, load, and full re-render.

- `addSquare(x, y, width, height)`
  - Does: creates a new shape in model and DOM (collision-safe).
  - Used by: create drag drop.

- `apiSquareToFit(apiSq)`
  - Does: converts API geometry to local board shape (`x`, `y`, `width`, `height`, `rotation`).
  - Used by: submission load flow.

- `loadSubmissionIntoBoard(submissionId)`
  - Does: fetches saved shapes and replaces current board with loaded solution.
  - Used by: URL `?load=` startup flow and Explore "View in Fit".

- `removeSquare(id)`
  - Does: deletes one shape from model and DOM.
  - Used by: delete-zone drop and clear helpers.

- `performClearBoard()`, `deleteAllSquares(skipConfirm)`, `closeClearConfirmModal()`
  - Does: clear board logic and confirmation modal control.
  - Used by: Clear button and load flow.

- `updateSquare(id, updates)`
  - Does: mutates shape and refreshes corresponding DOM and stats.
  - Used by: move/rotate/input editing.

- `updateAllSquareClasses()`
  - Does: manages selected/not-selected/rotate mode classes.
  - Used by: selection and drag updates.

- `renderSquares()`
  - Does: rebuilds all shape DOM from current model.
  - Used by: undo/redo restore.

### E) `fit-square-data.js`

- `applySquareDataInputs()`
  - Does: applies x/y/rotation text input edits to selected shape, with collision protection.
  - Used by: blur and Enter handlers.

- `setupSquareDataInputHandlers()`
  - Does: wires blur/Enter events for editor inputs.
  - Used by: display refresh.

- `updateSquareDataDisplay()`
  - Does: renders selected-shape editor or variant-aware empty message.
  - Used by: selection changes and updates.

### F) `fit-input.js`

- `isInDeleteZone(clientX, clientY)`
  - Does: checks delete drop area hit.
  - Used by: move drag and pointer up.

- `fitUndo()` and `fitRedo()`
  - Does: restore shape snapshots.
  - Used by: toolbar buttons and shortcuts.

- `fitCopySquare()` and `fitPasteSquare()`
  - Does: copy/paste selected shape with collision and bounds checks.
  - Used by: keyboard shortcuts.

- `onPointerDown(e)`
  - Does: enters create, pan, move, or rotate drag state.
  - Used by: global pointerdown listener.

- `onPointerMove(e)`
  - Does: updates active drag behavior and visual states.
  - Used by: global pointermove listener.

- `onPointerUp(e)`
  - Does: commits create/move/rotate/pan flow and cleanup.
  - Used by: global pointerup listener.

- `onDoubleClick(e)`
  - Does: toggles selected shape between move and rotate mode.
  - Used by: board dblclick listener.

- `onWheel(e)`
  - Does: cursor-centered zoom.
  - Used by: board wheel listener.

- `flushSquares(testSq, draggedID, ...)` and `wouldCollideWith(testSq, excludeId)`
  - Does: collision-resolution helper for flush movement when drag collides.
  - Used by: move drag path.

- `dotProduct(v, u)`
  - Does: utility used by flush collision calculations.

### G) `fit-main.js`

- URL-load bootstrap
  - Does: checks `load` query parameter, loads submission, then removes param from URL.
  - Used by: startup only.

- Initial `requestAnimationFrame(...)`
  - Does: centers view if not URL-loaded and initializes UI state.
  - Used by: startup only.

---

## 4. Backend function reference

### `clients/fit/routes.py`

- `_normalize_variant_arg(raw_variant)`
  - Does: validates route variant and falls back to square.
  - Used by: `/fit/explore` and variant-aware pages.

- `game()` (`/fit`)
  - Does: serves main game template and injects initial variant.

- `fit_api()` (`/fit/api`)
  - Does: serves API docs page.

- `explore_solutions()` (`/fit/explore`)
  - Does: variant-aware list page, pagination, duplicate filtering.

### `clients/fit/api.py`

- `_check_ip_rate(ip, is_authenticated)`
  - Does: per-IP submission throttle.
  - Used by: submit endpoint.

- `_get_authenticated_user()`
  - Does: resolves user from session or Bearer token.
  - Used by: submit endpoint.

- `api_token()` (`POST /api/fit/token`)
  - Does: returns JWT for API submissions.

- `api_explore_square_counts()` (`GET /api/fit/explore/square-counts`)
  - Does: returns lazy-load chip counts for Explore, variant-aware.

- `api_submission_squares(submission_id)` (`GET /api/submission/<id>/squares`)
  - Does: returns saved geometry for View in Fit and Explore preview (includes width/height for rectangles).

- `api_submit()` (`POST /api/fit/submit`)
  - Does: validates request shape, variant, auth/rate limits; stores submission.

- `_add_rate_headers(resp, rate_info)`
  - Does: writes response rate-limit headers.

### `clients/fit/db/submissions.py`

- `get_or_create_fit_instance(...)`
  - Does: resolves problem instance row by domain/container.

- `create_fit_submission(...)`
  - Does: stores square-mode submission and shape rows.

- `create_rectangle_submission(...)`
  - Does: stores rectangle-mode submission with width/height shape metadata.

- `_normalize_rectangle_payload(shape_payload)`
  - Does: validates rectangle payload shape and extracts normalized geometry.

- `ensure_rectangle_submission_table()`
  - Does: creates/updates rectangle storage table on demand.

- `get_available_square_counts(variant=...)`
  - Does: returns counts per shape count for Explore chips.

- `get_best_submissions(...)`
  - Does: paginated leaderboard rows, variant-aware.

- `get_top_valid_ids(...)`
  - Does: returns top distinct-bound valid rows for medal markers.

- `get_submission_squares(submission_id)`
  - Does: returns stored shape rows for loading/preview.

### `clients/fit/verify_worker.py`

- `fetch_pending(limit)`
  - Does: gets pending submissions for validation.

- `fetch_squares(submission_id, container_type)`
  - Does: loads stored shape rows from the right table.

- `validate_submission(squares)`
  - Does: square-mode geometry validator.

- `validate_rectangle_submission(squares)`
  - Does: rectangle-mode geometry validator.

- `record_result(submission_id, valid, reason, metrics, obj_from_db)`
  - Does: writes validation run and updates submission status/objective.

- `process_batch(limit)`
  - Does: validates pending rows and prints result log.

- `main()`
  - Does: CLI entrypoint (`--loop`, `--interval`, `--batch`).

---

## 5. Typical usage patterns

### Add and submit in rectangle mode

1. Open `/fit?variant=rectangle`.
2. Set width/height in toolbar.
3. Drag from source tile to create shapes.
4. Move/rotate until non-overlapping.
5. Submit (`POST /api/fit/submit`, variant `rectangle`).

### Open a saved submission in game

1. Explore page uses `View in Fit` with `?load=<id>`.
2. `fit-main.js` calls `loadSubmissionIntoBoard(id)`.
3. Loaded geometry is converted and rendered, then camera centers on solution bounds.

### Explore list and preview

1. Open `/fit/explore?variant=square` or `variant=rectangle`.
2. Chip rows lazily load counts through `/api/fit/explore/square-counts`.
3. Clicking a row fetches `/api/submission/<id>/squares` and renders SVG preview.

---

If you add new game behavior, update this reference and the API docs page together so frontend and backend contracts stay aligned.
