import {
  createContext
} from 'react';

const DescriptionContext = createContext({
  description: {},
  getDescriptionForId: () => {}
});

export default DescriptionContext;
