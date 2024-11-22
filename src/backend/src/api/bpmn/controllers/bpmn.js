'use strict';

/**
 * bpmn controller
 */

const { createCoreController } = require('@strapi/strapi').factories;

module.exports = createCoreController('api::bpmn.bpmn');
