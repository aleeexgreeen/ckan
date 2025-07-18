# encoding: utf-8

import json
import pytest

import sqlalchemy as sa
import sqlalchemy.orm as orm

import ckan.lib.create_test_data as ctd
import ckan.model as model
from ckan.tests import helpers
from ckan.plugins.toolkit import ValidationError, job_from_id
import ckan.tests.factories as factories
from ckan.logic import NotFound
import ckanext.datastore.backend.postgres as db
from ckanext.datastore.tests.helpers import (
    set_url_type,
    when_was_last_analyze,
    execute_sql,
)


class TestDatastoreDelete(object):
    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins", "with_request_context")
    def test_delete_basic(self):
        resource = factories.Resource(url_type='datastore')
        data = {
            "resource_id": resource["id"],
            "aliases": u"b\xfck2",
            "fields": [
                {"id": "book", "type": "text"},
                {"id": "author", "type": "text"},
                {"id": "rating with %", "type": "text"},
            ],
            "records": [
                {
                    "book": "annakarenina",
                    "author": "tolstoy",
                    "rating with %": "90%",
                },
                {
                    "book": "warandpeace",
                    "author": "tolstoy",
                    "rating with %": "42%",
                },
            ],
        }
        helpers.call_action("datastore_create", **data)
        data = {"resource_id": resource["id"]}
        helpers.call_action("datastore_delete", **data)

        resobj = model.Resource.get(data["resource_id"])
        assert resobj.extras.get('datastore_active') is False
        assert resobj.last_modified

        results = execute_sql(
            u"select 1 from pg_views where viewname = :name",
            {"name": "b\xfck2"}
        )
        assert results.rowcount == 0

        # check the table is gone
        results = execute_sql(
            u"""SELECT table_name
            FROM information_schema.tables
            WHERE table_name=:name;""",
            {"name": resource["id"]},
        )
        assert results.rowcount == 0

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins", "with_request_context")
    def test_calculate_record_count_is_false(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "fields": [
                {"id": "name", "type": "text"},
                {"id": "age", "type": "text"},
            ],
            "records": [
                {"name": "Sunita", "age": "51"},
                {"name": "Bowan", "age": "68"},
            ],
        }
        helpers.call_action("datastore_create", **data)
        data = {
            "resource_id": resource["id"],
            "filters": {"name": "Bowan"},
            "force": True,
        }
        helpers.call_action("datastore_delete", **data)
        last_analyze = when_was_last_analyze(resource["id"])
        assert last_analyze is None

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins", "with_request_context")
    @pytest.mark.flaky(reruns=2)  # because analyze is sometimes delayed
    def test_calculate_record_count(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "fields": [
                {"id": "name", "type": "text"},
                {"id": "age", "type": "text"},
            ],
            "records": [
                {"name": "Sunita", "age": "51"},
                {"name": "Bowan", "age": "68"},
            ],
        }
        helpers.call_action("datastore_create", **data)
        data = {
            "resource_id": resource["id"],
            "filters": {"name": "Bowan"},
            "calculate_record_count": True,
            "force": True,
        }
        helpers.call_action("datastore_delete", **data)
        last_analyze = when_was_last_analyze(resource["id"])
        assert last_analyze is not None


class TestDatastoreRecordsDelete(object):
    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins", "with_request_context")
    def test_delete_records_basic(self):
        resource = factories.Resource(url_type='datastore')
        data = {
            "resource_id": resource["id"],
            "aliases": u"b\xfck2",
            "fields": [
                {"id": "book", "type": "text"},
                {"id": "author", "type": "text"},
                {"id": "rating with %", "type": "text"},
            ],
            "records": [
                {
                    "book": "annakarenina",
                    "author": "tolstoy",
                    "rating with %": "90%",
                },
                {
                    "book": "warandpeace",
                    "author": "tolstoy",
                    "rating with %": "42%",
                },
            ],
        }
        helpers.call_action("datastore_create", **data)
        data = {"resource_id": resource["id"], "filters": {}}
        helpers.call_action("datastore_records_delete", **data)

        results = execute_sql(
            u"select 1 from pg_views where viewname = :name",
            {"name": "b\xfck2"}
        )
        assert results.rowcount == 1

        # check the table still exists
        results = execute_sql(
            u"""SELECT table_name
            FROM information_schema.tables
            WHERE table_name=:name;""",
            {"name": resource["id"]},
        )
        assert results.rowcount == 1

        resource = model.Resource.get(resource["id"])
        assert resource.extras.get('datastore_active') is True

        # job scheduled to update last_modified
        assert job_from_id(
            f"{resource.id} datastore patch last_modified")

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins", "with_request_context")
    def test_delete_records_required_filters(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "fields": [
                {"id": "name", "type": "text"},
                {"id": "age", "type": "text"},
            ],
            "records": [
                {"name": "Sunita", "age": "51"},
                {"name": "Bowan", "age": "68"},
            ],
        }
        helpers.call_action("datastore_create", **data)

        data = {"resource_id": resource["id"], "force": True}
        with pytest.raises(ValidationError) as ve:
            helpers.call_action("datastore_records_delete", **data)
        expected = {u'filters': [u'Missing value']}
        err = ve.value.error_dict
        assert err == expected

        data = {"resource_id": resource["id"], "force": True, "filters": "error here"}
        with pytest.raises(ValidationError) as ve:
            helpers.call_action("datastore_records_delete", **data)
        expected = {u'filters': [u'Must be a dict']}
        err = ve.value.error_dict
        assert err == expected

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins", "with_request_context")
    def test_delete_records_text_int_filter(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "fields": [
                {"id": "text_field", "type": "text"},
            ],
            "records": [
                {"text_field": 25},
                {"text_field": 37},
            ],
        }
        helpers.call_action("datastore_create", **data)

        # can delete by int
        data = {"resource_id": resource["id"], "force": True,
                "filters": {"text_field": 25}}
        helpers.call_action("datastore_records_delete", **data)
        result = helpers.call_action("datastore_search",
                                     resource_id=resource["id"],
                                     include_total=True)
        assert result["total"] == 1

        # can delete by text
        data = {"resource_id": resource["id"], "force": True,
                "filters": {"text_field": "37"}}
        helpers.call_action("datastore_records_delete", **data)
        result = helpers.call_action("datastore_search",
                                     resource_id=resource["id"],
                                     include_total=True)
        assert result["total"] == 0


