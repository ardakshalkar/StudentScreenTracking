export type Mode = 'overview'|'focused';
export const qualities = {
  overview:{width:640, interval:2500, quality:.68, maxBytes:60000},
  focused:{width:1600, interval:333, quality:.9, maxBytes:650000},
};
