import {
  createContext
} from 'react';

const TooltipContext = createContext({
  tooltip: {},
  getTooltipForId: () => {}
});

export default TooltipContext;
