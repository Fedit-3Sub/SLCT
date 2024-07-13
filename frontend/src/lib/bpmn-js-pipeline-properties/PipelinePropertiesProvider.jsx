import React, { dangerouslySetInnerHTML } from 'react';

// Import your custom list group entries.
import parametersProps from './parts/ParametersProps';
import parameterProps from './parts/ParameterProps';

// Import the properties panel list group component.
import { ListGroup } from '@bpmn-io/properties-panel';
import { useService } from 'bpmn-js-properties-panel';

import { is, getBusinessObject } from 'bpmn-js/lib/util/ModelUtil';

const LOW_PRIORITY = 500;


/**
 * A provider with a `#getGroups(element)` method
 * that exposes groups for a diagram element.
 *
 * @param {PropertiesPanel} propertiesPanel
 * @param {Function} translate
 */
export default function PipelinePropertiesProvider(propertiesPanel, injector, translate) {

  // API ////////

  /**
   * Return the groups provided for the given element.
   *
   * @param {DiagramElement} element
   *
   * @return {(Object[]) => (Object[])} groups middleware
   */
  this.getGroups = function(element) {

    /**
     * We return a middleware that modifies
     * the existing groups.
     *
     * @param {Object[]} groups
     *
     * @return {Object[]} modified groups
     */
    return function(groups) {
      //console.log("getGroups", element);
      if (is(element, 'bpmn:Processx') || is(element, 'bpmn:Task') || is(element, 'bpmn:StartEvent') || is(element, 'bpmn:EndEvent')) 
      {
        groups.push(createParametersGroup(element, injector, translate));
      }
      return groups;
    };
  };


  // registration ////////

  // Register our custom magic properties provider.
  // Use a lower priority to ensure it is loaded after
  // the basic BPMN properties.
  propertiesPanel.registerProvider(LOW_PRIORITY, this);
}

PipelinePropertiesProvider.$inject = [ 'propertiesPanel', 'injector', 'translate' ];

import { TextFieldEntry, isTextFieldEntryEdited } from '@bpmn-io/properties-panel';

// Create the custom parameters list group.
function createParametersGroup(element, injector, translate) {
  const bpmnFactory = injector.get('bpmnFactory'),
        commandStack = injector.get('commandStack');

  const id = element.id + '-parameter';
  
  let component = Url;
  let parameter = null;

  const commands = [];
  const businessObject = getBusinessObject(element);
  if(false) {
    component = ProcessUrl;
    commandStack.execute('element.updateModdleProperties', {
      element: element,
      moddleElement: businessObject,
      properties: {url: 'process url'}
    });
  } else {
    let extensionElements = businessObject.get('extensionElements');
    if (!extensionElements) {
      extensionElements = createElement(
        'bpmn:ExtensionElements',
        { values: [] },
        businessObject,
        bpmnFactory
      );

      commands.push({
        cmd: 'element.updateModdleProperties',
        context: {
          element,
          moddleElement: businessObject,
          properties: { extensionElements }
        }
      });
    }

    let extension = getExtension(businessObject, 'pipeline:Parameters');
    if(!extension) {
      extension = createParameters({
        values: []
      }, extensionElements, bpmnFactory);

      commands.push({
        cmd: 'element.updateModdleProperties',
        context: {
          element,
          moddleElement: extensionElements,
          properties: {
            values: [ ...extensionElements.get('values'), extension ]
          }
        }
      });
    }

    const parameters = extension.get('values');
    parameter = parameters.filter(function(e) {
      return e.$instanceOf('pipeline:Parameter');
    })[0];
    if(!parameter) {
      parameter = createElement('pipeline:Parameter', {
        url: ''
      }, extension, bpmnFactory);
      commands.push({
        cmd: 'element.updateModdleProperties',
        context: {
          element,
          moddleElement: extension,
          properties: {
            values: [ ...extension.get('values'), parameter ]
          }
        }
      });  
    }

    commandStack.execute('properties-panel.multi-command-executor', commands);
    //console.log(extension, parameters);
  }

  return {
    id: 'pipeline',
    label: translate('Pipeline parameters'),
    entries: [
      {
        id: id + '-url',
        element,
        parameter,
        commandStack,
        component,
        isEdited: isTextFieldEntryEdited
      },
    ]
  };

  // Create a group called "parameters".
  const parametersGroup = {
    id: 'parameters',
    label: translate('Pipeline parameters'),
    component: ListGroup,
    ...parametersProps({ element, injector })
  };

  return parametersGroup;
}

export function getExtension(element, type) {
  if (!element.extensionElements) {
    return null;
  }

  return element.extensionElements.values.filter(function(e) {
    return e.$instanceOf(type);
  })[0];
}

export function createElement(elementType, properties, parent, factory) {
  const element = factory.create(elementType, properties);

  if (parent) {
    element.$parent = parent;
  }

  return element;
}

export function createParameters(properties, parent, bpmnFactory) {
  return createElement('pipeline:Parameters', properties, parent, bpmnFactory);
}

function Url(props) {
  const { element, id, parameter, commandStack } = props;
  //console.log("Url", props);

  const modeling = useService('modeling');
  const translate = useService('translate');
  const debounce = useService('debounceInput');

  const getValue = () => {
    //console.log("getValue", parameter);
    return parameter.get('url');
  };

  const setValue = value => {
    commandStack.execute('element.updateModdleProperties', {
      element,
      moddleElement: parameter,
      properties: {
        url: value
      }
    });
  };

  return <TextFieldEntry
    id={ id }
    element={ element }
    description={ translate('Pipeline processor url') }
    label={ translate('Url') }
    getValue={ getValue }
    setValue={ setValue }
    debounce={ debounce }
  />;
}

export function getPipelineParameters(element) {
  const businessObject = getBusinessObject(element);
  const extensionElements = businessObject?.get('extensionElements');
  const extension = extensionElements?.values.filter(function(e) { return e.$instanceOf('pipeline:Parameters'); })[0];
  const parameters = extension?.get('values');
  const parameter = parameters?.filter(function(e) { return e.$instanceOf('pipeline:Parameter');  })[0];
  const url = parameter?.get('url');
  return { url, businessObject };
}
