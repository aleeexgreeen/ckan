# encoding: utf-8

import unittest.mock as mock
from bs4 import BeautifulSoup
import pytest
import six
from ckan.lib.helpers import url_for
import ckan.logic as logic
import ckan.tests.helpers as helpers
import ckan.model as model
from ckan.tests import factories


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestGroupController(object):
    def test_bulk_process_throws_403_for_nonexistent_org(self, app):
        """Returns 403, not 404, because access check cannot be passed.
        """
        bulk_process_url = url_for(
            "organization.bulk_process", id="does-not-exist"
        )
        app.get(url=bulk_process_url, status=403)

    def test_page_thru_list_of_orgs_preserves_sort_order(self, app):
        orgs = sorted([factories.Organization() for _ in range(35)],
                      key=lambda o: o["name"])
        org_url = url_for("organization.index", sort="name desc")
        response = app.get(url=org_url)
        assert orgs[-1]["name"] in response
        assert orgs[0]["name"] not in response

        org_url = url_for("organization.index", sort="name desc", page=2)
        response = app.get(url=org_url)
        assert orgs[-1]["name"] not in response
        assert orgs[0]["name"] in response

    def test_page_thru_list_of_groups_preserves_sort_order(self, app):
        groups = sorted([factories.Group() for _ in range(35)],
                        key=lambda g: g["title"])
        group_url = url_for("group.index", sort="title desc")

        response = app.get(url=group_url)
        assert groups[-1]["title"] in response
        assert groups[0]["title"] not in response

        org_url = url_for("group.index", sort="title desc", page=2)
        response = app.get(url=org_url)
        assert groups[-1]["title"] not in response
        assert groups[0]["title"] in response

    def test_invalid_sort_param_does_not_crash(self, app):

        with app.flask_app.test_request_context():
            group_url = url_for("group.index", sort="title desc nope")

            app.get(url=group_url)

            group_url = url_for("group.index", sort="title nope desc nope")

            app.get(url=group_url)


@pytest.fixture
def sysadmin():
    data = factories.Sysadmin(password="correct123")
    group = factories.Group(user=data)
    identity = {"login": data["name"], "password": "correct123"}
    sysadmin = {"data": data, "group": group, "identity": identity}

    return sysadmin


