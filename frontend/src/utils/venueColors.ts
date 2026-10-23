import type { NodeKind } from '@/types';

export function nodeKindColor(kind: NodeKind): string {
  switch (kind) {
    case 'entry': return '#c1b9aa';
    case 'exit': return '#c1b9aa';
    case 'junction': return '#918d82';
    case 'facility': return '#aaa396';
    case 'food': return '#aaa396';
    case 'medical': return '#c1b9aa';
    case 'stage': return '#d7d0c4';
  }
}

export function nodeKindRadius(kind: NodeKind): number {
  switch (kind) {
    case 'stage': return 22;
    case 'entry':
    case 'exit': return 12;
    case 'food':
    case 'medical': return 10;
    default: return 7;
  }
}

export function nodeKindIcon(kind: NodeKind): string {
  switch (kind) {
    case 'entry': return 'IN';
    case 'exit': return 'OUT';
    case 'junction': return 'J';
    case 'facility': return 'F';
    case 'food': return 'FD';
    case 'medical': return '+';
    case 'stage': return 'S';
  }
}
