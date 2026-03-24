/**
 * Fit game: DOM references, constants, and shared state.
 * Load this first; other fit-*.js scripts depend on it.
 */

const board = document.getElementById('board');
const boardZoomContainer = document.getElementById('board-zoom-container');
const boardTransform = document.getElementById('board-transform');
const boardScaleIndicator = document.getElementById('board-scale-indicator');
const source = document.getElementById('source');
const ghost = document.getElementById('ghost');
const deleteZone = document.getElementById('delete-zone');
const statCount = document.getElementById('stat-count');
const statBounds = document.getElementById('stat-bounds');
const boundingBox = document.getElementById('bounding-box');
const squareData = document.getElementById('square-data');
const submitBtn = document.getElementById('submit-btn');
const card = document.getElementById('bounds-card');

const SQUARE_SIZE = 56;
const BOARD_SIZE = 10000;
const BOARD_CENTER = BOARD_SIZE / 2;
const ZOOM_MIN = 0.5;  /* limit zoom-out so view doesn't get too small */
const ZOOM_MAX = 1000;  /* cap to avoid rendering bugs at very high zoom */
const ZOOM_FACTOR = 1.15;   /* each wheel step multiplies zoom by this (logarithmic) */
const ZOOM_SENSITIVITY = 0.012;  /* wheel delta multiplier for log zoom */
const GRID_MAX_RENDER_SIZE = 16384;  /* many browsers drop SVG above ~16k px; cap grid and scale */

let squares = [];
let dragState = null;
let selectedSquareId = null;
let idCounter = 0;
let zoom = 1;
let panX = 0;
let panY = 0;

/* ── Snap-to-grid ── */
let snapGridSize = 0.1; // in unit-square multiples; min 0.00001, position snap always on
const snapSizeEl = document.getElementById('snap-size');

/* ── Snap rotation (independent of position snap) ── */
let snapRotationEnabled = true;
let snapAngleStep = 15; // degrees
const snapRotationEnabledEl = document.getElementById('snap-rotation-enabled');
const snapAngleStepEl = document.getElementById('snap-angle-step');

function initSnapFromDom() {
  if (snapSizeEl) {
    const v = parseFloat(snapSizeEl.value);
    if (v >= 0.00001) snapGridSize = v;
  }
  if (snapAngleStepEl) {
    const v = parseFloat(snapAngleStepEl.value);
    if (v > 0 && v <= 180) snapAngleStep = v;
  }
}
initSnapFromDom();

if (snapSizeEl) {
  snapSizeEl.addEventListener('input', function() {
    const v = parseFloat(this.value);
    if (v >= 0.00001) snapGridSize = v;
  });
}
if (snapRotationEnabledEl) {
  snapRotationEnabledEl.addEventListener('change', function() { snapRotationEnabled = this.checked; });
}
if (snapAngleStepEl) {
  snapAngleStepEl.addEventListener('input', function() {
    const v = parseFloat(this.value);
    if (v > 0 && v <= 180) snapAngleStep = v;
  });
}

/**
 * Snap a top-left board-pixel position so the displayed unit coordinate
 * (pixelToCenterX/Y) falls on a clean multiple of snapGridSize. Position snap is always on.
 */
function snapPos(px) {
  const unit = (px - BOARD_CENTER) / SQUARE_SIZE;
  const snapped = Math.round(unit / snapGridSize) * snapGridSize;
  return BOARD_CENTER + snapped * SQUARE_SIZE;
}

/** Snap a rotation (degrees) to the nearest snapAngleStep when rotation snap is enabled. */
function snapRotation(deg) {
  if (!snapRotationEnabled) return deg;
  const step = snapAngleStep > 0 ? snapAngleStep : 90;
  return Math.round(deg / step) * step;
}
