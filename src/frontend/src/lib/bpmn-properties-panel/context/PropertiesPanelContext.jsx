import { createContext } from 'react';

const PropertiesPanelContext = createContext({

  // TODO: get element through context instead of props
  element: null,
  onShow: () => {}
});

export default PropertiesPanelContext;