class TestDatastoreDeleteLegacy(object):
    sysadmin_user = None
    normal_user = None
    Session = None

    @pytest.fixture(autouse=True)
    def initial_data(self, clean_datastore, app, test_request_context):
        self.app = app
        ctd.CreateTestData.create()
        self.sysadmin_user = factories.Sysadmin()
        self.sysadmin_token = factories.APIToken(user=self.sysadmin_user["id"])
        self.sysadmin_token = self.sysadmin_token["token"]
        self.normal_user = factories.User()
        self.normal_user_token = factories.APIToken(user=self.normal_user["id"])
        self.normal_user_token = self.normal_user_token["token"]
        resource = model.Package.get("annakarenina").resources[0]
        self.data = {
            "resource_id": resource.id,
            "aliases": u"b\xfck2",
            "fields": [
                {"id": "book", "type": "text"},
                {"id": "author", "type": "text"},
                {"id": "rating with %", "type": "text"},
            ],
            "records": [
                {
                    "book": "annakarenina",
                    "author": "tolstoy",
                    "rating with %": "90%",
                },
                {
                    "book": "warandpeace",
                    "author": "tolstoy",
                    "rating with %": "42%",
                },
            ],
        }

        engine = db.get_write_engine()

        self.Session = orm.scoped_session(orm.sessionmaker(bind=engine))
        with test_request_context():
            set_url_type(
                model.Package.get("annakarenina").resources, self.sysadmin_user
            )

    def _create(self):
        headers = {"Authorization": self.sysadmin_token}
        res = self.app.post(
            "/api/action/datastore_create",
            json=self.data,
            headers=headers,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True
        return res_dict

    def _delete(self):
        data = {"resource_id": self.data["resource_id"]}
        headers = {"Authorization": self.sysadmin_token}
        res = self.app.post(
            "/api/action/datastore_delete",
            data=data,
            headers=headers,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True
        assert res_dict["result"] == data
        return res_dict

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("with_plugins", "with_request_context")
    def test_datastore_deleted_during_resource_deletion(self):
        package = factories.Dataset()
        data = {
            "resource": {
                "boo%k": "crime",
                "author": ["tolstoy", "dostoevsky"],
                "package_id": package["id"],
            }
        }

        result = helpers.call_action("datastore_create", **data)
        resource_id = result["resource_id"]
        helpers.call_action("resource_delete", id=resource_id)

        with pytest.raises(NotFound):
            helpers.call_action("datastore_search", resource_id=resource_id)

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins", "with_request_context")
    def test_datastore_deleted_during_resource_only_for_deleted_resource(self):
        package = factories.Dataset()
        data = {
            "boo%k": "crime",
            "author": ["tolstoy", "dostoevsky"],
            "package_id": package["id"],
        }

        result_1 = helpers.call_action(
            "datastore_create", resource=data.copy()
        )
        resource_id_1 = result_1["resource_id"]

        result_2 = helpers.call_action(
            "datastore_create", resource=data.copy()
        )
        resource_id_2 = result_2["resource_id"]

        res_1 = model.Resource.get(resource_id_1)
        res_2 = model.Resource.get(resource_id_2)

        # `synchronize_session=False` and session cache requires
        # refreshing objects
        model.Session.refresh(res_1)
        model.Session.refresh(res_2)
        assert res_1.extras["datastore_active"]
        assert res_2.extras["datastore_active"]

        helpers.call_action("resource_delete", id=resource_id_1)

        with pytest.raises(NotFound):
            helpers.call_action("datastore_search", resource_id=resource_id_1)
        with pytest.raises(NotFound):
            helpers.call_action("resource_show", id=resource_id_1)
        model.Session.refresh(res_1)
        model.Session.refresh(res_2)
        assert not res_1.extras["datastore_active"]
        assert res_2.extras["datastore_active"]

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_delete_invalid_resource_id(self, app):
        data = {"resource_id": "bad"}
        headers = {"Authorization": self.sysadmin_token}
        res = app.post(
            "/api/action/datastore_delete",
            data=data,
            headers=headers,
        )
        assert res.status_code == 404
        res_dict = json.loads(res.data)
        assert res_dict["success"] is False

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins", "with_request_context")
    def test_delete_filters(self, app):
        self._create()
        resource_id = self.data["resource_id"]

        # try and delete just the 'warandpeace' row
        data = {"resource_id": resource_id, "filters": {"book": "warandpeace"}}
        headers = {"Authorization": self.sysadmin_token}
        res = app.post(
            "/api/action/datastore_delete",
            json=data,
            headers=headers,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True

        c = self.Session.connection()
        result = c.execute(sa.text(
            u'select * from "{0}";'.format(resource_id)
        ))
        results = [r for r in result]
        assert len(results) == 1
        assert results[0].book == "annakarenina"
        self.Session.remove()

        # shouldn't delete anything
        data = {
            "resource_id": resource_id,
            "filters": {"book": "annakarenina", "author": "bad"},
        }

        headers = {"Authorization": self.sysadmin_token}
        res = app.post(
            "/api/action/datastore_delete",
            json=data,
            headers=headers,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True

        c = self.Session.connection()
        result = c.execute(sa.text(
            'select * from "{0}";'.format(resource_id)
        ))
        results = [r for r in result]
        assert len(results) == 1
        assert results[0].book == "annakarenina"
        self.Session.remove()

        # delete the 'annakarenina' row and also only use id
        data = {
            "id": resource_id,
            "filters": {"book": "annakarenina", "author": "tolstoy"},
        }
        headers = {"Authorization": self.sysadmin_token}
        res = app.post(
            "/api/action/datastore_delete",
            json=data,
            headers=headers,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True

        c = self.Session.connection()
        result = c.execute(sa.text(
            'select * from "{0}";'.format(resource_id)
        ))
        results = [r for r in result]
        assert len(results) == 0
        self.Session.remove()

        self._delete()

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins", "with_request_context")
    def test_delete_is_unsuccessful_when_called_with_invalid_filters(
        self, app
    ):
        self._create()

        data = {
            "resource_id": self.data["resource_id"],
            "filters": {"invalid-column-name": "value"},
        }

        headers = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_delete",
            json=data,
            headers=headers,
        )
        assert res.status_code == 409
        res_dict = json.loads(res.data)
        assert res_dict["success"] is False
        assert res_dict["error"].get("filters") is not None, res_dict["error"]

        self._delete()

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins", "with_request_context")
    def test_delete_is_unsuccessful_when_called_with_filters_not_as_dict(
        self, app
    ):
        self._create()

        data = {"resource_id": self.data["resource_id"], "filters": []}
        headers = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_delete",
            json=data,
            headers=headers,
        )
        assert res.status_code == 409
        res_dict = json.loads(res.data)
        assert res_dict["success"] is False
        assert res_dict["error"].get("filters") is not None, res_dict["error"]

        self._delete()

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins", "with_request_context")
    def test_delete_with_blank_filters(self, app):
        self._create()

        res = app.post(
            "/api/action/datastore_delete",
            json={"resource_id": self.data["resource_id"], "filters": {}},
            headers={"Authorization": self.normal_user_token},
        )
        assert res.status_code == 200
        results = json.loads(res.data)
        assert results["success"] is True

        res = app.post(
            "/api/action/datastore_search",
            json={"resource_id": self.data["resource_id"]},
            headers={"Authorization": self.normal_user_token},
        )
        assert res.status_code == 200
        results = json.loads(res.data)
        assert results["success"] is True
        assert len(results["result"]["records"]) == 0

        self._delete()


class TestDatastoreFunctionDelete(object):
    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_create_delete(self):
        helpers.call_action(
            u"datastore_function_create",
            name=u"test_nop",
            rettype=u"trigger",
            definition=u"BEGIN RETURN NEW; END;",
        )
        helpers.call_action(u"datastore_function_delete", name=u"test_nop")

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_delete_nonexistant(self):
        try:
            helpers.call_action(
                u"datastore_function_delete", name=u"test_not_there"
            )
        except ValidationError as ve:
            assert ve.error_dict == {
                u"name": [u"function test_not_there() does not exist"]
            }
        else:
            assert 0, u"no validation error"

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_delete_if_exists(self):
        helpers.call_action(
            u"datastore_function_delete",
            name=u"test_not_there_either",
            if_exists=True,
        )
