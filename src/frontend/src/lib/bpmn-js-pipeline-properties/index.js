import pipelineModdleDescriptor from './descriptors/pipeline.json';
import PipelinePropertiesProvider, {getPipelineParameters} from './PipelinePropertiesProvider';
export const PipelineModdleDescriptor = pipelineModdleDescriptor;
export const GetPipelineParameters = getPipelineParameters;

export default {
  __init__: [ 'pipelinePropertiesProvider' ],
  pipelinePropertiesProvider: [ 'type', PipelinePropertiesProvider ]
};
