/* eslint-disable-next-line import/prefer-default-export */
export const SELECTOR = '#chart';
export const MESH_FORCE_LAYOUT = {
  defaultCollisionFactor: 80,
  defaultForceStrength: -100,
  defaultForceBody: 75,
  defaultForceX: 0,
  defaultForceY: 0,
};

export const DEFAULT_RADIUS = 16;
export const DEFAULT_NODE_COLOR = '#0066CC';
export const DEFAULT_NODE_HIGHLIGHT_COLOR = '#16407C';
export const DEFAULT_NODE_LABEL_TEXT_COLOR = 'white';
export const DEFAULT_FONT_SIZE = '12px';
export const LABEL_TEXT_MAX_LENGTH = 15;

export const MARGIN = 15;
export const FALLBACK_WIDTH = 700;

export const NODE_STATE_COLOR_KEY = {
  disabled: '#6A6E73',
  healthy: '#3E8635',
  error: '#C9190B',
};

export const NODE_STATE_HTML_ENTITY_KEY = {
  disabled: '\u25EF',
  healthy: '\u2713',
  error: '\u0021',
};

export const NODE_TYPE_SYMBOL_KEY = {
  hop: 'h',
  execution: 'Ex',
  hybrid: 'Hy',
  control: 'C',
};
