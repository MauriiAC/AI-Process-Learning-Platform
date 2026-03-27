export function getSemanticScoreLabel(score: number) {
  if (score >= 0.85) {
    return "Alta coincidencia temática";
  }
  if (score >= 0.72) {
    return "Coincidencia moderada";
  }
  return "Coincidencia exploratoria";
}

export function getSemanticScoreDetail(score: number) {
  return `Score técnico ${(score * 100).toFixed(0)}%`;
}
