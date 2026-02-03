const board = document.getElementById('board');
const boardZoomContainer = document.getElementById('board-zoom-container');
const boardTransform = document.getElementById('board-transform');
const source = document.getElementById('source');
const ghost = document.getElementById('ghost');
const deleteZone = document.getElementById('delete-zone');
const statCount = document.getElementById('stat-count');
const statBounds = document.getElementById('stat-bounds');
const boundingBox = document.getElementById('bounding-box');
const squareData = document.getElementById('square-data');

const SQUARE_SIZE = 56;
const BOARD_SIZE = 10000;
const BOARD_CENTER = BOARD_SIZE / 2;
const ZOOM_MIN = 0.05;
const ZOOM_MAX = 4;
const ZOOM_SENSITIVITY = 0.003;

let squares = [];
let dragState = null;
let selectedSquareId = null;
let idCounter = 0;
let zoom = 1;
let panX = 0;
let panY = 0;

function applyTransform() {
  boardTransform.style.transform = `translate(${panX}px, ${panY}px) scale(${zoom})`;
}

function centerViewOnGrid() {
  const rect = boardZoomContainer.getBoundingClientRect();
  panX = rect.width / 2 - BOARD_CENTER * zoom;
  panY = rect.height / 2 - BOARD_CENTER * zoom;
  applyTransform();
}

/** Convert client coords to logical board coords. */
function clientToBoard(clientX, clientY) {
  const rect = boardZoomContainer.getBoundingClientRect();
  const sx = clientX - rect.left;
  const sy = clientY - rect.top;
  return {
    x: (sx - panX) / zoom,
    y: (sy - panY) / zoom
  };
}

/** Check if client coords are inside the board viewport (for drop/create). */
function isInsideBoardViewport(clientX, clientY) {
  const rect = boardZoomContainer.getBoundingClientRect();
  return clientX >= rect.left && clientX <= rect.right &&
         clientY >= rect.top && clientY <= rect.bottom;
}

function getBoardSize() {
  return { width: BOARD_SIZE, height: BOARD_SIZE };
}

// Calculate the bounding box of a rotated square
function getRotatedSquareBounds(sq) {
  const centerX = sq.x + SQUARE_SIZE / 2;
  const centerY = sq.y + SQUARE_SIZE / 2;
  const angle = sq.rotation * Math.PI / 180;
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);
  const halfSize = SQUARE_SIZE / 2;
  
  // Calculate the four corners of the rotated square
  const corners = [
    { x: -halfSize, y: -halfSize },
    { x: halfSize, y: -halfSize },
    { x: halfSize, y: halfSize },
    { x: -halfSize, y: halfSize }
  ].map(corner => ({
    x: centerX + corner.x * cos - corner.y * sin,
    y: centerY + corner.x * sin + corner.y * cos
  }));
  
  // Find the axis-aligned bounding box
  let minX = Infinity, minY = Infinity;
  let maxX = -Infinity, maxY = -Infinity;
  
  corners.forEach(corner => {
    minX = Math.min(minX, corner.x);
    minY = Math.min(minY, corner.y);
    maxX = Math.max(maxX, corner.x);
    maxY = Math.max(maxY, corner.y);
  });
  
  return { minX, minY, maxX, maxY };
}

