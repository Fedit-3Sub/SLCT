import SimulationMenuProvider from './SimulationMenuProvider';
import FeditEntityMenuProvider from './FeditEntityMenuProvider';

export default {
  __depends__: [],
  __init__: ['simulationMenuProvider', 'feditEntityMenuProvider'],
  simulationMenuProvider: ['type', SimulationMenuProvider],
  feditEntityMenuProvider: ['type', FeditEntityMenuProvider]
};