@pytest.fixture
def user():
    data = factories.User(fullname="My Owner", password="correct123")
    group = factories.Group(user=data)
    identity = {"login": data["name"], "password": "correct123"}
    user = {"data": data, "group": group, "identity": identity}

    return user


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestGroupControllerNew(object):
    def test_not_logged_in(self, app):
        app.get(url=url_for("group.new"), status=403)

    def test_name_required(self, app, user):
        helpers.login_user(app, user["identity"])
        response = app.post(url=url_for("group.new"), data={"save": ""})

        assert "Name: Missing value" in response

    def test_saved(self, app, user):
        helpers.login_user(app, user["identity"])
        form = {"name": "saved", "save": ""}
        app.post(url=url_for("group.new"), data=form)

        group = model.Group.by_name(u"saved")
        assert group.title == u""
        assert group.type == "group"
        assert group.state == "active"

    def test_all_fields_saved(self, app, user):
        helpers.login_user(app, user["identity"])
        form = {
            "name": u"all-fields-saved",
            "title": "Science",
            "description": "Sciencey datasets",
            "image_url": "http://example.com/image.png",
            "save": "",
        }
        app.post(url=url_for("group.new"), data=form)

        group = model.Group.by_name(u"all-fields-saved")
        assert group.title == u"Science"
        assert group.description == "Sciencey datasets"

    def test_form_without_initial_data(self, app, user):
        helpers.login_user(app, user["identity"])
        url = url_for("group.new")
        resp = app.get(url=url)
        page = BeautifulSoup(resp.body)
        form = page.select_one('#group-edit')
        assert not form.select_one('[name=title]')['value']
        assert not form.select_one('[name=name]')['value']
        assert not form.select_one('[name=description]').text

    def test_form_with_initial_data(self, app, user):
        helpers.login_user(app, user["identity"])
        url = url_for("group.new", name="name",
                      description="description", title="title")
        resp = app.get(url=url)
        page = BeautifulSoup(resp.body)
        form = page.select_one('#group-edit')
        assert form.select_one('[name=title]')['value'] == "title"
        assert form.select_one('[name=name]')['value'] == "name"
        assert form.select_one('[name=description]').text == "description"


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestGroupControllerEdit(object):
    def test_not_logged_in(self, app):
        app.get(url=url_for("group.new"), status=403)

    def test_group_doesnt_exist(self, app, user):
        helpers.login_user(app, user["identity"])
        url = url_for("group.edit", id="doesnt_exist")
        app.get(url=url, status=404)

    def test_saved(self, app, user):
        helpers.login_user(app, user["identity"])
        group = factories.Group(user=user["data"])

        form = {"save": ""}
        app.post(url=url_for("group.edit", id=group["name"]), data=form)
        group = model.Group.by_name(group["name"])
        assert group.state == "active"

    def test_all_fields_saved(self, app, user):
        helpers.login_user(app, user["identity"])
        group = factories.Group(user=user["data"])

        form = {
            "name": u"all-fields-edited",
            "title": "Science",
            "description": "Sciencey datasets",
            "image_url": "http://example.com/image.png",
            "save": "",
        }
        app.post(url=url_for("group.edit", id=group["name"]), data=form)

        group = model.Group.by_name(u"all-fields-edited")
        assert group.title == u"Science"
        assert group.description == "Sciencey datasets"
        assert group.image_url == "http://example.com/image.png"

    def test_display_name_shown(self, app, user):
        helpers.login_user(app, user["identity"])
        group = factories.Group(
            name="display-name",
            title="Display name",
            user=user["data"]
        )

        form = {
            "name": "",
            "save": "",
        }
        resp = app.get(url=url_for("group.edit", id=group["name"]))
        page = BeautifulSoup(resp.body)
        breadcrumbs = page.select('.breadcrumb a')
        # Home -> Groups -> NAME -> Manage
        assert len(breadcrumbs) == 4
        # Verify that `NAME` is not empty, as well as other parts
        assert all([part.text for part in breadcrumbs])

        resp = app.post(url=url_for("group.edit", id=group["name"]), data=form)
        page = BeautifulSoup(resp.body)
        breadcrumbs = page.select('.breadcrumb a')
        # Home -> Groups -> NAME -> Manage
        assert len(breadcrumbs) == 4
        # Verify that `NAME` is not empty, as well as other parts
        assert all([part.text for part in breadcrumbs])


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestGroupRead(object):
    def test_group_read(self, app):
        group = factories.Group()
        response = app.get(url=url_for("group.read", id=group["name"]))
        assert group["title"] in response
        assert group["description"] in response

    def test_redirect_when_given_id(self, app):
        group = factories.Group()

        response = app.get(
            url_for("group.read", id=group["id"]),
            status=302,
            follow_redirects=False,
        )
        location = response.headers["location"]
        expected_url = url_for("group.read", id=group["name"], _external=True)
        assert location == expected_url

    def test_no_redirect_loop_when_name_is_the_same_as_the_id(self, app):
        group = factories.Group(id="abc", name="abc")

        # 200 == no redirect
        app.get(url_for("group.read", id=group["id"]), status=200)

    def test_search_with_extra_params(self, app):
        group = factories.Group()
        url = url_for('group.read', id=group['id'])
        url += '?ext_a=1&ext_a=2&ext_b=3'
        search_result = {
            'count': 0,
            'sort': "score desc, metadata_modified desc",
            'facets': {},
            'search_facets': {},
            'results': []
        }
        search = mock.Mock(return_value=search_result)
        logic._actions['package_search'] = search
        app.get(url)
        search.assert_called()
        extras = search.call_args[0][1]['extras']
        assert extras == {'ext_a': ['1', '2'], 'ext_b': '3'}


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestGroupDelete(object):

    def test_owner_delete(self, app, user):
        helpers.login_user(app, user["identity"])
        response = app.post(
            url=url_for("group.delete", id=user["group"]["id"]),
            data={"delete": ""}
        )
        assert response.status_code == 200
        group = helpers.call_action(
            "group_show", id=user["group"]["id"]
        )
        assert group["state"] == "deleted"

    def test_sysadmin_delete(self, app, sysadmin):
        helpers.login_user(app, sysadmin["identity"])

        response = app.post(
            url=url_for("group.delete", id=sysadmin["group"]["id"]),
            data={"delete": ""}
        )
        assert response.status_code == 200
        group = helpers.call_action(
            "group_show", id=sysadmin["group"]["id"]
        )
        assert group["state"] == "deleted"

    def test_non_authorized_user_trying_to_delete_fails(
        self, app, user
    ):  
        data = factories.User(password="correct123")
        identity = {"login": data["name"], "password": "correct123"}
        helpers.login_user(app, identity)
        app.get(
            url=url_for("group.delete", id=user["group"]["id"]),
            status=403,
        )

        group = helpers.call_action(
            "group_show", id=user["group"]["id"]
        )
        assert group["state"] == "active"

    def test_anon_user_trying_to_delete_fails(self, app, user):
        app.get(
            url=url_for("group.delete", id=user["group"]["id"]),
            status=403,
        )

        group = helpers.call_action(
            "group_show", id=user["group"]["id"]
        )
        assert group["state"] == "active"


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestGroupMembership(object):
    def _create_group(self, owner_username, users=None):
        """Create a group with the owner defined by owner_username and
        optionally with a list of other users."""
        if users is None:
            users = []
        context = {"user": owner_username, "ignore_auth": True}
        group = helpers.call_action(
            "group_create", context=context, name="test-group", users=users
        )
        return group

    def _get_group_add_member_page(self, app, user, group_name):
        helpers.login_user(app, user["identity"])
        url = url_for("group.member_new", id=group_name)
        response = app.get(url=url)
        return response

    def test_membership_list(self, app, user):
        """List group admins and members"""
        user_two = factories.User(fullname="User Two")

        other_users = [{"name": user_two["id"], "capacity": "member"}]

        group = self._create_group(user["data"]["name"], other_users)

        member_list_url = url_for("group.members", id=group["id"])
        helpers.login_user(app, user["identity"])

        member_list_response = app.get(member_list_url)

        assert "2 members" in member_list_response

        member_response_html = BeautifulSoup(member_list_response.body)
        user_names = [
            u.string
            for u in member_response_html.select("#member-table td.media a")
        ]
        roles = [
            r.next_sibling.next_sibling.string
            for r in member_response_html.select("#member-table td.media")
        ]

        user_roles = dict(zip(user_names, roles))

        assert user_roles["My Owner"] == "Admin"
        assert user_roles["User Two"] == "Member"

    def test_membership_add(self, app, user):
        """Member can be added via add member page"""
        factories.User(fullname="My Fullname", name="my-user")
        group = self._create_group(user["data"]["name"])

        helpers.login_user(app, user["identity"])
        url = url_for("group.member_new", id=group["name"])
        add_response = app.post(
            url,
            data={"save": "", "username": "my-user", "role": "member"},
        )

        assert "2 members" in add_response.body

        add_response_html = BeautifulSoup(add_response.body)
        user_names = [
            u.string
            for u in add_response_html.select("#member-table td.media a")
        ]
        roles = [
            r.next_sibling.next_sibling.string
            for r in add_response_html.select("#member-table td.media")
        ]

        user_roles = dict(zip(user_names, roles))

        assert user_roles["My Owner"] == "Admin"
        assert user_roles["My Fullname"] == "Member"

    def test_membership_add_by_email(self, app, mail_server, user):
        group = self._create_group(user["data"]["name"])
        url = url_for("group.member_new", id=group["name"])
        email = "invited_user@mailinator.com"
        helpers.login_user(app, user["identity"])
        app.post(
            url,
            data={"save": "", "email": email, "role": "member"},
            status=200
        )
        assert len(mail_server.get_smtp_messages()) == 1
        users = model.User.by_email(email)
        assert len(users) == 1, users
        user = users[0]
        assert user.email == email, user
        assert group["id"] in user.get_group_ids(capacity="member")

    def test_membership_edit_page(self, app, user):
        """If `user` parameter provided, render edit page."""
        member = factories.User(fullname="My Fullname", name="my-user")
        group = self._create_group(user["data"]["name"], users=[
            {'name': member['name'], 'capacity': 'admin'}
        ])

        url = url_for("group.member_new", id=group["name"], user=member['name'])
        helpers.login_user(app, user["identity"])
        response = app.get(url)

        page = BeautifulSoup(response.body)
        assert page.select_one('.page-heading').text.strip() == 'Edit Member'
        role_option = page.select_one('#role [selected]')
        assert role_option and role_option.get('value') == 'admin'
        assert page.select_one('#username').get('value') == member['name']

    def test_admin_add(self, app, user):
        """Admin can be added via add member page"""
        factories.User(fullname="My Fullname", name="my-user")
        group = self._create_group(user["data"]["name"])

        helpers.login_user(app, user["identity"])
        url = url_for("group.member_new", id=group["name"])
        add_response = app.post(
            url,
            data={"save": "", "username": "my-user", "role": "admin"},
        )

        assert "2 members" in add_response

        add_response_html = BeautifulSoup(add_response.body)
        user_names = [
            u.string
            for u in add_response_html.select("#member-table td.media a")
        ]
        roles = [
            r.next_sibling.next_sibling.string
            for r in add_response_html.select("#member-table td.media")
        ]

        user_roles = dict(zip(user_names, roles))

        assert user_roles["My Owner"] == "Admin"
        assert user_roles["My Fullname"] == "Admin"

    def test_remove_member(self, app, user):
        """Member can be removed from group"""
        user_two = factories.User(fullname="User Two")

        other_users = [{"name": user_two["id"], "capacity": "member"}]

        group = self._create_group(user["data"]["name"], other_users)

        remove_url = url_for(
            "group.member_delete", user=user_two["id"], id=group["id"]
        )

        helpers.login_user(app, user["identity"])

        remove_response = app.post(remove_url)
        assert helpers.body_contains(remove_response, "1 members")

        remove_response_html = BeautifulSoup(remove_response.body)
        user_names = [
            u.string
            for u in remove_response_html.select("#member-table td.media a")
        ]
        roles = [
            r.next_sibling.next_sibling.string
            for r in remove_response_html.select("#member-table td.media")
        ]

        user_roles = dict(zip(user_names, roles))

        assert len(user_roles.keys()) == 1
        assert user_roles["My Owner"] == "Admin"

    def test_member_users_cannot_add_members(self, app, user):

        group = factories.Group(
            users=[{"name": user["data"]["name"], "capacity": "member"}]
        )

        helpers.login_user(app, user["identity"])

        with app.flask_app.test_request_context():
            app.get(url_for("group.member_new", id=group["id"]), status=403)

            app.post(
                url_for("group.member_new", id=group["id"]),
                data={
                    "id": "test",
                    "username": "test",
                    "save": "save",
                    "role": "test",
                },
                status=403,
            )

    def test_anonymous_users_cannot_add_members(self, app):
        group = factories.Group()

        with app.flask_app.test_request_context():
            app.get(url_for("group.member_new", id=group["id"]), status=403)

            app.post(
                url_for("group.member_new", id=group["id"]),
                data={
                    "id": "test",
                    "username": "test",
                    "save": "save",
                    "role": "test",
                },
                status=403,
            )


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestGroupFollow:
    def test_group_follow(self, app, user):

        group = factories.Group()

        helpers.login_user(app, user["identity"])
        follow_url = url_for("group.follow", id=group["id"])
        response = app.post(follow_url)
        assert (
            "You are now following {0}".format(group["display_name"])
            in response
        )

    def test_group_follow_not_exist(self, app, user):
        """Pass an id for a group that doesn't exist"""

        helpers.login_user(app, user["identity"])
        follow_url = url_for("group.follow", id="not-here")
        response = app.post(follow_url, status=404)
        assert "Group not found" in response

    def test_group_unfollow(self, app, user):

        group = factories.Group()

        helpers.login_user(app, user["identity"])
        follow_url = url_for("group.follow", id=group["id"])
        app.post(follow_url)

        unfollow_url = url_for("group.unfollow", id=group["id"])
        unfollow_response = app.post(unfollow_url)

        assert (
            "You are no longer following {0}".format(group["display_name"])
            in unfollow_response
        )

    def test_group_unfollow_not_following(self, app, user):
        """Unfollow a group not currently following"""

        group = factories.Group()

        helpers.login_user(app, user["identity"])
        unfollow_url = url_for("group.unfollow", id=group["id"])
        unfollow_response = app.post(unfollow_url)

        assert (
            "You are not following {0}".format(group["id"])
            in unfollow_response
        )

    def test_group_unfollow_not_exist(self, app, user):
        """Unfollow a group that doesn't exist."""

        helpers.login_user(app, user["identity"])
        unfollow_url = url_for("group.unfollow", id="not-here")
        app.post(unfollow_url, status=404)

    def test_group_follower_list(self, app, sysadmin):
        """Following users appear on followers list page."""

        helpers.login_user(app, sysadmin["identity"])
        follow_url = url_for("group.follow", id=sysadmin["group"]["id"])
        app.post(follow_url)

        followers_url = url_for("group.followers", id=sysadmin["group"]["id"])

        # Only sysadmins can view the followers list pages
        followers_response = app.get(followers_url, status=200)
        assert sysadmin["data"]["name"] in followers_response