function updateStats() {
  statCount.textContent = squares.length;
  
  if (squares.length === 0) {
    statBounds.textContent = '—';
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
  
  const w = (maxX - minX) / SQUARE_SIZE;
  const h = (maxY - minY) / SQUARE_SIZE;
  
  // Use the largest side length to make it a square
  const maxSide = Math.max(w, h);
  
  // Display with high precision (up to 3 decimal places)
  const maxSideStr = maxSide.toFixed(3).replace(/\.?0+$/, '');
  statBounds.textContent = maxSideStr + ' × ' + maxSideStr;
  
  // Update visual bounding box as a square
  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;
  const squareSize = maxSide * SQUARE_SIZE;
  const halfSize = squareSize / 2;
  
  boundingBox.style.display = 'block';
  boundingBox.style.left = (centerX - halfSize) + 'px';
  boundingBox.style.top = (centerY - halfSize) + 'px';
  boundingBox.style.width = squareSize + 'px';
  boundingBox.style.height = squareSize + 'px';
}

function createSquareEl(sq) {
  const el = document.createElement('div');
  let className = 'square';
  if (sq.mode === 'rotate') {
    className += ' mode-rotate';
  }
  el.className = className;
  el.dataset.id = sq.id;
  el.style.left = sq.x + 'px';
  el.style.top = sq.y + 'px';
  el.style.transform = 'rotate(' + sq.rotation + 'deg)';
  return el;
}

function addSquare(x, y) {
  const boardSize = getBoardSize();
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

/* Delete all stuff 8 */
const deleteAllBtn = document.getElementById('delete-all');

function deleteAllSquares() {
  // Clear data model
  squares.length = 0;

  // Remove square DOM elements
  board.querySelectorAll('.square').forEach(el => el.remove());

  // Reset selection
  selectedSquareId = null;
  dragState = null;

  // Hide data popup
  squareData.style.display = 'none';

  // Reset bounding box + stats
  boundingBox.style.display = 'none';
  updateStats();
}
/* Ends here */

function updateSquare(id, updates) {
  const sq = squares.find(function(s) { return s.id === id; });
  if (!sq) return;
  Object.assign(sq, updates);
  
  const el = board.querySelector('[data-id="' + id + '"]');
  if (!el) return;
  
  el.style.left = sq.x + 'px';
  el.style.top = sq.y + 'px';
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

function formatSquareUnit(v) {
  return Number(v).toFixed(3).replace(/\.?0+$/, '') || '0';
}
function formatRotation(v) {
  return Number(v).toFixed(1).replace(/\.?0+$/, '') || '0';
}

function pixelToCenterX(xPx) { return (xPx - BOARD_CENTER) / SQUARE_SIZE; }
function pixelToCenterY(yPx) { return (yPx - BOARD_CENTER) / SQUARE_SIZE; }
function centerToPixelX(cx) { return BOARD_CENTER + cx * SQUARE_SIZE; }
function centerToPixelY(cy) { return BOARD_CENTER + cy * SQUARE_SIZE; }

function applySquareDataInputs() {
  if (!selectedSquareId) return;
  const sq = squares.find(function(s) { return s.id === selectedSquareId; });
  if (!sq) return;
  const xIn = squareData.querySelector('.data-input-x');
  const yIn = squareData.querySelector('.data-input-y');
  const rotIn = squareData.querySelector('.data-input-rotation');
  if (!xIn || !yIn || !rotIn) return;

  const cxVal = parseFloat(xIn.value);
  const cyVal = parseFloat(yIn.value);
  const rotVal = parseFloat(rotIn.value);
  if (Number.isNaN(cxVal) || Number.isNaN(cyVal) || Number.isNaN(rotVal)) {
    xIn.value = formatSquareUnit(pixelToCenterX(sq.x));
    yIn.value = formatSquareUnit(pixelToCenterY(sq.y));
    rotIn.value = formatRotation(sq.rotation);
    squareData.classList.add('data-error');
    setTimeout(function() { squareData.classList.remove('data-error'); }, 600);
    return;
  }

  const boardSize = getBoardSize();
  const xPx = Math.max(0, Math.min(centerToPixelX(cxVal), boardSize.width - SQUARE_SIZE));
  const yPx = Math.max(0, Math.min(centerToPixelY(cyVal), boardSize.height - SQUARE_SIZE));
  let rotation = ((rotVal % 360) + 360) % 360;
  const testSq = { x: xPx, y: yPx, rotation: rotation };
  if (wouldCollide(testSq, selectedSquareId)) {
    xIn.value = formatSquareUnit(pixelToCenterX(sq.x));
    yIn.value = formatSquareUnit(pixelToCenterY(sq.y));
    rotIn.value = formatRotation(sq.rotation);
    squareData.classList.add('data-error');
    setTimeout(function() { squareData.classList.remove('data-error'); }, 600);
    return;
  }

  updateSquare(selectedSquareId, { x: xPx, y: yPx, rotation: rotation });
}

function setupSquareDataInputHandlers() {
  const xIn = squareData.querySelector('.data-input-x');
  const yIn = squareData.querySelector('.data-input-y');
  const rotIn = squareData.querySelector('.data-input-rotation');
  if (!xIn || !yIn || !rotIn) return;
  function onApply() { applySquareDataInputs(); }
  function onKey(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      onApply();
    }
  }
  [xIn, yIn, rotIn].forEach(function(inp) {
    inp.addEventListener('blur', onApply);
    inp.addEventListener('keydown', onKey);
  });
}

function updateSquareDataDisplay() {
  if (!selectedSquareId) {
    squareData.style.display = 'none';
    return;
  }

  const sq = squares.find(function(s) { return s.id === selectedSquareId; });
  if (!sq) {
    squareData.style.display = 'none';
    return;
  }

  const cx = formatSquareUnit(pixelToCenterX(sq.x));
  const cy = formatSquareUnit(pixelToCenterY(sq.y));
  const rotation = formatRotation(sq.rotation);

  squareData.innerHTML = `
    <div class="data-label">Position (from center)</div>
    <div class="data-row">
      <label>x</label>
      <input type="text" class="data-input data-input-x" value="${cx}" inputmode="decimal" />
      <label>y</label>
      <input type="text" class="data-input data-input-y" value="${cy}" inputmode="decimal" />
    </div>
    <div class="data-label">Rotation</div>
    <div class="data-row">
      <input type="text" class="data-input data-input-rotation" value="${rotation}" inputmode="decimal" />
      <span class="data-unit">°</span>
    </div>
  `;
  setupSquareDataInputHandlers();

  const boardSize = getBoardSize();
  const squareCenterX = sq.x + SQUARE_SIZE / 2;
  const squareCenterY = sq.y + SQUARE_SIZE / 2;
  const dataWidth = 180;
  const dataHeight = 88;
  const padding = 10;

  const positions = [
    { x: squareCenterX + SQUARE_SIZE / 2 + padding, y: squareCenterY - dataHeight / 2 },
    { x: squareCenterX - SQUARE_SIZE / 2 - padding - dataWidth, y: squareCenterY - dataHeight / 2 },
    { x: squareCenterX - dataWidth / 2, y: sq.y - dataHeight - padding },
    { x: squareCenterX - dataWidth / 2, y: sq.y + SQUARE_SIZE + padding }
  ];

  let bestPosition = positions[0];
  for (let pos of positions) {
    if (pos.x < 0 || pos.x + dataWidth > boardSize.width ||
        pos.y < 0 || pos.y + dataHeight > boardSize.height) continue;
    let overlaps = false;
    for (let otherSq of squares) {
      if (otherSq.id === selectedSquareId) continue;
      const bounds = getRotatedSquareBounds(otherSq);
      if (pos.x < bounds.maxX && pos.x + dataWidth > bounds.minX &&
          pos.y < bounds.maxY && pos.y + dataHeight > bounds.minY) {
        overlaps = true;
        break;
      }
    }
    if (!overlaps) {
      bestPosition = pos;
      break;
    }
  }

  squareData.style.display = 'block';
  squareData.style.left = bestPosition.x + 'px';
  squareData.style.top = bestPosition.y + 'px';
}

// Get the four corners of a rotated square
function getSquareCorners(sq) {
  const centerX = sq.x + SQUARE_SIZE / 2;
  const centerY = sq.y + SQUARE_SIZE / 2;
  const angle = sq.rotation * Math.PI / 180;
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);
  const halfSize = SQUARE_SIZE / 2;
  
  return [
    { x: centerX + (-halfSize) * cos - (-halfSize) * sin, y: centerY + (-halfSize) * sin + (-halfSize) * cos },
    { x: centerX + halfSize * cos - (-halfSize) * sin, y: centerY + halfSize * sin + (-halfSize) * cos },
    { x: centerX + halfSize * cos - halfSize * sin, y: centerY + halfSize * sin + halfSize * cos },
    { x: centerX + (-halfSize) * cos - halfSize * sin, y: centerY + (-halfSize) * sin + halfSize * cos }
  ];
}

// Check if a point is inside a rotated square
function pointInRotatedSquare(point, sq) {
  const corners = getSquareCorners(sq);
  const centerX = sq.x + SQUARE_SIZE / 2;
  const centerY = sq.y + SQUARE_SIZE / 2;
  const angle = -sq.rotation * Math.PI / 180; // Reverse rotation
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);
  
  // Transform point to square's local space
  const dx = point.x - centerX;
  const dy = point.y - centerY;
  const localX = dx * cos - dy * sin;
  const localY = dx * sin + dy * cos;
  
  const halfSize = SQUARE_SIZE / 2;
  return Math.abs(localX) <= halfSize && Math.abs(localY) <= halfSize;
}

