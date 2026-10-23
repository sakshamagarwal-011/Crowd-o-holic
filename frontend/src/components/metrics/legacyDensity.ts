export function densityColor(d: number): string {
  if (d > 0.8) return '#c94b44';
  if (d > 0.6) return '#d97706';
  if (d > 0.3) return '#b5a994';
  return '#8fa66f';
}
