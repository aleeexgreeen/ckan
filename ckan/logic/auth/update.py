# encoding: utf-8

import ckan.logic as logic
import ckan.authz as authz
import ckan.logic.auth as logic_auth
from ckan import model
from ckan.common import _

# FIXME this import is evil and should be refactored
from ckan.logic.auth.create import _check_group_auth
from ckan.types import Context, DataDict, AuthResult


@logic.auth_allow_anonymous_access
def package_update(context: Context, data_dict: DataDict) -> AuthResult:
    user = context.get('user')

    package = logic_auth.get_package_object(context, data_dict)
    if package.owner_org:
        # if there is an owner org then we must have update_dataset
        # permission for that organization
        check1 = authz.has_user_permission_for_group_or_org(
            package.owner_org, user, 'update_dataset'
        )
    else:
        # If dataset is not owned then we can edit if config permissions allow
        if authz.auth_is_anon_user(context):
            check1 = all(authz.check_config_permission(p) for p in (
                'anon_create_dataset',
                'create_dataset_if_not_in_organization',
                'create_unowned_dataset',
                ))
        else:
            check1 = all(authz.check_config_permission(p) for p in (
                'create_dataset_if_not_in_organization',
                'create_unowned_dataset',
                )) or authz.has_user_permission_for_some_org(
                user, 'create_dataset')

    if not check1:
        success = False
        if authz.check_config_permission('allow_dataset_collaborators'):
            # if org-level auth failed, check dataset-level auth
            # (ie if user is a collaborator)
            user_obj = model.User.get(user)
            if user_obj:
                success = authz.user_is_collaborator_on_dataset(
                    user_obj.id, package.id, ['admin', 'editor'])
        if not success:
            return {'success': False,
                    'msg': _('User %s not authorized to edit package %s') %
                            (str(user), package.id)}
    else:
        check2 = _check_group_auth(context, data_dict)
        if not check2:
            return {'success': False,
                    'msg': _('User %s not authorized to edit these groups') %
                            (str(user))}

    return {'success': True}


