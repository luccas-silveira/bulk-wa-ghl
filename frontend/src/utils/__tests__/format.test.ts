import { formatNumber, formatPercentage } from '../format';

describe('formatNumber', () => {
  it('formats thousands with pt-BR locale (dot as separator)', () => {
    expect(formatNumber(1500)).toBe('1.500');
  });

  it('formats zero', () => {
    expect(formatNumber(0)).toBe('0');
  });

  it('formats large numbers', () => {
    expect(formatNumber(12500)).toBe('12.500');
  });

  it('formats negative numbers', () => {
    expect(formatNumber(-1500)).toBe('-1.500');
  });

  it('formats decimal numbers', () => {
    // Intl.NumberFormat pt-BR preserves decimal places with comma separator
    expect(formatNumber(1500.5)).toBe('1.500,5');
  });
});

describe('formatPercentage', () => {
  it('formats to one decimal with % suffix', () => {
    expect(formatPercentage(94.4)).toBe('94.4%');
  });

  it('formats zero', () => {
    expect(formatPercentage(0)).toBe('0.0%');
  });

  it('rounds to one decimal', () => {
    expect(formatPercentage(12.567)).toBe('12.6%');
  });

  it('formats 100%', () => {
    expect(formatPercentage(100)).toBe('100.0%');
  });
});
