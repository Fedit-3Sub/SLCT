import {
  createContext
} from 'react';

const BpmnPropertiesPanelContext = createContext({
  selectedElement: null,
  injector: null,
  getService() { return null; }
});

export default BpmnPropertiesPanelContext;