def package_revise(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('package_update', context, data_dict['update'])


def package_resource_reorder(context: Context,
                             data_dict: DataDict) -> AuthResult:
    ## the action function runs package update so no need to run it twice
    return {'success': True}

def resource_update(context: Context, data_dict: DataDict) -> AuthResult:
    user = context.get('user')
    resource = logic_auth.get_resource_object(context, data_dict)

    # check authentication against package
    assert resource.package_id
    pkg = model.Package.get(resource.package_id)
    if not pkg:
        raise logic.NotFound(
            _('No package found for this resource, cannot check auth.')
        )

    pkg_dict = {'id': pkg.id}
    authorized = authz.is_authorized('package_update', context, pkg_dict).get('success')

    if not authorized:
        return {'success': False,
                'msg': _('User %s not authorized to edit resource %s') %
                        (str(user), resource.id)}
    else:
        return {'success': True}


def resource_view_update(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('resource_update', context, {'id': data_dict['resource_id']})

def resource_view_reorder(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('resource_update', context, {'id': data_dict['resource_id']})


def package_relationship_update(context: Context,
                                data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('package_relationship_create',
                                   context,
                                   data_dict)


def package_change_state(context: Context, data_dict: DataDict) -> AuthResult:
    user = context['user']
    package = logic_auth.get_package_object(context, data_dict)

    # use the logic for package_update
    authorized = authz.is_authorized_boolean('package_update',
                                                 context,
                                                 data_dict)
    if not authorized:
        return {
            'success': False,
            'msg': _('User %s not authorized to change state of package %s') %
                    (str(user), package.id)
        }
    else:
        return {'success': True}


def group_update(context: Context, data_dict: DataDict) -> AuthResult:
    group = logic_auth.get_group_object(context, data_dict)
    user = context['user']
    authorized = authz.has_user_permission_for_group_or_org(group.id,
                                                                user,
                                                                'update')
    if not authorized:
        return {'success': False,
                'msg': _('User %s not authorized to edit group %s') %
                        (str(user), group.id)}
    else:
        return {'success': True}


def organization_update(context: Context, data_dict: DataDict) -> AuthResult:
    group = logic_auth.get_group_object(context, data_dict)
    user = context['user']
    authorized = authz.has_user_permission_for_group_or_org(
        group.id, user, 'update')
    if not authorized:
        return {'success': False,
                'msg': _('User %s not authorized to edit organization %s') %
                        (user, group.id)}
    else:
        return {'success': True}


def group_change_state(context: Context, data_dict: DataDict) -> AuthResult:
    user = context['user']
    group = logic_auth.get_group_object(context, data_dict)

    # use logic for group_update
    authorized = authz.is_authorized_boolean('group_update',
                                                 context,
                                                 data_dict)
    if not authorized:
        return {
            'success': False,
            'msg': _('User %s not authorized to change state of group %s') %
                    (str(user), group.id)
        }
    else:
        return {'success': True}


def group_edit_permissions(context: Context, data_dict: DataDict) -> AuthResult:
    user = context['user']
    group = logic_auth.get_group_object(context, data_dict)

    authorized = authz.has_user_permission_for_group_or_org(
        group.id, user, 'update')

    if not authorized:
        return {
            'success': False,
            'msg': _('User %s not authorized to'
                     ' edit permissions of group %s') %
            (str(user), group.id)}
    else:
        return {'success': True}


@logic.auth_allow_anonymous_access
def user_update(context: Context, data_dict: DataDict) -> AuthResult:
    user = context['user']

    # FIXME: We shouldn't have to do a try ... except here, validation should
    # have ensured that the data_dict contains a valid user id before we get to
    # authorization.
    try:
        user_obj = logic_auth.get_user_object(context, data_dict)
    except logic.NotFound:
        return {'success': False, 'msg': _('User not found')}

    # If the user has a valid reset_key in the db, and that same reset key
    # has been posted in the data_dict, we allow the user to update
    # her account without using her password or API key.
    if user_obj.reset_key and 'reset_key' in data_dict:
        if user_obj.reset_key == data_dict['reset_key']:
            return {'success': True}

    if not user:
        return {'success': False,
                'msg': _('Have to be logged in to edit user')}

    if user == user_obj.name:
        # Allow users to update their own user accounts.
        return {'success': True}
    else:
        # Don't allow users to update other users' accounts.
        return {'success': False,
                'msg': _('User %s not authorized to edit user %s') %
                        (user, user_obj.id)}


def task_status_update(context: Context, data_dict: DataDict) -> AuthResult:
    # sysadmins only
    user = context['user']
    return {
        'success': False,
        'msg': _('User %s not authorized to update task_status table') % user
    }


def vocabulary_update(context: Context, data_dict: DataDict) -> AuthResult:
    # sysadmins only
    return {'success': False}


def term_translation_update(context: Context,
                            data_dict: DataDict) -> AuthResult:
    # sysadmins only
    user = context['user']
    return {
        'success': False,
        'msg': _('User %s not authorized to update term_translation table') % user
    }


def package_owner_org_update(context: Context,
                             data_dict: DataDict) -> AuthResult:
    # sysadmins only
    return {'success': False}


def bulk_update_private(context: Context, data_dict: DataDict) -> AuthResult:
    org_id = data_dict.get('org_id')
    user = context['user']
    authorized = authz.has_user_permission_for_group_or_org(
        org_id, user, 'update')
    if not authorized:
        return {'success': False}
    return {'success': True}


def bulk_update_public(context: Context, data_dict: DataDict) -> AuthResult:
    org_id = data_dict.get('org_id')
    user = context['user']
    authorized = authz.has_user_permission_for_group_or_org(
        org_id, user, 'update')
    if not authorized:
        return {'success': False}
    return {'success': True}


def bulk_update_delete(context: Context, data_dict: DataDict) -> AuthResult:
    org_id = data_dict.get('org_id')
    user = context['user']
    authorized = authz.has_user_permission_for_group_or_org(
        org_id, user, 'update')
    if not authorized:
        return {'success': False}
    return {'success': True}


def config_option_update(context: Context, data_dict: DataDict) -> AuthResult:
    '''Update the runtime-editable configuration options

       Only sysadmins can do it
    '''
    return {'success': False}