@pytest.mark.usefixtures("clean_db", "clean_index", "with_request_context")
class TestGroupSearch(object):
    """Test searching for groups."""

    def test_group_search(self, app):
        """Requesting group search (index) returns list of groups and search
        form."""

        factories.Group(name="grp-one", title="AGrp One")
        factories.Group(name="grp-two", title="AGrp Two")
        factories.Group(name="grp-three", title="Grp Three")
        index_response = app.get(url_for("group.index"))
        index_response_html = BeautifulSoup(index_response.body)
        grp_names = index_response_html.select(
            "ul.media-grid " "li.media-item " "h2.media-heading"
        )
        grp_names = [n.string for n in grp_names]

        assert len(grp_names) == 3
        assert "AGrp One" in grp_names
        assert "AGrp Two" in grp_names
        assert "Grp Three" in grp_names

    def test_group_search_results(self, app):
        """Searching via group search form returns list of expected groups."""
        factories.Group(name="grp-one", title="AGrp One")
        factories.Group(name="grp-two", title="AGrp Two")
        factories.Group(name="grp-three", title="Grp Three")

        search_response = app.get(
            url_for("group.index"), query_string={"q": "AGrp"}
        )
        search_response_html = BeautifulSoup(search_response.body)
        grp_names = search_response_html.select(
            "ul.media-grid " "li.media-item " "h2.media-heading"
        )
        grp_names = [n.string for n in grp_names]

        assert len(grp_names) == 2
        assert "AGrp One" in grp_names
        assert "AGrp Two" in grp_names
        assert "Grp Three" not in grp_names

    def test_group_search_no_results(self, app):
        """Searching with a term that doesn't apply returns no results."""

        factories.Group(name="grp-one", title="AGrp One")
        factories.Group(name="grp-two", title="AGrp Two")
        factories.Group(name="grp-three", title="Grp Three")

        search_response = app.get(
            url_for("group.index"), query_string={"q": "No Results Here"}
        )

        search_response_html = BeautifulSoup(search_response.body)
        grp_names = search_response_html.select(
            "ul.media-grid " "li.media-item " "h2.media-heading"
        )
        grp_names = [n.string for n in grp_names]

        assert len(grp_names) == 0
        assert 'No groups found for "No Results Here"' in search_response


