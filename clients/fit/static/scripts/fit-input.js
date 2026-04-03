/**
 * Fit game: pointer/drag handling and event bindings.
 * Depends on: all other fit-*.js (constants, geometry, transform, squares, square-data).
 */

var FIT_MOBILE = typeof window !== 'undefined' && !!window.FIT_MOBILE;

/** Board-background pointers (for two-finger pinch zoom on touch). */
var fitMobileBoardPointers = new Map();
/** { id1, id2, lastDist } or null */
var fitPinchState = null;

function fitBeginMobilePinch() {
  if (!FIT_MOBILE || fitPinchState || fitMobileBoardPointers.size < 2) return;
  var ids = Array.from(fitMobileBoardPointers.keys());
  var p0 = fitMobileBoardPointers.get(ids[0]);
  var p1 = fitMobileBoardPointers.get(ids[1]);
  var d = Math.hypot(p0.clientX - p1.clientX, p0.clientY - p1.clientY);
  if (d < 8) return;
  if (dragState && dragState.type === 'pan') {
    try {
      boardZoomContainer.releasePointerCapture(dragState.capturePointerId);
    } catch (err) {}
    boardZoomContainer.classList.remove('panning');
    dragState = null;
  }
  fitPinchState = { id1: ids[0], id2: ids[1], lastDist: d };
}

function fitApplyMobilePinchZoom() {
  if (!fitPinchState) return;
  var p0 = fitMobileBoardPointers.get(fitPinchState.id1);
  var p1 = fitMobileBoardPointers.get(fitPinchState.id2);
  if (!p0 || !p1) return;
  var d = Math.hypot(p0.clientX - p1.clientX, p0.clientY - p1.clientY);
  if (d <= 1 || fitPinchState.lastDist <= 1) return;
  var rect = boardZoomContainer.getBoundingClientRect();
  var sx = (p0.clientX + p1.clientX) / 2 - rect.left;
  var sy = (p0.clientY + p1.clientY) / 2 - rect.top;
  var ratio = d / fitPinchState.lastDist;
  fitPinchState.lastDist = d;
  var lx = (sx + panX) / zoom;
  var ly = (sy + panY) / zoom;
  var newZoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, zoom * ratio));
  panX = lx * newZoom - sx;
  panY = ly * newZoom - sy;
  zoom = newZoom;
  applyTransform();
}

function fitSetPointerCapture(el, e) {
  if (!el || e.pointerId === undefined) return;
  try {
    el.setPointerCapture(e.pointerId);
  } catch (err) {}
}

