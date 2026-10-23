// Common and shared primitives
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

export type PrimaryKey = number | string;

export interface Keyring {
  pkey: number;
  uuid: string;
}

export type { Point, BoxCoordinates } from "@/utils/geometry";
export {
  boxWidth,
  boxHeight,
  boxCenter,
  boxPoints,
  calcIoU,
} from "@/utils/geometry";

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
  fill?: string;
  stroke: string;
}

export interface tempRect {
  startPointX: number;
  startPointY: number;
  width: number;
  height: number;
}

export interface CGObject {
  name?: string;
  username?: string;
  status?: string;
  last_login?: Date;
  locale?: string;
  roles?: CGObject[];
  uuid: string;
  created?: Date;
  modified?: Date;
}
