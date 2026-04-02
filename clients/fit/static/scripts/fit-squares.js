/**
 * Fit game: square CRUD, stats, clear-board modal, and submission loading.
 * Depends on: fit-constants.js, fit-geometry.js, fit-transform.js.
 */

var MIN_SQUARES = 11;
var MIN_REQUIRED = FIT_VARIANT === 'rectangle' ? 1 : MIN_SQUARES;

function updateSubmitButtonState() {
  var n = squares.length;
  var isOptimal = window.FIT_OPTIMAL_N && window.FIT_OPTIMAL_N.has(n);
  var tooFew = n < MIN_REQUIRED;

  var reason = '';
  if (n === 0) reason = '';
  else if (tooFew) reason = 'Need ' + (MIN_REQUIRED - n) + ' more ' + fitShapeWord(MIN_REQUIRED - n);
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
  var statLabelCount = document.getElementById('stat-label-count');
  if (!ruleMin) return;

  if (statLabelCount) {
    statLabelCount.textContent = FIT_SHAPE_PLURAL.charAt(0).toUpperCase() + FIT_SHAPE_PLURAL.slice(1);
  }

  var minOk = n >= MIN_REQUIRED;
  ruleMin.className = minOk ? 'rule-pass' : 'rule-fail';
  ruleMin.textContent = minOk
    ? (n + ' ' + fitShapeWord(n) + ' placed')
    : ('Place at least ' + MIN_REQUIRED + ' ' + FIT_SHAPE_PLURAL + ' (' + n + ' now)');

  ruleOptimal.className = (n > 0 && isOptimal) ? 'rule-fail' : 'rule-pass';
  ruleOptimal.textContent = (n > 0 && isOptimal)
    ? (n + ' ' + fitShapeWord(n) + ' is a known optimal, not accepted')
    : (FIT_SHAPE_SINGULAR.charAt(0).toUpperCase() + FIT_SHAPE_SINGULAR.slice(1) + ' count is not a known optimal');
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

  const widthRaw = (maxX - minX) / SQUARE_SIZE;
  const heightRaw = (maxY - minY) / SQUARE_SIZE;
  const widthVal = roundDecimal(widthRaw, 5);
  const heightVal = roundDecimal(heightRaw, 5);

  const precision = isExpanded ? 5 : 2;
  const widthStr = widthVal.toFixed(precision).replace(/\.?0+$/, '');
  const heightStr = heightVal.toFixed(precision).replace(/\.?0+$/, '');

  statBounds.textContent = widthStr + ' × ' + heightStr;

  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;
  const boundsWidth = maxX - minX;
  const boundsHeight = maxY - minY;
  const halfWidth = boundsWidth / 2;
  const halfHeight = boundsHeight / 2;

  boundingBox.style.display = 'block';
  boundingBox.style.left = (centerX - halfWidth) * zoom + 'px';
  boundingBox.style.top = (centerY - halfHeight) * zoom + 'px';
  boundingBox.style.width = boundsWidth * zoom + 'px';
  boundingBox.style.height = boundsHeight * zoom + 'px';
}

function createSquareEl(sq) {
  const el = document.createElement('div');
  const width = getShapeWidthPx(sq);
  const height = getShapeHeightPx(sq);
  let className = 'square';
  if (sq.mode === 'rotate') {
    className += ' mode-rotate';
  }
  el.className = className;
  el.dataset.id = sq.id;
  el.style.left = sq.x * zoom + 'px';
  el.style.top = sq.y * zoom + 'px';
  el.style.width = width * zoom + 'px';
  el.style.height = height * zoom + 'px';
  el.style.transform = 'rotate(' + sq.rotation + 'deg)';
  return el;
}

function addSquare(x, y, width, height) {
  const boardSize = getBoardSize();
  const shapeWidth = Number.isFinite(width) && width > 0 ? width : SQUARE_SIZE;
  const shapeHeight = Number.isFinite(height) && height > 0 ? height : SQUARE_SIZE;
  x = snapPos(x);
  y = snapPos(y);
  const sq = {
    id: 'sq-' + (++idCounter),
    x: Math.max(0, Math.min(x, boardSize.width - shapeWidth)),
    y: Math.max(0, Math.min(y, boardSize.height - shapeHeight)),
    width: shapeWidth,
    height: shapeHeight,
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
  const width = Number.isFinite(apiSq.width) && apiSq.width > 0 ? apiSq.width : SQUARE_SIZE;
  const height = Number.isFinite(apiSq.height) && apiSq.height > 0 ? apiSq.height : SQUARE_SIZE;

  if (FIT_VARIANT === 'rectangle' && Number.isFinite(apiSq.width) && Number.isFinite(apiSq.height)) {
    const cornerAngle = Math.atan2(uy, ux);
    const offsetAngle = Math.atan2(height, width);
    let rotation = (cornerAngle + offsetAngle) * (180 / Math.PI);
    rotation = ((rotation % 360) + 360) % 360;
    const x = cx - width / 2;
    const y = cy - height / 2;
    return { x: x, y: y, width: width, height: height, rotation: rotation };
  }

  const x = cx - SQUARE_SIZE / 2;
  const y = cy - SQUARE_SIZE / 2;
  let rotation = Math.atan2(uy, ux) * (180 / Math.PI) + 45;
  rotation = ((rotation % 360) + 360) % 360;
  return { x: x, y: y, width: SQUARE_SIZE, height: SQUARE_SIZE, rotation: rotation };
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
          width: fitSq.width,
          height: fitSq.height,
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
  const width = getShapeWidthPx(sq);
  const height = getShapeHeightPx(sq);

  const el = board.querySelector('[data-id="' + id + '"]');
  if (!el) return;

  el.style.left = sq.x * zoom + 'px';
  el.style.top = sq.y * zoom + 'px';
  el.style.width = width * zoom + 'px';
  el.style.height = height * zoom + 'px';
  el.style.transform = 'rotate(' + sq.rotation + 'deg)';

  // Update classes for all squares to maintain correct state
  updateAllSquareClasses();
  updateSquareDataDisplay();
  updateStats();
}

function updateAllSquareClasses() {
  squares.forEach(sq => {
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