@pytest.mark.usefixtures("clean_db", "clean_index", "with_request_context")
class TestGroupInnerSearch(object):
    """Test searching within an group."""

    def test_group_search_within_org(self, app):
        """Group read page request returns list of datasets owned by group."""
        grp = factories.Group()
        factories.Dataset(
            name="ds-one", title="Dataset One", groups=[{"id": grp["id"]}]
        )
        factories.Dataset(
            name="ds-two", title="Dataset Two", groups=[{"id": grp["id"]}]
        )
        factories.Dataset(
            name="ds-three", title="Dataset Three", groups=[{"id": grp["id"]}]
        )

        grp_url = url_for("group.read", id=grp["name"])
        grp_response = app.get(grp_url)
        grp_response_html = BeautifulSoup(grp_response.body)

        ds_titles = grp_response_html.select(
            ".dataset-list " ".dataset-item " ".dataset-heading a"
        )
        ds_titles = [t.string.strip() for t in ds_titles]

        assert "3 datasets found" in grp_response
        assert len(ds_titles) == 3
        assert "Dataset One" in ds_titles
        assert "Dataset Two" in ds_titles
        assert "Dataset Three" in ds_titles

    def test_group_search_within_org_results(self, app):
        """Searching within an group returns expected dataset results."""

        grp = factories.Group()
        factories.Dataset(
            name="ds-one", title="Dataset One", groups=[{"id": grp["id"]}]
        )
        factories.Dataset(
            name="ds-two", title="Dataset Two", groups=[{"id": grp["id"]}]
        )
        factories.Dataset(
            name="ds-three", title="Dataset Three", groups=[{"id": grp["id"]}]
        )

        grp_url = url_for("group.read", id=grp["name"])

        search_response = app.get(grp_url, query_string={"q": "One"})
        assert "1 dataset found for &#34;One&#34;" in search_response

        search_response_html = BeautifulSoup(search_response.body)

        ds_titles = search_response_html.select(
            ".dataset-list " ".dataset-item " ".dataset-heading a"
        )
        ds_titles = [t.string.strip() for t in ds_titles]

        assert len(ds_titles) == 1
        assert "Dataset One" in ds_titles
        assert "Dataset Two" not in ds_titles
        assert "Dataset Three" not in ds_titles

    def test_group_search_within_org_no_results(self, app):
        """Searching for non-returning phrase within an group returns no
        results."""

        grp = factories.Group()
        factories.Dataset(
            name="ds-one", title="Dataset One", groups=[{"id": grp["id"]}]
        )
        factories.Dataset(
            name="ds-two", title="Dataset Two", groups=[{"id": grp["id"]}]
        )
        factories.Dataset(
            name="ds-three", title="Dataset Three", groups=[{"id": grp["id"]}]
        )

        grp_url = url_for("group.read", id=grp["name"])
        search_response = app.get(grp_url, query_string={"q": "Nout"})

        assert helpers.body_contains(
            search_response, 'No datasets found for "Nout"'
        )

        search_response_html = BeautifulSoup(search_response.body)

        ds_titles = search_response_html.select(
            ".dataset-list " ".dataset-item " ".dataset-heading a"
        )
        ds_titles = [t.string for t in ds_titles]

        assert len(ds_titles) == 0


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestGroupIndex(object):
    def test_group_index(self, app):

        for i in range(1, 26):
            _i = "0" + str(i) if i < 10 else i
            factories.Group(
                name="test-group-{0}".format(_i),
                title="Test Group {0}".format(_i),
            )

        url = url_for("group.index")
        response = app.get(url)

        for i in range(1, 21):
            _i = "0" + str(i) if i < 10 else i
            assert "Test Group {0}".format(_i) in response

        assert "Test Group 21" not in response

        url = url_for("group.index", page=1)
        response = app.get(url)

        for i in range(1, 21):
            _i = "0" + str(i) if i < 10 else i
            assert "Test Group {0}".format(_i) in response

        assert "Test Group 21" not in response

        url = url_for("group.index", page=2)
        response = app.get(url)

        for i in range(21, 26):
            assert "Test Group {0}".format(i) in response

        assert "Test Group 20" not in response


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestActivity:
    def test_simple(self, app, user):
        """Checking the template shows the activity stream."""

        url = url_for("group.activity", id=user["group"]["id"])
        response = app.get(url)
        assert user["data"]["fullname"] in response
        assert "created the group" in response

    def test_create_group(self, app, user):

        url = url_for("group.activity", id=user["group"]["id"])
        response = app.get(url)
        assert (
            '<a href="/user/{}">{}'.format(
                user["data"]["name"], user["data"]["fullname"]
            ) in response
        )
        assert "created the group" in response
        assert (
            '<a href="/group/{}">{}'.format(user["group"]["name"], user["group"]["title"]) in response
        )

    def _clear_activities(self):
        model.Session.query(model.ActivityDetail).delete()
        model.Session.query(model.Activity).delete()
        model.Session.flush()

    def test_change_group(self, app, user):
        self._clear_activities()
        user["group"]["title"] = "Group with changed title"
        helpers.call_action(
            "group_update", context={"user": user["data"]["name"]}, **user["group"]
        )

        url = url_for("group.activity", id=user["group"]["id"])
        response = app.get(url)
        assert (
            '<a href="/user/{}">{}'.format(
                user["data"]["name"], user["data"]["fullname"]
            ) in response
        )
        assert "updated the group" in response
        assert (
            '<a href="/group/{}">{}'.format(
                user["group"]["name"], user["group"]["title"]
            )
            in response
        )

    def test_delete_group_using_group_delete(self, app, user):
        self._clear_activities()
        helpers.call_action(
            "group_delete", context={"user": user["data"]["name"]}, **user["group"]
        )

        url = url_for("group.activity", id=user["group"]["id"])
        helpers.login_user(app, user["identity"])
        app.get(url, status=404)
        # group_delete causes the Member to state=deleted and then the user
        # doesn't have permission to see their own deleted Group. Therefore you
        # can't render the activity stream of that group. You'd hope that
        # group_delete was the same as group_update state=deleted but they are
        # not...

    def test_delete_group_by_updating_state(self, app, user):
        self._clear_activities()
        user["group"]["state"] = "deleted"
        helpers.call_action(
            "group_update", context={"user": user["data"]["name"]}, **user["group"]
        )

        url = url_for("group.activity", id=user["group"]["id"])
        helpers.login_user(app, user["identity"])
        response = app.get(url)
        assert (
            '<a href="/user/{}">{}'.format(
                user["data"]["name"], user["data"]["fullname"]
            ) in response
        )
        assert "deleted the group" in response
        assert (
            '<a href="/group/{}">{}'.format(user["group"]["name"], user["group"]["title"]) in response
        )

    def test_create_dataset(self, app, user):
        self._clear_activities()
        dataset = factories.Dataset(groups=[{"id": user["group"]["id"]}], user=user["data"])

        url = url_for("group.activity", id=user["group"]["id"])
        response = app.get(url)
        page = BeautifulSoup(response.body)
        href = page.select_one(".dataset")
        assert (
            '<a href="/user/{}">{}'.format(
                user["data"]["name"], user["data"]["fullname"]
            ) in response
        )
        assert "created the dataset" in response
        assert dataset["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert dataset["title"] in href.text.strip()

    def test_change_dataset(self, app, user):

        dataset = factories.Dataset(groups=[{"id": user["group"]["id"]}], user=user["data"])
        self._clear_activities()
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_update", context={"user": user["data"]["name"]}, **dataset
        )

        url = url_for("group.activity", id=user["group"]["id"])
        response = app.get(url)
        page = BeautifulSoup(response.body)
        href = page.select_one(".dataset")
        assert (
            '<a href="/user/{}">{}'.format(
                user["data"]["name"], user["data"]["fullname"]
            ) in response
        )
        assert "updated the dataset" in response
        assert dataset["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert dataset["title"] in href.text.strip()

    def test_delete_dataset(self, app, user):
        dataset = factories.Dataset(groups=[{"id": user["group"]["id"]}], user=user["data"])
        self._clear_activities()
        helpers.call_action(
            "package_delete", context={"user": user["data"]["name"]}, **dataset
        )

        url = url_for("group.activity", id=user["group"]["id"])
        response = app.get(url)
        page = BeautifulSoup(response.body)
        href = page.select_one(".dataset")
        assert (
            '<a href="/user/{}">{}'.format(user["data"]["name"], user["data"]["fullname"]
                                           ) in response
        )
        assert "deleted the dataset" in response
        assert dataset["id"] in href.select_one("a")["href"].split("/", 2)[-1]
        assert dataset["title"] in href.text.strip()
