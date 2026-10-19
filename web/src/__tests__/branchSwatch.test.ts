import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { BranchBar, BranchTag, HypotheticalBanner } from '../components/BranchSwatch';

const html = (el: Parameters<typeof renderToStaticMarkup>[0]) => renderToStaticMarkup(el);

describe('BranchSwatch', () => {
  it('有资料支持不加字，仅推断写「Inferred」，占位资料再加说明', () => {
    expect(html(createElement(BranchTag, { kind: 'evidenced' }))).toBe('');
    expect(html(createElement(BranchTag, { kind: 'model_only' }))).toContain('Inferred');
    expect(html(createElement(BranchTag, { kind: 'model_only', synthetic: true }))).toContain('Placeholder sources');
  });
  it('假设分支：标签、底纹、横幅文案', () => {
    expect(html(createElement(BranchTag, { kind: 'hypothetical' }))).toContain('Assumed · not observed');
    expect(html(createElement(BranchBar, { kind: 'hypothetical' }))).toContain('repeating-linear-gradient');
    expect(html(createElement(HypotheticalBanner, { what: 'integrated lasers' }))).toContain('This branch rests on an assumption that has not happened yet: integrated lasers');
  });
});
