import {
  createContext
} from 'react';

const LayoutContext = createContext({
  layout: {},
  setLayout: () => {},
  getLayoutForKey: () => {},
  setLayoutForKey: () => {}
});

export default LayoutContext;