function fitReleaseDragPointerCapture(e) {
  if (!dragState || dragState.capturePointerId !== e.pointerId || !dragState.captureEl) return;
  try {
    dragState.captureEl.releasePointerCapture(e.pointerId);
  } catch (err) {}
}

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
  let x = snapPos(clipboard.x + 20);
  let y = snapPos(clipboard.y + 20);
  x = Math.max(0, Math.min(x, boardSize.width - SQUARE_SIZE));
  y = Math.max(0, Math.min(y, boardSize.height - SQUARE_SIZE));
  const newSquare = {
    id: 'sq-' + (++idCounter),
    x: x,
    y: y,
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
    dragState = {
      type: 'create',
      startX: e.clientX,
      startY: e.clientY,
      captureEl: source,
      capturePointerId: e.pointerId
    };
    fitSetPointerCapture(source, e);
    ghost.style.display = 'block';
    ghost.style.left = (e.clientX - SQUARE_SIZE / 2) + 'px';
    ghost.style.top = (e.clientY - SQUARE_SIZE / 2) + 'px';
    selectedSquareId = null;
    updateAllSquareClasses();
    updateSquareDataDisplay();
    e.preventDefault();
  } else if (isBoard) {
    if (FIT_MOBILE) {
      fitMobileBoardPointers.set(e.pointerId, { clientX: e.clientX, clientY: e.clientY });
      fitBeginMobilePinch();
      if (fitPinchState) {
        e.preventDefault();
        return;
      }
      if (fitMobileBoardPointers.size >= 2) {
        e.preventDefault();
        return;
      }
    }
    selectedSquareId = null;
    updateAllSquareClasses();
    updateSquareDataDisplay();
    dragState = {
      type: 'pan',
      startClientX: e.clientX,
      startClientY: e.clientY,
      startPanX: panX,
      startPanY: panY,
      captureEl: boardZoomContainer,
      capturePointerId: e.pointerId
    };
    fitSetPointerCapture(boardZoomContainer, e);
    boardZoomContainer.classList.add('panning');
    e.preventDefault();
  } else if (target) {
    const id = target.dataset.id;
    const sq = squares.find(function(s) { return s.id === id; });
    if (!sq) return;

    if (FIT_MOBILE) {
      sq.mode = 'move';
    }

    pushUndoState();

    if (multiEnable){
      //if (!selectedSquares) selectedSquares.push(id)
      if (selectedSquares.indexOf(id) == -1) selectedSquares.push(id);
      updateAllSquareClasses();
      updateSquareDataDisplay();

      const pt = clientToBoard(e.clientX, e.clientY);
        dragState = {
          type: 'move',
          id: id,
          offsetX: pt.x - sq.x,
          offsetY: pt.y - sq.y,
          captureEl: target,
          capturePointerId: e.pointerId
        };

        offsets.length = 0; // clear the array
        for (temp of selectedSquares){
          offsetSq = squares.find(function(s) { return s.id === temp; });
          offsets.push({x: pt.x - offsetSq.x , y: pt.y - offsetSq.y});
        }
        //console.log(offsets[0].x);

        fitSetPointerCapture(target, e);
        target.style.zIndex = 100;
        e.preventDefault();

    }else{
      selectedSquares.length = 0;
      offsets.length = 0;
      // Select the square
      selectedSquareId = id;
      updateAllSquareClasses();
      updateSquareDataDisplay();

      if (sq.mode === 'rotate') {
        const pt = clientToBoard(e.clientX, e.clientY);
        const centerX = sq.x + SQUARE_SIZE / 2;
        const centerY = sq.y + SQUARE_SIZE / 2;
        const startAngle = Math.atan2(pt.y - centerY, pt.x - centerX);
        dragState = {
          type: 'rotate',
          id: id,
          startAngle: startAngle,
          startRotation: sq.rotation,
          captureEl: target,
          capturePointerId: e.pointerId
        };
        fitSetPointerCapture(target, e);
        target.style.zIndex = 100;
        e.preventDefault();
      } else {
        const pt = clientToBoard(e.clientX, e.clientY);
        dragState = {
          type: 'move',
          id: id,
          offsetX: pt.x - sq.x,
          offsetY: pt.y - sq.y,
          captureEl: target,
          capturePointerId: e.pointerId
        };
        fitSetPointerCapture(target, e);
        target.style.zIndex = 100;
        e.preventDefault();
    }
    }
  }
}

function onPointerMove(e) {
  if (FIT_MOBILE && fitMobileBoardPointers.has(e.pointerId)) {
    fitMobileBoardPointers.set(e.pointerId, { clientX: e.clientX, clientY: e.clientY });
  }

  if (FIT_MOBILE && !fitPinchState && fitMobileBoardPointers.size >= 2) {
    fitBeginMobilePinch();
  }

  if (FIT_MOBILE && fitPinchState &&
      fitMobileBoardPointers.has(fitPinchState.id1) &&
      fitMobileBoardPointers.has(fitPinchState.id2)) {
    fitApplyMobilePinchZoom();
    e.preventDefault();
    return;
  }

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
    if (multiEnable){
      let count = 0;
      for (id of selectedSquares){
        let pt = clientToBoard(e.clientX, e.clientY);
        const boardSize = getBoardSize();

        let sq = squares.find(function(s) { return s.id === id; })

        let x = snapPos(pt.x - (offsets[count].x));
        let y = snapPos(pt.y - (offsets[count].y));
        count += 1;

        x = Math.max(0, Math.min(x, boardSize.width - SQUARE_SIZE));
        y = Math.max(0, Math.min(y, boardSize.height - SQUARE_SIZE));

        // Check for collisions before updating
        if (sq) {
          const testSq = { x: x, y: y, rotation: sq.rotation };
          if (!wouldCollide(testSq, id)) {
            updateSquare(id, { x: x, y: y });
          } else { // use Separating Axis Theorem to move sqaures flush
            updateSq = flushSquares(testSq, id);
            updateSquare(id, { x: updateSq.x, y: updateSq.y });
          }
        }
      }
    }else{
      let pt = clientToBoard(e.clientX, e.clientY);
      const boardSize = getBoardSize();
      let x = snapPos(pt.x - dragState.offsetX);
      let y = snapPos(pt.y - dragState.offsetY);

      x = Math.max(0, Math.min(x, boardSize.width - SQUARE_SIZE));
      y = Math.max(0, Math.min(y, boardSize.height - SQUARE_SIZE));

      // Check for collisions before updating
      const sq = squares.find(function(s) { return s.id === dragState.id; });
      if (sq) {
        const testSq = { x: x, y: y, rotation: sq.rotation };
        if (!wouldCollide(testSq, dragState.id)) {
          updateSquare(dragState.id, { x: x, y: y });
        } else { // use Separating Axis Theorem to move sqaures flush
          updateSq = flushSquares(testSq, dragState.id);
          updateSquare(dragState.id, { x: updateSq.x, y: updateSq.y });
        }
      }

      if (isInDeleteZone(e.clientX, e.clientY)) {
        deleteZone.classList.add('active');
      } else {
        deleteZone.classList.remove('active');
      }
  }
  } else if (dragState.type === 'rotate') {
    const pt = clientToBoard(e.clientX, e.clientY);
    const sq = squares.find(function(s) { return s.id === dragState.id; });
    if (!sq) return;

    const centerX = sq.x + SQUARE_SIZE / 2;
    const centerY = sq.y + SQUARE_SIZE / 2;
    const currentAngle = Math.atan2(pt.y - centerY, pt.x - centerX);

    const angleDiff = currentAngle - dragState.startAngle;
    const rotationDiff = angleDiff * (180 / Math.PI);
    let newRotation = dragState.startRotation + rotationDiff;
    newRotation = snapRotation(newRotation);

    // Normalize to 0-360 range
    newRotation = ((newRotation % 360) + 360) % 360;

    // Check for collisions before updating
    const testSq = { x: sq.x, y: sq.y, rotation: newRotation };
    if (!wouldCollide(testSq, dragState.id)) {
      updateSquare(dragState.id, { rotation: newRotation });
    }
  }
}

