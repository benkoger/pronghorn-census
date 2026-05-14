// Types for the graph implementation used in the dataStore dataStore
// Author: Michael B. Lance

// // ---------------------------------------------------------------------------------------------------------------------------

export type Node = {
  id: string;
  group: string;
  radius: number;
  parent_count?: number;
};

export type Edge = {
  source: string;
  target: string;
  value: number;
};

export type dataGraph = {
  nodes: Node[];
  Edges: Edge[];
};
