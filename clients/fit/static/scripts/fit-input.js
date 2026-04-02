/**
 * Fit game: pointer/drag handling and event bindings.
 * Depends on: all other fit-*.js (constants, geometry, transform, squares, square-data).
 */

function isInDeleteZone(clientX, clientY) {
  const rect = deleteZone.getBoundingClientRect();
  return clientX >= rect.left && clientX <= rect.right &&
         clientY >= rect.top && clientY <= rect.bottom;
}

function fitUndo() {
  if (undoStack.length === 0) return;
  redoStack.push(JSON.stringify(squares));
  squares = JSON.parse(undoStack.pop());
  renderSquares();
}

function fitRedo() {
  if (redoStack.length === 0) return;
  undoStack.push(JSON.stringify(squares));
  squares = JSON.parse(redoStack.pop());
  renderSquares();
}

function fitCopySquare() {
  if (!selectedSquareId) return;
  const sq = squares.find(function (s) { return s.id === selectedSquareId; });
  if (!sq) return;
  clipboard = Object.assign({}, sq);
}

function fitPasteSquare() {
  if (!clipboard) return;
  const boardSize = getBoardSize();
  const shapeWidth = getShapeWidthPx(clipboard);
  const shapeHeight = getShapeHeightPx(clipboard);
  let x = snapPos(clipboard.x + 20);
  let y = snapPos(clipboard.y + 20);
  x = Math.max(0, Math.min(x, boardSize.width - shapeWidth));
  y = Math.max(0, Math.min(y, boardSize.height - shapeHeight));
  const newSquare = {
    id: 'sq-' + (++idCounter),
    x: x,
    y: y,
    width: shapeWidth,
    height: shapeHeight,
    rotation: clipboard.rotation,
    mode: clipboard.mode || 'move'
  };
  if (wouldCollide(newSquare, null)) {
    showToast('No room to paste here.', 'error');
    return;
  }
  pushUndoState();
  squares.push(newSquare);
  board.appendChild(createSquareEl(newSquare));
  selectedSquareId = newSquare.id;
  updateAllSquareClasses();
  updateSquareDataDisplay();
  updateStats();
}

function onPointerDown(e) {
  const target = e.target.closest('.square');
  const isSource = e.target.closest('#source');
  const isPopup = e.target.closest('#square-data');
  const isBoard = e.target.closest('#board') && !target && !isPopup;

  if (isSource) {
    var shapeSize = getCurrentShapeSizePx();
    dragState = {
      type: 'create',
      startX: e.clientX,
      startY: e.clientY,
      createWidth: shapeSize.width,
      createHeight: shapeSize.height
    };
    ghost.style.display = 'block';
    ghost.style.left = (e.clientX - SQUARE_SIZE / 2) + 'px';
    ghost.style.top = (e.clientY - SQUARE_SIZE / 2) + 'px';
    selectedSquareId = null;
    updateAllSquareClasses();
    updateSquareDataDisplay();
    e.preventDefault();
  } else if (isBoard) {
    selectedSquareId = null;
    updateAllSquareClasses();
    updateSquareDataDisplay();
    dragState = {
      type: 'pan',
      startClientX: e.clientX,
      startClientY: e.clientY,
      startPanX: panX,
      startPanY: panY
    };
    boardZoomContainer.classList.add('panning');
    e.preventDefault();
  } else if (target) {
    const id = target.dataset.id;
    const sq = squares.find(function(s) { return s.id === id; });
    if (!sq) return;

    pushUndoState();

    // Select the square
    selectedSquareId = id;
    updateAllSquareClasses();
    updateSquareDataDisplay();

    if (sq.mode === 'rotate') {
      const pt = clientToBoard(e.clientX, e.clientY);
      const centerX = sq.x + getShapeWidthPx(sq) / 2;
      const centerY = sq.y + getShapeHeightPx(sq) / 2;
      const startAngle = Math.atan2(pt.y - centerY, pt.x - centerX);
      dragState = {
        type: 'rotate',
        id: id,
        startAngle: startAngle,
        startRotation: sq.rotation
      };
      target.style.zIndex = 100;
      e.preventDefault();
    } else {
      const pt = clientToBoard(e.clientX, e.clientY);
      dragState = {
        type: 'move',
        id: id,
        offsetX: pt.x - sq.x,
        offsetY: pt.y - sq.y
      };
      target.style.zIndex = 100;
      e.preventDefault();
    }
  }
}

