import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { BranchBar, BranchTag, HypotheticalBanner } from '../components/BranchSwatch';

const html = (el: Parameters<typeof renderToStaticMarkup>[0]) => renderToStaticMarkup(el);

describe('BranchSwatch', () => {
  it('有资料支持不加字，仅推断写「仅推断」，占位资料再加说明', () => {
    expect(html(createElement(BranchTag, { kind: 'evidenced' }))).toBe('');
    expect(html(createElement(BranchTag, { kind: 'model_only' }))).toContain('仅推断');
    expect(html(createElement(BranchTag, { kind: 'model_only', synthetic: true }))).toContain('资料为占位');
  });
  it('假设分支：标签、底纹、横幅文案', () => {
    expect(html(createElement(BranchTag, { kind: 'hypothetical' }))).toContain('假设 · 未观测');
    expect(html(createElement(BranchBar, { kind: 'hypothetical' }))).toContain('repeating-linear-gradient');
    expect(html(createElement(HypotheticalBanner, { what: '改用集成激光' }))).toContain('这条分支建立在尚未发生的假设上：改用集成激光');
  });
});
