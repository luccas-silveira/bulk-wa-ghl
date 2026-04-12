// Singleton instance to avoid creating new Intl.NumberFormat on every call
const _numberFormatter = new Intl.NumberFormat('pt-BR');

export const formatNumber = (value: number): string =>
  _numberFormatter.format(value);

export const formatPercentage = (value: number): string =>
  `${value.toFixed(1)}%`;
