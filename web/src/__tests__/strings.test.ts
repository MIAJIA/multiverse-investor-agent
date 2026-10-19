// 界面文字只能写在 strings.ts：扫描 src 下的源码，去掉注释后不能再出现中文。
// 例外是演示数据文件（它们是数据，不是界面文字）和测试本身。
import { describe, expect, it } from 'vitest';

const SOURCES = import.meta.glob<string>(['../**/*.ts', '../**/*.tsx', '!../__tests__/**'], {
  query: '?raw', import: 'default', eager: true,
});
const ALLOW = new Set(['../strings.ts', '../playground/demoLabels.ts', '../preview/demoPlanB.ts', '../scenarios/demoNames.ts']);
const CJK = /[一-鿿　-〿＀-￯]/;

function stripComments(code: string): string {
  return code
    .replace(/\{\/\*[\s\S]*?\*\/\}/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .split('\n').map((l) => l.replace(/(^|[^:'"`])\/\/.*$/, '$1')).join('\n');
}

describe('界面文字集中在 strings.ts', () => {
  it('扫描到了源码', () => {
    expect(Object.keys(SOURCES).length).toBeGreaterThan(20);
  });

  it('组件和逻辑代码里没有中文字符串', () => {
    const offenders = Object.entries(SOURCES)
      .filter(([path]) => !ALLOW.has(path))
      .flatMap(([path, code]) => stripComments(code).split('\n')
        .map((line, i) => ({ line, i }))
        .filter(({ line }) => CJK.test(line))
        .map(({ line, i }) => `${path.slice(3)}:${i + 1}  ${line.trim().slice(0, 80)}`));
    expect(offenders).toEqual([]);
  });
});