function flushSquares(testSq, draggedID, fallbackSq = { x: 0, y: 0 }, arrayID = new Array()){
    let collisionSq = wouldCollideWith(testSq, draggedID); // get square that is being collided with

    if (fallbackSq.x == 0 && fallbackSq.y == 0){
      tempSq = squares.find(function(s) { return s.id === draggedID; });
      fallbackSq.x = tempSq.x;
      fallbackSq.y = tempSq.y;
    }

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
  if (FIT_MOBILE) {
    fitMobileBoardPointers.delete(e.pointerId);
    if (fitPinchState && (e.pointerId === fitPinchState.id1 || e.pointerId === fitPinchState.id2)) {
      fitPinchState = null;
    }
  }

  if (!dragState) return;

  fitReleaseDragPointerCapture(e);

  if (dragState.type === 'create') {
    ghost.style.display = 'none';

    if (isInsideBoardViewport(e.clientX, e.clientY)) {
      const pt = clientToBoard(e.clientX, e.clientY);
      addSquare(pt.x - SQUARE_SIZE / 2, pt.y - SQUARE_SIZE / 2);
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
  if (FIT_MOBILE) return;

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

/* Event listener bindings */
boardZoomContainer.addEventListener('wheel', onWheel, { passive: false });

document.addEventListener('pointerdown', onPointerDown);
document.addEventListener('pointermove', onPointerMove);
document.addEventListener('pointerup', onPointerUp);
document.addEventListener('pointercancel', onPointerUp);
board.addEventListener('dblclick', onDoubleClick);

document.addEventListener('dragstart', function(e) { e.preventDefault(); });

/* Bounds card expand/collapse */
if (card) {
  card.addEventListener('click', function() {
    this.classList.toggle('expanded');
    this.setAttribute('aria-expanded', this.classList.contains('expanded'));
    updateStats();
  });
}

/* Delete all squares: show confirmation modal first */
if (deleteAllBtn) {
  deleteAllBtn.addEventListener('click', function (e) {
    e.preventDefault();
    e.stopPropagation();
    deleteAllSquares();
  });
}

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

if (submitBtn) {
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
      data.push(roundCornersForSubmit(getSquareCorners(sq)));
    }
    if (data.length < MIN_SQUARES) {
      showToast('Place at least ' + MIN_SQUARES + ' squares to submit.', 'error');
      return;
    }
    if (window.FIT_OPTIMAL_N && window.FIT_OPTIMAL_N.has(data.length)) {
      showToast('Solutions for ' + data.length + ' squares are already known optimal.', 'error');
      return;
    }
    submitBtn.disabled = true;
    var reasonEl = document.getElementById('submit-reason');
    if (reasonEl) reasonEl.textContent = 'Submitting…';
    try {
      const res = await fetch('/api/fit/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ squares: data })
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
}

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
