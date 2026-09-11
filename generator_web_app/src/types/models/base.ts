// Base types and Box model mirroring airial_api/database/object_models/base.py
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

export type PrimaryKey = number | string;

export interface Keyring {
  pkey: number;
  uuid: string;
}

// ---------------------------------------------------------------------------------------------------------------------------

export interface coord {
  x: number;
  y: number;
}

export interface BoxIntf {
  top_left: coord;
  bottom_right: coord;
}

export type RawCoord = coord | [number, number];

export interface RawBoxInput {
  top_left: RawCoord;
  bottom_right: RawCoord;
}

export class Box implements BoxIntf {
  top_left: coord;
  bottom_right: coord;

  constructor(box: BoxIntf | RawBoxInput) {
    const parseCoord = (c: RawCoord): coord => {
      if (Array.isArray(c)) {
        return { x: c[0], y: c[1] };
      }
      return { x: c.x, y: c.y };
    };

    this.top_left = parseCoord(box.top_left);
    this.bottom_right = parseCoord(box.bottom_right);
  }

  getCenter(): [number, number] {
    const x = (this.top_left.x + this.bottom_right.x) / 2;
    const y = (this.top_left.y + this.bottom_right.y) / 2;
    return [x, y];
  }

  getPoints(): [number, number, number, number] {
    return [
      this.top_left.x,
      this.top_left.y,
      this.bottom_right.x,
      this.bottom_right.y,
    ];
  }

  getWidth(): number {
    return Math.abs(this.top_left.x - this.bottom_right.x);
  }

  getHeight(): number {
    return Math.abs(this.top_left.y - this.bottom_right.y);
  }

  calcIou(box_2: Box | BoxIntf): number {
    const p1 = this.getPoints();
    const p2 =
      box_2 instanceof Box
        ? box_2.getPoints()
        : [
            box_2.top_left.x,
            box_2.top_left.y,
            box_2.bottom_right.x,
            box_2.bottom_right.y,
          ];

    const x0_A = p1[0],
      y0_A = p1[1],
      x1_A = p1[2],
      y1_A = p1[3];
    const x0_B = p2[0],
      y0_B = p2[1],
      x1_B = p2[2],
      y1_B = p2[3];

    const x0_I = Math.max(x0_A, x0_B);
    const y0_I = Math.max(y0_A, y0_B);
    const x1_I = Math.min(x1_A, x1_B);
    const y1_I = Math.min(y1_A, y1_B);

    let width_I = x1_I - x0_I;
    let height_I = y1_I - y0_I;

    width_I = width_I < 0 ? 0 : width_I;
    height_I = height_I < 0 ? 0 : height_I;

    const intersection = width_I * height_I;

    const width_A = x1_A - x0_A;
    const height_A = y1_A - y0_A;
    const width_B = x1_B - x0_B;
    const height_B = y1_B - y0_B;

    const union = width_A * height_A + width_B * height_B - intersection;
    if (union === 0) return 0;
    return intersection / union;
  }

  serialize(): BoxIntf {
    return {
      top_left: { x: this.top_left.x, y: this.top_left.y },
      bottom_right: { x: this.bottom_right.x, y: this.bottom_right.y },
    };
  }

  to_dict(): [number, number, number, number] {
    return this.getPoints();
  }
}

// ---------------------------------------------------------------------------------------------------------------------------
// Canvas & UI Helper Interfaces

export interface konvaBoxConf {
  width: number;
  height: number;
  x: number;
  y: number;
  scaleX: number;
  scaleY: number;
  rotation: number;
  stroke: string;
}

export interface tempRect {
  startPointX: number;
  startPointY: number;
  width: number;
  height: number;
}

export type CGObject = {
  name?: string;
  username?: string;
  status?: string;
  last_login?: Date | string;
  locale?: string;
  roles?: CGObject[] | any[];
  uuid: string;
  created?: Date | string;
  modified?: Date | string;
  [key: string]: any;
};
