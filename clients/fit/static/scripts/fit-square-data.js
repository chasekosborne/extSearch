/**
 * Fit game: selection editor panel (position/rotation inputs).
 * Depends on: fit-constants.js, fit-geometry.js, fit-squares.js.
 */

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
  rotation = snapRotation(rotation);
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
    squareData.innerHTML = '<p class="selection-editor-empty">Select a square to edit position and rotation</p>';
    squareData.classList.add('is-empty');
    return;
  }

  const sq = squares.find(function(s) { return s.id === selectedSquareId; });
  if (!sq) {
    squareData.innerHTML = '<p class="selection-editor-empty">Select a square to edit position and rotation</p>';
    squareData.classList.add('is-empty');
    return;
  }

  squareData.classList.remove('is-empty');
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
}
