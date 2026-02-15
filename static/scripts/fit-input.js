/**
 * Fit game: pointer/drag handling and event bindings.
 * Depends on: all other fit-*.js (constants, geometry, transform, squares, square-data).
 */

function isInDeleteZone(clientX, clientY) {
  const rect = deleteZone.getBoundingClientRect();
  return clientX >= rect.left && clientX <= rect.right &&
         clientY >= rect.top && clientY <= rect.bottom;
}

function onPointerDown(e) {
  const target = e.target.closest('.square');
  const isSource = e.target.closest('#source');
  const isPopup = e.target.closest('#square-data');
  const isBoard = e.target.closest('#board') && !target && !isPopup;

  if (isSource) {
    dragState = { type: 'create', startX: e.clientX, startY: e.clientY };
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
      }
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

function onPointerUp(e) {
  if (!dragState) return;

  if (dragState.type === 'create') {
    ghost.style.display = 'none';

    if (isInsideBoardViewport(e.clientX, e.clientY)) {
      const pt = clientToBoard(e.clientX, e.clientY);
      addSquare(pt.x - SQUARE_SIZE / 2, pt.y - SQUARE_SIZE / 2);
    }
  } else if (dragState.type === 'move') {
    if (isInDeleteZone(e.clientX, e.clientY)) {
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

/* Submit button */
submitBtn.addEventListener('click', async () => {
  const data = [];
  for (let sq of squares) {
    data.push(roundCornersForSubmit(getSquareCorners(sq)));
  }
  if (data.length === 0) {
    return;
  }
  if (window.FIT_OPTIMAL_N && window.FIT_OPTIMAL_N.has(data.length)) {
    return;
  }
  submitBtn.disabled = true;
  try {
    const res = await fetch('/api/fit/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ squares: data })
    });
    if (res.ok) {
      const result = await res.json().catch(() => ({}));
      if (result.message) {
        alert(result.message);
      }
    } else {
      const err = await res.json().catch(() => ({}));
      alert(err.error || 'Submission failed.');
    }
  } finally {
    submitBtn.disabled = false;
  }
});
