/**
 * Fit game: geometry, collision detection, and coordinate/format helpers.
 * Depends on: fit-constants.js (SQUARE_SIZE, BOARD_CENTER, squares).
 */

// Calculate the bounding box of a rotated square
function getRotatedSquareBounds(sq) {
  const shapeWidth = getShapeWidthPx(sq);
  const shapeHeight = getShapeHeightPx(sq);
  const centerX = sq.x + shapeWidth / 2;
  const centerY = sq.y + shapeHeight / 2;
  const angle = sq.rotation * Math.PI / 180;
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);
  const halfWidth = shapeWidth / 2;
  const halfHeight = shapeHeight / 2;

  // Calculate the four corners of the rotated square
  const corners = [
    { x: -halfWidth, y: -halfHeight },
    { x: halfWidth, y: -halfHeight },
    { x: halfWidth, y: halfHeight },
    { x: -halfWidth, y: halfHeight }
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

// Get the four corners of a rotated square
function getSquareCorners(sq) {
  const shapeWidth = getShapeWidthPx(sq);
  const shapeHeight = getShapeHeightPx(sq);
  const centerX = sq.x + shapeWidth / 2;
  const centerY = sq.y + shapeHeight / 2;
  const angle = sq.rotation * Math.PI / 180;
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);
  const halfWidth = shapeWidth / 2;
  const halfHeight = shapeHeight / 2;

  return [
    { x: centerX + (-halfWidth) * cos - (-halfHeight) * sin, y: centerY + (-halfWidth) * sin + (-halfHeight) * cos },
    { x: centerX + halfWidth * cos - (-halfHeight) * sin, y: centerY + halfWidth * sin + (-halfHeight) * cos },
    { x: centerX + halfWidth * cos - halfHeight * sin, y: centerY + halfWidth * sin + halfHeight * cos },
    { x: centerX + (-halfWidth) * cos - halfHeight * sin, y: centerY + (-halfWidth) * sin + halfHeight * cos }
  ];
}

// Check if a point is inside a rotated square
function pointInRotatedSquare(point, sq) {
  const corners = getSquareCorners(sq);
  const shapeWidth = getShapeWidthPx(sq);
  const shapeHeight = getShapeHeightPx(sq);
  const centerX = sq.x + shapeWidth / 2;
  const centerY = sq.y + shapeHeight / 2;
  const angle = -sq.rotation * Math.PI / 180; // Reverse rotation
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);

  // Transform point to square's local space
  const dx = point.x - centerX;
  const dy = point.y - centerY;
  const localX = dx * cos - dy * sin;
  const localY = dx * sin + dy * cos;

  const halfWidth = shapeWidth / 2;
  const halfHeight = shapeHeight / 2;
  return Math.abs(localX) <= halfWidth && Math.abs(localY) <= halfHeight;
}

// Check if two rotated squares overlap using SAT (Separating Axis Theorem)
function squaresOverlap(sq1, sq2) {
  const corners1 = getSquareCorners(sq1);
  const corners2 = getSquareCorners(sq2);
  const eps = 1e-8;

  function project(corners, ax, ay) {
    let min = corners[0].x * ax + corners[0].y * ay;
    let max = min;
    for (let i = 1; i < corners.length; i++) {
      const d = corners[i].x * ax + corners[i].y * ay;
      if (d < min) min = d;
      if (d > max) max = d;
    }
    return { min: min, max: max };
  }

  const polys = [corners1, corners2];
  for (let p = 0; p < polys.length; p++) {
    const poly = polys[p];
    for (let i = 0; i < poly.length; i++) {
      const a = poly[i];
      const b = poly[(i + 1) % poly.length];
      const ax = -(b.y - a.y);
      const ay = b.x - a.x;
      if (Math.abs(ax) < eps && Math.abs(ay) < eps) continue;

      const p1 = project(corners1, ax, ay);
      const p2 = project(corners2, ax, ay);

      // Touching edges are non-overlapping.
      if (p1.max <= p2.min + eps || p2.max <= p1.min + eps) {
        return false;
      }
    }
  }
  return true;
}

// Check if a square at given position/rotation would collide with any other square
function wouldCollide(testSq, excludeId) {
  return squares.some(sq => {
    if (sq.id === excludeId) return false;
    return squaresOverlap(testSq, sq);
  });
}

// Round to n decimal places to avoid floating-point display noise
function roundDecimal(val, n) {
  if (n <= 0) return Math.round(val);
  const p = Math.pow(10, n);
  return Math.round(val * p) / p;
}

function formatSquareUnit(v) {
  const x = Number(v);
  const cleaned = roundDecimal(x, 13);
  return cleaned.toFixed(14).replace(/\.?0+$/, '') || '0';
}
function formatRotation(v) {
  const x = Number(v);
  const cleaned = roundDecimal(x, 2);
  return cleaned.toFixed(1).replace(/\.?0+$/, '') || '0';
}

function pixelToCenterX(xPx) { return (xPx - BOARD_CENTER) / SQUARE_SIZE; }
function pixelToCenterY(yPx) { return (yPx - BOARD_CENTER) / SQUARE_SIZE; }
function centerToPixelX(cx) { return BOARD_CENTER + cx * SQUARE_SIZE; }
function centerToPixelY(cy) { return BOARD_CENTER + cy * SQUARE_SIZE; }

function organizeSquareBounds(squaresCorners) {
  let top = squaresCorners[0], right = squaresCorners[0], bottom = squaresCorners[0], left = squaresCorners[0];
  for (let corner of squaresCorners) {
    if (corner.y < top.y) top = corner;
    if (corner.x > right.x) right = corner;
    if (corner.y > bottom.y) bottom = corner;
    if (corner.x < left.x) left = corner;
  }
  return { top, right, bottom, left };
}

/** Round corner coordinates for submission so bounding box / objective value matches display. */
function roundCornersForSubmit(corners) {
  return corners.map(function (pt) {
    return {
      x: roundDecimal(pt.x, 10),
      y: roundDecimal(pt.y, 10)
    };
  });
}