function onPointerMove(e) {
  if (!dragState) return;

  if (dragState.type === 'create') {
    ghost.style.left = (e.clientX - SQUARE_SIZE / 2) + 'px';
    ghost.style.top = (e.clientY - SQUARE_SIZE / 2) + 'px';
  } else if (dragState.type === 'pan') {
    const dx = e.clientX - dragState.startClientX;
    const dy = e.clientY - dragState.startClientY;
    panX = dragState.startPanX - dx;
    panY = dragState.startPanY - dy;
    applyTransform();
  } else if (dragState.type === 'move') {
    const pt = clientToBoard(e.clientX, e.clientY);
    const boardSize = getBoardSize();
    const sq = squares.find(function(s) { return s.id === dragState.id; });
    if (!sq) return;
    const shapeWidth = getShapeWidthPx(sq);
    const shapeHeight = getShapeHeightPx(sq);
    let x = snapPos(pt.x - dragState.offsetX);
    let y = snapPos(pt.y - dragState.offsetY);

    x = Math.max(0, Math.min(x, boardSize.width - shapeWidth));
    y = Math.max(0, Math.min(y, boardSize.height - shapeHeight));

    // Check for collisions before updating
    const testSq = { x: x, y: y, width: shapeWidth, height: shapeHeight, rotation: sq.rotation };
    if (!wouldCollide(testSq, dragState.id)) {
      updateSquare(dragState.id, { x: x, y: y });
    } else { // use Separating Axis Theorem to move sqaures flush
      updateSq = flushSquares(testSq, dragState.id);
      updateSquare(dragState.id, { x: updateSq.x, y: updateSq.y });
    }

    if (isInDeleteZone(e.clientX, e.clientY)) {
      deleteZone.classList.add('active');
    } else {
      deleteZone.classList.remove('active');
    }
  } else if (dragState.type === 'rotate') {
    const pt = clientToBoard(e.clientX, e.clientY);
    const sq = squares.find(function(s) { return s.id === dragState.id; });
    if (!sq) return;

    const centerX = sq.x + getShapeWidthPx(sq) / 2;
    const centerY = sq.y + getShapeHeightPx(sq) / 2;
    const currentAngle = Math.atan2(pt.y - centerY, pt.x - centerX);

    const angleDiff = currentAngle - dragState.startAngle;
    const rotationDiff = angleDiff * (180 / Math.PI);
    let newRotation = dragState.startRotation + rotationDiff;
    newRotation = snapRotation(newRotation);

    // Normalize to 0-360 range
    newRotation = ((newRotation % 360) + 360) % 360;

    // Check for collisions before updating
    const testSq = {
      x: sq.x,
      y: sq.y,
      width: getShapeWidthPx(sq),
      height: getShapeHeightPx(sq),
      rotation: newRotation
    };
    if (!wouldCollide(testSq, dragState.id)) {
      updateSquare(dragState.id, { rotation: newRotation });
    }
  }
}

