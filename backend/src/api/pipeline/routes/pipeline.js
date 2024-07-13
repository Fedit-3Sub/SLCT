'use strict';

/**
 * pipeline router
 */

const { createCoreRouter } = require('@strapi/strapi').factories;

module.exports = createCoreRouter('api::pipeline.pipeline');
