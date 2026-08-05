import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

function files(root: string): string[] {
  return readdirSync(root).flatMap((name) => {
    const path = join(root, name);
    return statSync(path).isDirectory() ? files(path) : [path];
  });
}

describe('Nursing repository boundary', () => {
  it('does not depend on HR or Games products', () => {
    const src = join(process.cwd(), 'src');
    for (const path of files(src)) {
      const content = readFileSync(path, 'utf8');
      expect(content).not.toContain('optime-hr');
      expect(content).not.toContain('domains/hr');
      expect(content).not.toContain('domains/games');
    }
  });

  it('keeps the local OS contract boundary domain-neutral', () => {
    const content = readFileSync(join(process.cwd(), 'src', 'os', 'contracts.ts'), 'utf8');
    expect(content).not.toMatch(/facility|nursing|senior|candidate|employer|resume/i);
    expect(content).not.toMatch(/^import\s/m);
  });
});
