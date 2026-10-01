export const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;
export const capitalize = (word: string) => word[0].toUpperCase() + word.slice(1);
