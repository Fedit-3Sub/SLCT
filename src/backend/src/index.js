'use strict';

const boostrapPermissions = async (strapi) => {
  try {
    // 1. 퍼블릭 역할 가져오기
    const roles = await strapi
      .service('plugin::users-permissions.role')
      .find();
    const _public = await strapi
      .service('plugin::users-permissions.role')
      .findOne(roles.filter((role) => role.type === 'public')[0].id);

    // 2. 기본 CRUD 권한 활성화
    Object.keys(_public.permissions)
      .filter((permission) => permission.startsWith('api'))
      .forEach((permission) => {
        const controller = Object.keys(_public.permissions[permission].controllers)[0];

        _public.permissions[permission].controllers[controller].find.enabled = true;
        if (_public.permissions[permission].controllers[controller].findOne)
          _public.permissions[permission].controllers[controller].findOne.enabled = true;
        if (_public.permissions[permission].controllers[controller].create)
          _public.permissions[permission].controllers[controller].create.enabled = true;
        if (_public.permissions[permission].controllers[controller].update)
          _public.permissions[permission].controllers[controller].update.enabled = true;
      });

    // 3. 커스텀 경로 권한 추가 (/feditscraper/json)
    if (!_public.permissions['api::feditscraper.feditscraper']) {
      _public.permissions['api::feditscraper.feditscraper'] = {
        controllers: {
          feditscraper: {
            json: { enabled: true }, // /json 경로에 대한 GET 권한 활성화
          },
        },
      };
    } else {
      _public.permissions['api::feditscraper.feditscraper'].controllers.feditscraper.json = {
        enabled: true,
      };
    }

    // 4. 퍼블릭 역할 업데이트
    await strapi
      .service('plugin::users-permissions.role')
      .updateRole(_public.id, _public);

    strapi.log.info('Public role permissions have been updated successfully.');
  } catch (error) {
    strapi.log.error('Error while updating public permissions:', error);
  }
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
  bootstrap({ strapi }) {
    boostrapPermissions(strapi);
  },
};