// Check if two rotated squares overlap using SAT (Separating Axis Theorem)
function squaresOverlap(sq1, sq2) {
  // Quick AABB check first
  const bounds1 = getRotatedSquareBounds(sq1);
  const bounds2 = getRotatedSquareBounds(sq2);
  
  if (bounds1.maxX <= bounds2.minX || bounds2.maxX <= bounds1.minX ||
      bounds1.maxY <= bounds2.minY || bounds2.maxY <= bounds1.minY) {
    return false;
  }
  
  // More precise check: check if any corner of one square is inside the other
  const corners1 = getSquareCorners(sq1);
  const corners2 = getSquareCorners(sq2);
  
  // Check if any corner of sq1 is inside sq2
  for (let i = 0; i < corners1.length; i++) {
    if (pointInRotatedSquare(corners1[i], sq2)) {
      return true;
    }
  }
  
  // Check if any corner of sq2 is inside sq1
  for (let i = 0; i < corners2.length; i++) {
    if (pointInRotatedSquare(corners2[i], sq1)) {
      return true;
    }
  }
  
  // Check if edges intersect (simplified: check if squares are very close)
  // This handles edge cases where squares might overlap without corners inside
  const center1 = { x: sq1.x + SQUARE_SIZE / 2, y: sq1.y + SQUARE_SIZE / 2 };
  const center2 = { x: sq2.x + SQUARE_SIZE / 2, y: sq2.y + SQUARE_SIZE / 2 };
  const dist = Math.sqrt(Math.pow(center1.x - center2.x, 2) + Math.pow(center1.y - center2.y, 2));
  
  // If centers are closer than diagonal of one square, they might overlap
  const diagonal = SQUARE_SIZE * Math.sqrt(2);
  if (dist < diagonal) {
    // More thorough check: sample points along edges
    const edges1 = [
      [corners1[0], corners1[1]],
      [corners1[1], corners1[2]],
      [corners1[2], corners1[3]],
      [corners1[3], corners1[0]]
    ];
    
    for (let edge of edges1) {
      const midPoint = {
        x: (edge[0].x + edge[1].x) / 2,
        y: (edge[0].y + edge[1].y) / 2
      };
      if (pointInRotatedSquare(midPoint, sq2)) {
        return true;
      }
    }
  }
  
  return false;
}

