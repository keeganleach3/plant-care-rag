// STUB (architect): W1 fills the pool of twelve — punchlist 2026-09-30 §7.3.
export interface Prompt {
  text: string;
  icon: "drop" | "sprout" | "sun" | "bug";
}

export const PROMPTS: Prompt[] = [
  { text: "How humid should the dome be for new TC plantlets?", icon: "drop" },
  { text: "What soil mix do tissue-culture Monstera go into first?", icon: "sprout" },
  { text: "Is one Barrina T5 at 8 inches enough for an albo?", icon: "sun" },
  { text: "What's the best way to deal with thrips on baby aroids?", icon: "bug" },
];
