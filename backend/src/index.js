'use strict';

const boostrapPermissions = async (strapi) => {
  const roles = await strapi
    .service("plugin::users-permissions.role")
    .find();

  const _public = await strapi
    .service("plugin::users-permissions.role")
    .findOne(roles.filter((role) => role.type === "public")[0].id);

  // Iterate over all api content-types
  Object.keys(_public.permissions)
    .filter(permission => permission.startsWith('api'))
    .forEach(permission => {
      const controller = Object.keys(_public.permissions[permission].controllers)[0];

      _public.permissions[permission].controllers[controller].find.enabled = true;
      if (_public.permissions[permission].controllers[controller].findOne) 
        _public.permissions[permission].controllers[controller].findOne.enabled = true;
      if (_public.permissions[permission].controllers[controller].create) 
        _public.permissions[permission].controllers[controller].create.enabled = true;
      if (_public.permissions[permission].controllers[controller].update) 
        _public.permissions[permission].controllers[controller].update.enabled = true;
    });

  await strapi
    .service("plugin::users-permissions.role")
    .updateRole(_public.id, _public);
};

module.exports = {
  /**
   * An asynchronous register function that runs before
   * your application is initialized.
   *
   * This gives you an opportunity to extend code.
   */
  register(/*{ strapi }*/) {},

  /**
   * An asynchronous bootstrap function that runs before
   * your application gets started.
   *
   * This gives you an opportunity to set up your data model,
   * run jobs, or perform some special logic.
   */
  bootstrap(/*{ strapi }*/) {
    boostrapPermissions(strapi);
  },
};