function flushSquares(testSq, draggedID, fallbackSq = { x: 0, y: 0 }, arrayID = new Array()){
    let collisionSq = wouldCollideWith(testSq, draggedID); // get square that is being collided with

    tempSq = squares.find(function(s) { return s.id === dragState.id; });
    fallbackSq.x = tempSq.x;
    fallbackSq.y = tempSq.y;

    if (arrayID.indexOf(collisionSq.id) != -1){ // if square has already been collided with and moved away from before
      return fallbackSq; // cancel flush movement
    }

    if (testSq.x == collisionSq.x && testSq.y == collisionSq.y){ // if in the exact middle of colliding square
      return fallbackSq // cancel flush movement
    }

    // initializations
    x = testSq.x;
    y = testSq.y;
    arrayID.push(collisionSq.id);
    smallestScalar = null;
    finalVector = {x:0.0, y:0.0};
    separatingAxis = false;
    testMin = null;
    testMax = null;
    collisionMin = null;
    collisionMax = null;
    unitVector = {x:0.0, y:0.0};
    dot = 0.0;

    let normals = [];
    normals.push(testSq.rotation);
    if (normals.indexOf(collisionSq.rotation) == -1) normals.push(collisionSq.rotation); // ifs prevents duplicate normals
    if (normals.indexOf(testSq.rotation + 90) == -1) normals.push(testSq.rotation + 90.0);// get the degree normal of the adjacent side, only need 2 angles for each square since axis is same for opposite sides
    if (normals.indexOf(collisionSq.rotation + 90) == -1) normals.push(collisionSq.rotation + 90.0);

    testCorners = getSquareCorners(testSq);
    collisionCorners = getSquareCorners(collisionSq);
        
    for (normal in normals){
      // set up unit vector for current axis
      unitVector.x = Math.cos(normals[normal] * (Math.PI/180));
      unitVector.y = Math.sin(normals[normal] * (Math.PI/180));

      // certain values must be reset to null and not 0, or they will affect max and min calculations
      separatingAxis = false;
      testMin = null;
      testMax = null;
      collisionMin = null;
      collisionMax = null;

      for (corner in testCorners){ // project each corner onto axis and get the min and max bounds of box on it
        dot = dotProduct(testCorners[corner], unitVector);
        if (dot > testMax || testMax == null) testMax = dot;
        if (dot < testMin || testMin == null) testMin = dot;
       }

       for (corner in collisionCorners){ // ditto for the collision box
        dot = dotProduct(collisionCorners[corner], unitVector);
        if (dot > collisionMax || collisionMax == null) collisionMax = dot;
        if (dot < collisionMin || collisionMin == null) collisionMin = dot;
       }

      if (!((testMin < collisionMax && testMax > collisionMax) || (testMax > collisionMin && testMin < collisionMin))){ // if not collision
        separatingAxis = true; // there is a separating axis
      } else { // if there is a collision -> update smallest scalar if new collision is smaller
        if (testMin < collisionMax && testMax > collisionMax){ // check which areas caused collision
          if ((collisionMax - testMin) < smallestScalar || smallestScalar == null){ // if distance to move is shorter than last scalar
            // record new smallest magnitude and direction values
            smallestScalar = (collisionMax - testMin);
            finalVector.x = unitVector.x;
             finalVector.y = unitVector.y;
          }
        }
        if (testMax > collisionMin && testMin < collisionMin){ // check which areas caused collision
          if ((testMax - collisionMin) < smallestScalar || smallestScalar == null){ // if distance to move is shorter than last scalar
            // record new smallest magnitude and direction values
            smallestScalar = (testMax - collisionMin);
            finalVector.x = unitVector.x;
            finalVector.y = unitVector.y;
          }
        }
      }
    }
    if (((testSq.x < collisionSq.x) && (finalVector.x > 0)) || ((testSq.x > collisionSq.x) && (finalVector.x < 0))) finalVector.x = finalVector.x * -1; // flip x direction if vector in wrong direction
    if (((testSq.y < collisionSq.y) && (finalVector.y > 0)) || ((testSq.y > collisionSq.y) && (finalVector.y < 0))) finalVector.y = finalVector.y * -1; // ditto for y
    //updateSquare(draggedID, {x: x + (smallestScalar * finalVector.x), y: y + (smallestScalar * finalVector.y)}); // update with square moved in the vector direction for scalar amount
    finalSq = testSq;
    finalSq.x = x + (smallestScalar * finalVector.x);
    finalSq.y = y + (smallestScalar * finalVector.y);
    finalSq.rotation = testSq.rotation;
    //finalSq = squares.find(function(s) { return s.id === draggedID; });
    if (wouldCollide(finalSq, draggedID)) flushSquares(finalSq, draggedID, fallbackSq, arrayID); // repeat until no collisions
    else return finalSq;
    return fallbackSq;
}

// Get the square that it would collide with
function wouldCollideWith(testSq, excludeId) {
  let returnSq;
  flag = squares.some(sq => {
    if (sq.id === excludeId) return false;
    if (squaresOverlap(testSq, sq)) returnSq = sq;
  });
  return returnSq;
}

