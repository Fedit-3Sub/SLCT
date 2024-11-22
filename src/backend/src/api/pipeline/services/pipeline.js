'use strict';

/**
 * pipeline service
 */

const { createCoreService } = require('@strapi/strapi').factories;

module.exports = createCoreService('api::pipeline.pipeline');
