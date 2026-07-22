/**
 * Case-insensitive subsequence fuzzy matcher.
 * Returns a score (higher = better) or null when the query does not match.
 */
export function fuzzyScore(query: string, target: string): number | null {
  const q = query.toLowerCase().trim();
  const t = target.toLowerCase();
  if (!q) return 0;
  if (!t) return null;

  let score = 0;
  let targetIndex = 0;
  let runLength = 0;

  for (const char of q) {
    const found = t.indexOf(char, targetIndex);
    if (found === -1) return null;

    // Consecutive-run bonus rewards adjacent matches.
    if (found === targetIndex && runLength > 0) {
      runLength += 1;
      score += 3 + runLength;
    } else {
      runLength = 1;
      score += 1;
    }

    // Word-boundary bonus (start of string or after a separator).
    if (found === 0 || /[\s\-_./\\:]/.test(t[found - 1])) {
      score += 4;
    }

    // Early-match bonus.
    score += Math.max(0, 4 - Math.floor(found / 8));

    targetIndex = found + 1;
  }

  // Slightly prefer shorter targets for the same query.
  score -= Math.floor(t.length / 24);
  return score;
}
