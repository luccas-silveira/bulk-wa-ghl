export const formatNumber = (value: number): string =>
  new Intl.NumberFormat('pt-BR').format(value);

export const formatPercentage = (value: number): string =>
  `${value.toFixed(1)}%`;
