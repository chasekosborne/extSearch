/**
 * Fit game: square CRUD, stats, clear-board modal, and submission loading.
 * Depends on: fit-constants.js, fit-geometry.js, fit-transform.js.
 */

var MIN_SQUARES = 11;

function updateSubmitButtonState() {
  var n = squares.length;
  var isOptimal = window.FIT_OPTIMAL_N && window.FIT_OPTIMAL_N.has(n);
  var tooFew = n < MIN_SQUARES;

  var reason = '';
  if (n === 0) reason = '';
  else if (tooFew) reason = 'Need ' + (MIN_SQUARES - n) + ' more square' + (MIN_SQUARES - n !== 1 ? 's' : '');
  else if (isOptimal) reason = 'Known optimal';

  var canSubmit = n > 0 && !tooFew && !isOptimal;
  submitBtn.disabled = !canSubmit;
  submitBtn.setAttribute('aria-disabled', canSubmit ? 'false' : 'true');

  var reasonEl = document.getElementById('submit-reason');
  if (reasonEl) reasonEl.textContent = reason;

  updateSubmitRulesPanel(n, isOptimal);
}

function updateSubmitRulesPanel(n, isOptimal) {
  var ruleMin = document.getElementById('rule-min');
  var ruleOptimal = document.getElementById('rule-optimal');
  if (!ruleMin) return;

  var minOk = n >= MIN_SQUARES;
  ruleMin.className = minOk ? 'rule-pass' : 'rule-fail';
  ruleMin.textContent = minOk ? (n + ' squares placed') : ('Place at least ' + MIN_SQUARES + ' squares (' + n + ' now)');

  ruleOptimal.className = (n > 0 && isOptimal) ? 'rule-fail' : 'rule-pass';
  ruleOptimal.textContent = (n > 0 && isOptimal) ? (n + ' squares is a known optimal, not accepted') : 'Square count is not a known optimal';
}

function updateStats() {
  statCount.textContent = squares.length;
  updateSubmitButtonState();
  if (!card) return;
  const isExpanded = card.classList.contains('expanded');

  if (squares.length === 0) {
    statBounds.textContent = '-';
    boundingBox.style.display = 'none';
    return;
  }

  let minX = Infinity, minY = Infinity;
  let maxX = -Infinity, maxY = -Infinity;

  squares.forEach(sq => {
    const bounds = getRotatedSquareBounds(sq);
    minX = Math.min(minX, bounds.minX);
    minY = Math.min(minY, bounds.minY);
    maxX = Math.max(maxX, bounds.maxX);
    maxY = Math.max(maxY, bounds.maxY);
  });

  const maxSideRaw = Math.max((maxX - minX) / SQUARE_SIZE, (maxY - minY) / SQUARE_SIZE);
  const maxSide = roundDecimal(maxSideRaw, 5);  /* hundred-thousands place to match manual precision */

  const precision = isExpanded ? 5 : 2;
  const maxSideStr = maxSide.toFixed(precision).replace(/\.?0+$/, '');

  statBounds.textContent = maxSideStr + ' × ' + maxSideStr;

  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;
  const squareSize = maxSide * SQUARE_SIZE;
  const halfSize = squareSize / 2;

  boundingBox.style.display = 'block';
  boundingBox.style.left = (centerX - halfSize) * zoom + 'px';
  boundingBox.style.top = (centerY - halfSize) * zoom + 'px';
  boundingBox.style.width = squareSize * zoom + 'px';
  boundingBox.style.height = squareSize * zoom + 'px';
}

function createSquareEl(sq) {
  const el = document.createElement('div');
  let className = 'square';
  if (sq.mode === 'rotate') {
    className += ' mode-rotate';
  }
  el.className = className;
  el.dataset.id = sq.id;
  el.style.left = sq.x * zoom + 'px';
  el.style.top = sq.y * zoom + 'px';
  el.style.width = SQUARE_SIZE * zoom + 'px';
  el.style.height = SQUARE_SIZE * zoom + 'px';
  el.style.transform = 'rotate(' + sq.rotation + 'deg)';
  return el;
}

function addSquare(x, y) {
  const boardSize = getBoardSize();
  x = snapPos(x);
  y = snapPos(y);
  const sq = {
    id: 'sq-' + (++idCounter),
    x: Math.max(0, Math.min(x, boardSize.width - SQUARE_SIZE)),
    y: Math.max(0, Math.min(y, boardSize.height - SQUARE_SIZE)),
    rotation: 0,
    mode: 'move'
  };

  // Check for collisions before adding
  if (!wouldCollide(sq, null)) {
    squares.push(sq);
    board.appendChild(createSquareEl(sq));
    selectedSquareId = sq.id;
    updateAllSquareClasses();
    updateSquareDataDisplay();
    updateStats();
  }
}

/** Convert API square (cx, cy, ux, uy) to Fit game square (x, y, rotation). */
function apiSquareToFit(apiSq) {
  const cx = apiSq.cx, cy = apiSq.cy, ux = apiSq.ux, uy = apiSq.uy;
  const x = cx - SQUARE_SIZE / 2;
  const y = cy - SQUARE_SIZE / 2;
  let rotation = Math.atan2(uy, ux) * (180 / Math.PI) + 45;
  rotation = ((rotation % 360) + 360) % 360;
  return { x: x, y: y, rotation: rotation };
}

