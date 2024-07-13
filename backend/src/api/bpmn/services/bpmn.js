'use strict';

/**
 * bpmn service
 */

const { createCoreService } = require('@strapi/strapi').factories;

module.exports = createCoreService('api::bpmn.bpmn');
