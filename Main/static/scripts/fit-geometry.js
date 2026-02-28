/**
 * Fit game: geometry, collision detection, and coordinate/format helpers.
 * Depends on: fit-constants.js (SQUARE_SIZE, BOARD_CENTER, squares).
 */

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
  const center1 = { x: sq1.x + SQUARE_SIZE / 2, y: sq1.y + SQUARE_SIZE / 2 };
  const center2 = { x: sq2.x + SQUARE_SIZE / 2, y: sq2.y + SQUARE_SIZE / 2 };
  const dist = Math.sqrt(Math.pow(center1.x - center2.x, 2) + Math.pow(center1.y - center2.y, 2));

  const diagonal = SQUARE_SIZE * Math.sqrt(2);
  if (dist < diagonal) {
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
