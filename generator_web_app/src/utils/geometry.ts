// Bounding box and coordinate geometry utilities
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

export interface Point {
  x: number;
  y: number;
}

export interface BoxCoordinates {
  top_left: Point;
  bottom_right: Point;
}

// ---------------------------------------------------------------------------------------------------------------------------
// Pure Geometry Functions

export function boxWidth(box: BoxCoordinates): number {
  return Math.abs(box.top_left.x - box.bottom_right.x);
}

export function boxHeight(box: BoxCoordinates): number {
  return Math.abs(box.top_left.y - box.bottom_right.y);
}

export function boxCenter(box: BoxCoordinates): [number, number] {
  const x = (box.top_left.x + box.bottom_right.x) / 2;
  const y = (box.top_left.y + box.bottom_right.y) / 2;
  return [x, y];
}

export function boxPoints(box: BoxCoordinates): [number, number, number, number] {
  return [box.top_left.x, box.top_left.y, box.bottom_right.x, box.bottom_right.y];
}

export function calcIoU(
  boxA: BoxCoordinates,
  boxB: BoxCoordinates,
): number {
  const [x0_A, y0_A, x1_A, y1_A] = boxPoints(boxA);
  const [x0_B, y0_B, x1_B, y1_B] = boxPoints(boxB);

  const x0_I = Math.max(x0_A, x0_B);
  const y0_I = Math.max(y0_A, y0_B);
  const x1_I = Math.min(x1_A, x1_B);
  const y1_I = Math.min(y1_A, y1_B);

  const width_I = Math.max(0, x1_I - x0_I);
  const height_I = Math.max(0, y1_I - y0_I);
  const intersection = width_I * height_I;

  const width_A = x1_A - x0_A;
  const height_A = y1_A - y0_A;
  const width_B = x1_B - x0_B;
  const height_B = y1_B - y0_B;

  const union = width_A * height_A + width_B * height_B - intersection;
  if (union <= 0) return 0;

  return intersection / union;
}