function dotProduct(v, u){ // returns dot product of two duples with elements x & y
  return ((v.x * u.x) + (v.y * u.y));
}

function onPointerUp(e) {
  if (!dragState) return;

  if (dragState.type === 'create') {
    ghost.style.display = 'none';

    if (isInsideBoardViewport(e.clientX, e.clientY)) {
      const pt = clientToBoard(e.clientX, e.clientY);
      addSquare(
        pt.x - dragState.createWidth / 2,
        pt.y - dragState.createHeight / 2,
        dragState.createWidth,
        dragState.createHeight
      );
    }
  } else if (dragState.type === 'move') {
    if (isInDeleteZone(e.clientX, e.clientY)) {
      pushUndoState();
      removeSquare(dragState.id);
    }

    const el = board.querySelector('[data-id="' + dragState.id + '"]');
    if (el) el.style.zIndex = '';

    deleteZone.classList.remove('active');
  } else if (dragState.type === 'rotate') {
    const el = board.querySelector('[data-id="' + dragState.id + '"]');
    if (el) el.style.zIndex = '';
  } else if (dragState.type === 'pan') {
    boardZoomContainer.classList.remove('panning');
  }

  dragState = null;
  updateAllSquareClasses();
}

function onDoubleClick(e) {
  if (dragState) return;

  const target = e.target.closest('.square');
  if (!target) return;

  const id = target.dataset.id;
  const sq = squares.find(function(s) { return s.id === id; });
  if (!sq) return;

  const newMode = sq.mode === 'move' ? 'rotate' : 'move';
  updateSquare(id, { mode: newMode });
  e.preventDefault();
}

function onWheel(e) {
  e.preventDefault();
  const rect = boardZoomContainer.getBoundingClientRect();
  const sx = e.clientX - rect.left;
  const sy = e.clientY - rect.top;
  const lx = (sx + panX) / zoom;
  const ly = (sy + panY) / zoom;
  const logDelta = -e.deltaY * ZOOM_SENSITIVITY;
  const newZoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, zoom * Math.pow(ZOOM_FACTOR, logDelta)));
  panX = lx * newZoom - sx;
  panY = ly * newZoom - sy;
  zoom = newZoom;
  applyTransform();
}

function isSquare(p) {
    if (p.length !== 4) return false;

    const d = [];
    for (let i = 0; i < p.length; i++) {
        for (let j = i + 1; j < p.length; j++) {
            const dx = p[i].x - p[j].x;
            const dy = p[i].y - p[j].y;
            d.push(dx * dx + dy * dy);
        }
    }

    d.sort((a, b) => a - b);

    const isClose = (a, b) => Math.abs(a - b) < 1e-5;

    return d[0] > 0 && 
           isClose(d[0], d[3]) && 
           isClose(d[4], d[5]) && 
           isClose(d[4], d[0] * 2);
} 

/* Event listener bindings */
boardZoomContainer.addEventListener('wheel', onWheel, { passive: false });

document.addEventListener('pointerdown', onPointerDown);
document.addEventListener('pointermove', onPointerMove);
document.addEventListener('pointerup', onPointerUp);
board.addEventListener('dblclick', onDoubleClick);

document.addEventListener('dragstart', function(e) { e.preventDefault(); });

/* Bounds card expand/collapse */
card.addEventListener('click', function() {
  this.classList.toggle('expanded');
  this.setAttribute('aria-expanded', this.classList.contains('expanded'));
  updateStats();
});

/* Delete all squares: show confirmation modal first */
deleteAllBtn.addEventListener('click', function (e) {
  e.preventDefault();
  e.stopPropagation();
  deleteAllSquares();
});

var fitUndoBtn = document.getElementById('fit-undo-btn');
var fitRedoBtn = document.getElementById('fit-redo-btn');
if (fitUndoBtn) {
  fitUndoBtn.addEventListener('click', function (e) { e.preventDefault(); fitUndo(); });
}
if (fitRedoBtn) {
  fitRedoBtn.addEventListener('click', function (e) { e.preventDefault(); fitRedo(); });
}

