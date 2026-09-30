// Welcome prompt pool (punchlist 2026-09-30 §7.3): every one answerable from the notes. The first four are the comp's;
// "Refresh prompts" pages through the pool four at a time.
export interface Prompt {
  text: string;
  icon: "drop" | "sprout" | "sun" | "bug";
}

export const PROMPTS: Prompt[] = [
  { text: "How humid should the dome be for new TC plantlets?", icon: "drop" },
  { text: "What soil mix do tissue-culture Monstera go into first?", icon: "sprout" },
  { text: "Is one Barrina T5 at 8 inches enough for an albo?", icon: "sun" },
  { text: "What's the best way to deal with thrips on baby aroids?", icon: "bug" },
  { text: "How much light do Alocasia plantlets need right after potting?", icon: "sun" },
  { text: "How long before I start lowering the humidity on Alocasia?", icon: "drop" },
  { text: "Should tissue cultures get fertilizer when they're first potted?", icon: "sprout" },
  { text: "My TCs arrived in a heat wave. Can the bags sit out for a few days?", icon: "sun" },
  { text: "Is Thai Constellation care different from albo care?", icon: "sprout" },
  { text: "Leaves yellowed right after the dome came off. Is it light or humidity?", icon: "drop" },
  { text: "Is an AC Infinity S16 at 10 inches for 14 hours enough for Philodendron?", icon: "sun" },
  { text: "Bugs showed up while my plants are still in the dome. Treat now or wait?", icon: "bug" },
];
