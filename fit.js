const board = document.getElementById('board');
const source = document.getElementById('source');
const ghost = document.getElementById('ghost');
const deleteZone = document.getElementById('delete-zone');
const statCount = document.getElementById('stat-count');
const statBounds = document.getElementById('stat-bounds');

const SQUARE_SIZE = 56;
let squares = [];
let dragState = null;
let idCounter = 0;

function getBoardSize() {
  const rect = board.getBoundingClientRect();
  return { width: rect.width, height: rect.height };
}

function updateStats() {
  statCount.textContent = squares.length;
  
  if (squares.length === 0) {
    statBounds.textContent = '—';
    return;
  }
  
  let minX = Infinity, minY = Infinity;
  let maxX = -Infinity, maxY = -Infinity;
  
  squares.forEach(sq => {
    minX = Math.min(minX, sq.x);
    minY = Math.min(minY, sq.y);
    maxX = Math.max(maxX, sq.x + SQUARE_SIZE);
    maxY = Math.max(maxY, sq.y + SQUARE_SIZE);
  });
  
  const w = maxX - minX;
  const h = maxY - minY;
  statBounds.textContent = w + ' × ' + h;
}

function createSquareEl(sq) {
  const el = document.createElement('div');
  el.className = 'square' + (sq.mode === 'rotate' ? ' mode-rotate' : '');
  el.dataset.id = sq.id;
  el.style.left = sq.x + 'px';
  el.style.top = sq.y + 'px';
  el.style.transform = 'rotate(' + sq.rotation + 'deg)';
  el.innerHTML = '<span class="square-label">' + sq.mode + '</span>';
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
  squares.push(sq);
  board.appendChild(createSquareEl(sq));
  updateStats();
}

function removeSquare(id) {
  squares = squares.filter(function(s) { return s.id !== id; });
  const el = board.querySelector('[data-id="' + id + '"]');
  if (el) el.remove();
  updateStats();
}

function updateSquare(id, updates) {
  const sq = squares.find(function(s) { return s.id === id; });
  if (!sq) return;
  Object.assign(sq, updates);
  
  const el = board.querySelector('[data-id="' + id + '"]');
  if (!el) return;
  
  el.style.left = sq.x + 'px';
  el.style.top = sq.y + 'px';
  el.style.transform = 'rotate(' + sq.rotation + 'deg)';
  el.className = 'square' + (sq.mode === 'rotate' ? ' mode-rotate' : '');
  el.innerHTML = '<span class="square-label">' + sq.mode + '</span>';
  updateStats();
}

function isInDeleteZone(clientX, clientY) {
  const rect = deleteZone.getBoundingClientRect();
  return clientX >= rect.left && clientX <= rect.right &&
         clientY >= rect.top && clientY <= rect.bottom;
}

function onPointerDown(e) {
  const target = e.target.closest('.square');
  const isSource = e.target.closest('#source');
  
  if (isSource) {
    dragState = { type: 'create', startX: e.clientX, startY: e.clientY };
    ghost.style.display = 'block';
    ghost.style.left = (e.clientX - SQUARE_SIZE / 2) + 'px';
    ghost.style.top = (e.clientY - SQUARE_SIZE / 2) + 'px';
    e.preventDefault();
  } else if (target) {
    const id = target.dataset.id;
    const sq = squares.find(function(s) { return s.id === id; });
    if (!sq) return;
    
    if (sq.mode === 'rotate') {
      if (!dragState) {
        updateSquare(id, { rotation: (sq.rotation + 90) % 360 });
      }
    } else {
      const rect = board.getBoundingClientRect();
      dragState = {
        type: 'move',
        id: id,
        offsetX: e.clientX - rect.left - sq.x,
        offsetY: e.clientY - rect.top - sq.y
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
    const rect = board.getBoundingClientRect();
    const boardSize = getBoardSize();
    let x = e.clientX - rect.left - dragState.offsetX;
    let y = e.clientY - rect.top - dragState.offsetY;
    
    x = Math.max(0, Math.min(x, boardSize.width - SQUARE_SIZE));
    y = Math.max(0, Math.min(y, boardSize.height - SQUARE_SIZE));
    
    updateSquare(dragState.id, { x: x, y: y });
    
    if (isInDeleteZone(e.clientX, e.clientY)) {
      deleteZone.classList.add('active');
    } else {
      deleteZone.classList.remove('active');
    }
  }
}

function onPointerUp(e) {
  if (!dragState) return;
  
  if (dragState.type === 'create') {
    ghost.style.display = 'none';
    
    const rect = board.getBoundingClientRect();
    if (e.clientX >= rect.left && e.clientX <= rect.right &&
        e.clientY >= rect.top && e.clientY <= rect.bottom) {
      const x = e.clientX - rect.left - SQUARE_SIZE / 2;
      const y = e.clientY - rect.top - SQUARE_SIZE / 2;
      addSquare(x, y);
    }
  } else if (dragState.type === 'move') {
    if (isInDeleteZone(e.clientX, e.clientY)) {
      removeSquare(dragState.id);
    }
    
    const el = board.querySelector('[data-id="' + dragState.id + '"]');
    if (el) el.style.zIndex = '';
    
    deleteZone.classList.remove('active');
  }
  
  dragState = null;
}

function onClick(e) {
  if (dragState) return;
  
  const target = e.target.closest('.square');
  if (!target) return;
  
  const id = target.dataset.id;
  const sq = squares.find(function(s) { return s.id === id; });
  if (!sq) return;
  
  const newMode = sq.mode === 'move' ? 'rotate' : 'move';
  updateSquare(id, { mode: newMode });
}

document.addEventListener('pointerdown', onPointerDown);
document.addEventListener('pointermove', onPointerMove);
document.addEventListener('pointerup', onPointerUp);
board.addEventListener('click', onClick);

document.addEventListener('dragstart', function(e) { e.preventDefault(); });

