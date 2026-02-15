export type Location =
  | "top-left" | "top" | "top-right"
  | "left" | "center" | "right"
  | "bottom-left" | "bottom" | "bottom-right"
  | "unknown";

export type ObjectItem = {
  name: string;
  count?: number | null;
  location: Location;
  relative_position?: string | null;
  attributes: string[];
  visible_text: string[];
  confidence?: number | null;
};

export type Inventory = {
  objects: ObjectItem[];
  scene_summary?: string | null;
};

export type Ambiguity = {
  ambiguous: boolean;
  reason?: string | null;
  candidates: string[];
};

export type OnePassResponse = {
  inventory: Inventory;
  ambiguity: Ambiguity;
  answer: string;
};

export type IterStartResponse = {
  session_id: string;
  inventory_brief: string;
  ambiguity: Ambiguity;
  clarification_question: string;
  options: string[];
};

export type IterChooseResponse = {
  focused_answer: string;
  followup_suggestions: string[];
  updated_state: any;
};