/** Load a submission into the board (from ?load=id). Clears existing squares. */
function loadSubmissionIntoBoard(submissionId) {
  fetch('/api/submission/' + submissionId + '/squares')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      const apiSquares = data.squares || [];
      undoStack = [];
      redoStack = [];
      clipboard = null;
      deleteAllSquares(true);
      apiSquares.forEach(function (apiSq) {
        const fitSq = apiSquareToFit(apiSq);
        const sq = {
          id: 'sq-' + (++idCounter),
          x: fitSq.x,
          y: fitSq.y,
          rotation: fitSq.rotation,
          mode: 'move'
        };
        squares.push(sq);
        board.appendChild(createSquareEl(sq));
      });
      selectedSquareId = null;
      updateAllSquareClasses();
      updateSquareDataDisplay();
      updateStats();
      if (squares.length > 0) {
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        squares.forEach(function (sq) {
          const b = getRotatedSquareBounds(sq);
          minX = Math.min(minX, b.minX);
          minY = Math.min(minY, b.minY);
          maxX = Math.max(maxX, b.maxX);
          maxY = Math.max(maxY, b.maxY);
        });
        const cx = (minX + maxX) / 2;
        const cy = (minY + maxY) / 2;
        const rect = boardZoomContainer.getBoundingClientRect();
        panX = cx * zoom - rect.width / 2;
        panY = cy * zoom - rect.height / 2;
        applyTransform();
      } else {
        centerViewOnGrid();
      }
    })
    .catch(function () { });
}

function removeSquare(id) {
  squares = squares.filter(function(s) { return s.id !== id; });
  const el = board.querySelector('[data-id="' + id + '"]');
  if (el) el.remove();
  if (selectedSquareId === id) {
    selectedSquareId = null;
    updateSquareDataDisplay();
  }
  updateAllSquareClasses();
  updateStats();
}

/* Delete all: confirmation modal + clear logic */
const deleteAllBtn = document.getElementById('delete-all');
const clearConfirmOverlay = document.getElementById('clear-confirm-overlay');
const clearConfirmCancel = document.getElementById('clear-confirm-cancel');
const clearConfirmOk = document.getElementById('clear-confirm-ok');

function performClearBoard() {
  squares.length = 0;
  board.querySelectorAll('.square').forEach(function (el) { el.remove(); });
  selectedSquareId = null;
  dragState = null;
  squareData.style.display = 'none';
  boundingBox.style.display = 'none';
  updateStats();
}

function deleteAllSquares(skipConfirm) {
  if (squares.length === 0) {
    return;
  }
  if (skipConfirm) {
    performClearBoard();
    return;
  }
  clearConfirmOverlay.removeAttribute('hidden');
}

function closeClearConfirmModal() {
  clearConfirmOverlay.setAttribute('hidden', '');
}

clearConfirmCancel.addEventListener('click', closeClearConfirmModal);
clearConfirmOk.addEventListener('click', function () {
  closeClearConfirmModal();
  if (squares.length > 0) {
    pushUndoState();
  }
  performClearBoard();
});

clearConfirmOverlay.addEventListener('click', function (e) {
  if (e.target === clearConfirmOverlay) closeClearConfirmModal();
});

document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape' && !clearConfirmOverlay.hasAttribute('hidden')) {
    closeClearConfirmModal();
  }
});

function updateSquare(id, updates) {
  const sq = squares.find(function(s) { return s.id === id; });
  if (!sq) return;
  Object.assign(sq, updates);

  const el = board.querySelector('[data-id="' + id + '"]');
  if (!el) return;

  el.style.left = sq.x * zoom + 'px';
  el.style.top = sq.y * zoom + 'px';
  el.style.width = SQUARE_SIZE * zoom + 'px';
  el.style.height = SQUARE_SIZE * zoom + 'px';
  el.style.transform = 'rotate(' + sq.rotation + 'deg)';

  // Update classes for all squares to maintain correct state
  updateAllSquareClasses();
  updateSquareDataDisplay();
  updateStats();
}

function updateAllSquareClasses() {
  squares.forEach(sq => {

    if (multiEnable){
      const el = board.querySelector('[data-id="' + sq.id + '"]');
      if (!el) return;

      let className = 'square';
      if (sq.mode === 'rotate') {
        className += ' mode-rotate';
      }
      if (selectedSquares.indexOf(sq.id) != -1) {
        className += ' selected';
      } else {
        className += ' not-selected';
      }
      el.className = className;

    }else{
      const el = board.querySelector('[data-id="' + sq.id + '"]');
      if (!el) return;

      let className = 'square';
      if (sq.mode === 'rotate') {
        className += ' mode-rotate';
      }
      if (selectedSquareId === sq.id) {
        className += ' selected';
      } else if (selectedSquareId !== null || (dragState && dragState.id !== sq.id)) {
        className += ' not-selected';
      }
      el.className = className;
    }

  });
}

/** Rebuild square DOM from `squares` (used by undo/redo). */
function renderSquares() {
  board.querySelectorAll('.square').forEach(function (el) { el.remove(); });
  squares.forEach(function (sq) {
    board.appendChild(createSquareEl(sq));
  });
  idCounter = 0;
  squares.forEach(function (sq) {
    var m = /^sq-(\d+)$/.exec(sq.id);
    if (m) idCounter = Math.max(idCounter, parseInt(m[1], 10));
  });
  updateAllSquareClasses();
  updateSquareDataDisplay();
  updateStats();
}
