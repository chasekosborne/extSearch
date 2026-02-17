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
      } else { // use Separating Axis Theorem to move sqaures flush
        console.log("OOGA");
        flushSquares(testSq, dragState.id, x, y); 
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

function flushSquares(testSq, draggedID, x, y){
    let collisionSq = wouldCollideWith(testSq, draggedID); // get square that is being collided with

    //console.log(collisionSq);
    //console.log(collisionSq.x);
    //console.log(collisionSq.y);

    // initializations
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
    updateSquare(draggedID, {x: x + (smallestScalar * finalVector.x), y: y + (smallestScalar * finalVector.y)}); // update with square moved in the vector direction for scalar amount
    finalSquare = squares.find(function(s) { return s.id === draggedID; });
    if (wouldCollide(finalSquare, draggedID)) flushSquares(finalSquare, draggedID, finalSquare.x, finalSquare.y); // repeat until no collisions
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
