import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import BusyHint from '../components/BusyHint';

describe('等待提示', () => {
  it('显示真实的已用时间和说明，不显示百分比或进度条', () => {
    const html = renderToStaticMarkup(createElement(BusyHint, { kind: 'analyze', since: Date.now() - 125_000, online: false }));
    expect(html).toContain('2:05');
    expect(html).toContain('两到三分钟');
    expect(html).not.toMatch(/%|progress/);
  });
  it('联网时多一句说明', () => {
    const html = renderToStaticMarkup(createElement(BusyHint, { kind: 'analyze', since: Date.now(), online: true }));
    expect(html).toContain('联网已打开');
  });
});
