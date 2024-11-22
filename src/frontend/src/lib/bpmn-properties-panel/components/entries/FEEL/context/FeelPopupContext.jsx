import {
  createContext
} from 'react';

const FeelPopupContext = createContext({
  open: () => {},
  close: () => {},
  source: null
});

export default FeelPopupContext;