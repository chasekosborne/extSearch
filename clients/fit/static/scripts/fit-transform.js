/**
 * Fit game: pan/zoom and coordinate conversion.
 * Depends on: fit-constants.js, fit-geometry.js (updateStats, updateSquareDataDisplay used by applyTransform).
 */

/**
 * Apply pan and zoom. Uses "content at zoom resolution": board and all content
 * are drawn at zoom× size (no CSS scale), so rendering stays crisp at high zoom.
 * panX/panY = viewport top-left in zoomed board pixels.
 */
function applyTransform() {
  boardTransform.style.transform = `translate(-${panX}px, -${panY}px)`;

  const zoomedSize = BOARD_SIZE * zoom;
  board.style.width = zoomedSize + 'px';
  board.style.height = zoomedSize + 'px';
  board.style.minWidth = zoomedSize + 'px';
  board.style.minHeight = zoomedSize + 'px';

  const gridWrapper = board.querySelector('.board-grid-wrapper');
  const gridSvg = board.querySelector('.board-grid');
  if (gridWrapper && gridSvg) {
    gridWrapper.style.width = zoomedSize + 'px';
    gridWrapper.style.height = zoomedSize + 'px';
    const cell = SQUARE_SIZE * zoom;
    const gridRect = gridSvg.querySelector('rect');
    if (gridRect) {
      gridRect.setAttribute('width', zoomedSize);
      gridRect.setAttribute('height', zoomedSize);
    }
    const pattern = gridSvg.querySelector('#grid-pattern');
    if (pattern) {
      pattern.setAttribute('width', cell);
      pattern.setAttribute('height', cell);
      const path = pattern.querySelector('path');
      if (path) {
        const margin = 16 * zoom;
        path.setAttribute('d', `M ${margin} 0 v ${cell} M 0 ${margin} h ${cell}`);
        const strokeWidth = Math.max(1, Math.min(4, Math.round(zoom)));
        path.setAttribute('stroke-width', String(strokeWidth));
      }
    }
    /* Cap SVG size so browsers don't drop the grid (e.g. ~16k px limit); scale up to fill */
    if (zoomedSize > GRID_MAX_RENDER_SIZE) {
      gridSvg.setAttribute('width', GRID_MAX_RENDER_SIZE);
      gridSvg.setAttribute('height', GRID_MAX_RENDER_SIZE);
      gridSvg.setAttribute('viewBox', `0 0 ${zoomedSize} ${zoomedSize}`);
      gridSvg.style.transform = `scale(${zoomedSize / GRID_MAX_RENDER_SIZE})`;
    } else {
      gridSvg.setAttribute('width', zoomedSize);
      gridSvg.setAttribute('height', zoomedSize);
      gridSvg.removeAttribute('viewBox');
      gridSvg.style.transform = '';
    }
  }

  squares.forEach(function (sq) {
    const el = board.querySelector('[data-id="' + sq.id + '"]');
    if (!el) return;
    el.style.left = sq.x * zoom + 'px';
    el.style.top = sq.y * zoom + 'px';
    el.style.width = SQUARE_SIZE * zoom + 'px';
    el.style.height = SQUARE_SIZE * zoom + 'px';
    el.style.transform = 'rotate(' + sq.rotation + 'deg)';
  });

  if (boardScaleIndicator) {
    boardScaleIndicator.textContent = zoom === 1 ? '1×' : zoom.toFixed(1).replace(/\.0$/, '') + '×';
  }
  updateStats();
  if (selectedSquareId) updateSquareDataDisplay();
}

function centerViewOnGrid() {
  const rect = boardZoomContainer.getBoundingClientRect();
  panX = BOARD_CENTER * zoom - rect.width / 2;
  panY = BOARD_CENTER * zoom - rect.height / 2;
  applyTransform();
}

/** Convert client coords to board coords (board pixels). */
function clientToBoard(clientX, clientY) {
  const rect = boardZoomContainer.getBoundingClientRect();
  const sx = clientX - rect.left;
  const sy = clientY - rect.top;
  return {
    x: (sx + panX) / zoom,
    y: (sy + panY) / zoom
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