/* Toast helper */
var toastTimer = null;
function showToast(message, type) {
  var el = document.getElementById('fit-toast');
  var msgEl = document.getElementById('fit-toast-msg');
  var iconEl = document.getElementById('fit-toast-icon');
  if (!el) return;
  clearTimeout(toastTimer);
  el.removeAttribute('hidden');
  el.className = 'fit-toast toast-' + (type || 'info');
  msgEl.textContent = message;
  iconEl.textContent = type === 'success' ? '✓' : type === 'error' ? '✗' : 'ℹ';
  requestAnimationFrame(function() { el.classList.add('show'); });
  toastTimer = setTimeout(function() {
    el.classList.remove('show');
    setTimeout(function() { el.setAttribute('hidden', ''); }, 300);
  }, 4000);
}

/* Submit rules panel toggle */
var rulesPanel = document.getElementById('submit-rules');
var rulesVisible = false;

submitBtn.addEventListener('mouseenter', function() {
  if (rulesPanel && submitBtn.disabled) {
    rulesPanel.classList.add('visible');
    rulesVisible = true;
  }
});
submitBtn.addEventListener('mouseleave', function() {
  if (rulesPanel) {
    rulesPanel.classList.remove('visible');
    rulesVisible = false;
  }
});

/* Submit button */
submitBtn.addEventListener('click', async () => {
  const data = [];
  for (let sq of squares) {
    const corners = roundCornersForSubmit(getSquareCorners(sq));
    if (FIT_VARIANT === 'rectangle') {
      data.push({
        corners: corners,
        width: roundDecimal(getShapeWidthPx(sq), 10),
        height: roundDecimal(getShapeHeightPx(sq), 10)
      });
    } else {
      data.push(corners);
    }
  }
  if (FIT_VARIANT === 'square' && data.length < MIN_SQUARES) {
    showToast('Place at least ' + MIN_SQUARES + ' ' + FIT_SHAPE_PLURAL + ' to submit.', 'error');
    return;
  }
  if (FIT_VARIANT === 'square' && window.FIT_OPTIMAL_N && window.FIT_OPTIMAL_N.has(data.length)) {
    showToast('Solutions for ' + data.length + ' ' + fitShapeWord(data.length) + ' are already known optimal.', 'error');
    return;
  }
  submitBtn.disabled = true;
  var reasonEl = document.getElementById('submit-reason');
  if (reasonEl) reasonEl.textContent = 'Submitting…';
  try {
    const res = await fetch('/api/fit/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify({
         variant: (window.FIT_VARIANT || 'square'),
         squares: data
       })
    });
    if (res.ok) {
      const result = await res.json().catch(() => ({}));
      const remaining = res.headers.get('X-RateLimit-Remaining');
      var msg = result.message || 'Solution submitted!';
      if (remaining !== null) msg += ' (' + remaining + ' remaining)';
      showToast(msg, 'success');
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(err.error || 'Submission failed.', 'error');
    }
  } catch (e) {
    showToast('Network error, could not submit.', 'error');
  } finally {
    submitBtn.disabled = false;
    updateSubmitButtonState();
  }
});

/* Toolbar minimize/maximize toggle */
(function initToolbarMinimizeToggle() {
  var btn = document.getElementById('fit-toolbar-minimize-btn');
  var bottomBar = document.querySelector('aside.bottom-bar');
  if (!btn || !bottomBar) return;

  var iconEl = btn.querySelector('.toolbar-minimize-btn-icon');
  var textEl = btn.querySelector('.toolbar-minimize-btn-text');

  function update() {
    var minimized = bottomBar.classList.contains('is-minimized');
    btn.setAttribute('aria-expanded', minimized ? 'false' : 'true');
    if (iconEl) iconEl.textContent = minimized ? '+' : '−';
    if (textEl) textEl.textContent = minimized ? 'Expand' : 'Minimize';
  }

  function toggleToolbar(e) {
    e.preventDefault();
    bottomBar.classList.toggle('is-minimized');
    update();
  }

  btn.addEventListener('pointerup', toggleToolbar);
  btn.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' || e.key === ' ') {
      toggleToolbar(e);
    }
  });

  update();
})();