// Check if a square at given position/rotation would collide with any other square
function wouldCollide(testSq, excludeId) {
  return squares.some(sq => {
    if (sq.id === excludeId) return false;
    return squaresOverlap(testSq, sq);
  });
}

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
    // Clicking on board deselects
    selectedSquareId = null;
    updateAllSquareClasses();
    updateSquareDataDisplay();
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
  } else if (dragState.type === 'move') {
    const pt = clientToBoard(e.clientX, e.clientY);
    const boardSize = getBoardSize();
    let x = pt.x - dragState.offsetX;
    let y = pt.y - dragState.offsetY;
    
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
  const lx = (sx - panX) / zoom;
  const ly = (sy - panY) / zoom;
  const delta = -e.deltaY * ZOOM_SENSITIVITY;
  const newZoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, zoom + delta));
  panX += lx * (zoom - newZoom);
  panY += ly * (zoom - newZoom);
  zoom = newZoom;
  applyTransform();
}

boardZoomContainer.addEventListener('wheel', onWheel, { passive: false });

document.addEventListener('pointerdown', onPointerDown);
document.addEventListener('pointermove', onPointerMove);
document.addEventListener('pointerup', onPointerUp);
board.addEventListener('dblclick', onDoubleClick);


document.addEventListener('dragstart', function(e) { e.preventDefault(); });


/* Delete all squares */
deleteAllBtn.addEventListener('click', deleteAllSquares);
requestAnimationFrame(function() { centerViewOnGrid(); });

