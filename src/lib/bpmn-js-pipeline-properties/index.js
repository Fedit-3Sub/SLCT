import pipelineModdleDescriptor from './descriptors/pipeline.json';
import PipelinePropertiesProvider from './PipelinePropertiesProvider';
export const PipelineModdleDescriptor = pipelineModdleDescriptor;
console.log("PipelineModdleDescriptor", PipelineModdleDescriptor)

export default {
  __init__: [ 'pipelinePropertiesProvider' ],
  pipelinePropertiesProvider: [ 'type', PipelinePropertiesProvider ]
};
