'use strict';

/**
 * bpmn router
 */

const { createCoreRouter } = require('@strapi/strapi').factories;

module.exports = createCoreRouter('api::bpmn.bpmn');
