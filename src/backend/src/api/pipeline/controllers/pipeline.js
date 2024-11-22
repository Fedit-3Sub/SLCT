'use strict';

/**
 * pipeline controller
 */

const { createCoreController } = require('@strapi/strapi').factories;

module.exports = createCoreController('api::pipeline.pipeline');
