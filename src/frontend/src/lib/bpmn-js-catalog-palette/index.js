import CatalogPaletteProvider from './CatalogPaletteProvider';
import CatalogMenuProvider from './CatalogMenuProvider';

export default {
  __init__: ['catalogPaletteProvider', 'catalogMenuProvider'],
  catalogPaletteProvider: ['type', CatalogPaletteProvider],
  catalogMenuProvider: ['type', CatalogMenuProvider],
};
