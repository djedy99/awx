import pytest
from unittest import mock

# Django REST Framework
from rest_framework import exceptions
from rest_framework.generics import ListAPIView

# Django
from django.db.models.fields.reverse_related import ManyToManyRel
from django.db.models.fields.related import ManyToManyField
from django.urls import resolve

# AWX
from awx.main.views import ApiErrorView
from awx.api.versioning import reverse
from awx.api.views import JobList
from awx.api import serializers
from awx.api.generics import ListCreateAPIView, SubListAttachDetachAPIView, SubListCreateAttachDetachAPIView
from awx.main.signals import model_serializer_mapping


HTTP_METHOD_NAMES = [
    'get',
    'post',
    'put',
    'patch',
    'delete',
    'head',
    'options',
    'trace',
]


@pytest.fixture
def api_view_obj_fixture():
    return ApiErrorView()


@pytest.mark.parametrize('method_name', HTTP_METHOD_NAMES)
def test_exception_view_allow_http_methods(method_name):
    assert hasattr(ApiErrorView, method_name)


@pytest.mark.parametrize('method_name', HTTP_METHOD_NAMES)
def test_exception_view_raises_exception(api_view_obj_fixture, method_name):
    request_mock = mock.MagicMock()
    with pytest.raises(exceptions.APIException):
        getattr(api_view_obj_fixture, method_name)(request_mock)


def test_disable_post_on_v2_jobs_list():
    job_list = JobList()
    job_list.request = mock.MagicMock()
    assert ('POST' in job_list.allowed_methods) is False


def test_views_have_search_fields(all_views):
    # Gather any views that don't have search fields defined
    views_missing_search = []
    for View in all_views:
        if not issubclass(View, ListAPIView):
            continue
        view = View()
        if not hasattr(view, 'search_fields') or len(view.search_fields) == 0:
            views_missing_search.append(view)

    if views_missing_search:
        raise Exception(
            '{} views do not have search fields defined:\n{}'.format(
                len(views_missing_search),
                '\n'.join([v.__class__.__name__ + ' (model: {})'.format(getattr(v, 'model', type(None)).__name__) for v in views_missing_search]),
            )
        )


def test_global_creation_always_possible(all_views):
    """To not make life very difficult for clients, this test
    asserts that all creatable resources can be created by
    POSTing to the global resource list
    """
    views_by_model = {}
    for View in all_views:
        if not getattr(View, 'deprecated', False) and issubclass(View, ListAPIView) and hasattr(View, 'model'):
            if type(View.model) is property:
                continue  # special case for JobEventChildrenList
            views_by_model.setdefault(View.model, []).append(View)
    for model, views in views_by_model.items():
        creatable = False
        global_view = None
        creatable_view = None
        for View in views:
            if '{}ListView'.format(model.__name__) == View.__name__:
                global_view = View
            if issubclass(View, ListCreateAPIView) and not issubclass(View, SubListAttachDetachAPIView):
                creatable = True
                creatable_view = View
        if not creatable or not global_view:
            continue
        assert 'POST' in global_view().allowed_methods, 'Resource {} should be creatable in global list view {}. Can be created now in {}'.format(
            model, global_view, creatable_view
        )


def test_associate_views_are_m2m(all_views):
    for View in all_views:
        if not issubclass(View, SubListCreateAttachDetachAPIView):
            continue
        cls = View.parent_model

        # special exception for role teams
        relationship = View.relationship
        if View.relationship == 'member_role.parents':
            relationship = 'parents'

        for rel in relationship.split('.'):
            try:
                field = cls._meta.get_field(rel)
                cls = field.remote_field.model
            except Exception:
                print(View)
                raise
        assert isinstance(field, (ManyToManyField, ManyToManyRel)), f'The sublist view {View} is of {type(field)}, which is not a m2m'


def get_serializer_for_model(cls):
    """
    Go through a preference order to find the most representative serializer
    for the specified model
    """
    serializer_mapping = model_serializer_mapping()
    if cls in serializer_mapping:
        return serializer_mapping[cls]
    # not in activity stream serializer mapping, so just loop through serializers
    for name in dir(serializers):
        item = getattr(serializers, name)
        try:
            if issubclass(item, serializers.BaseSerializer) and hasattr(item.Meta, 'model'):
                if item.Meta.model is cls:
                    return item
        except TypeError:
            pass
    raise Exception(f'Could not find a serializer for {cls}')


def test_attach_detatch_views_are_marked(all_views):
    for View in all_views:
        if not issubclass(View, SubListCreateAttachDetachAPIView):
            continue

        parent_serializer = get_serializer_for_model(View.parent_model)
        cls_sublists = getattr(parent_serializer, 'sublists', ())
        found_classes = []
        for key, view_name in cls_sublists:
            url = reverse(f'api:{view_name}', kwargs={'pk': 42})
            related_view = resolve(url).func.view_class
            found_classes.append(related_view)
            if related_view is View:
                break
        else:
            lb = "\n"
            raise Exception(
                f'The view {View} is not listed in parent model {View.parent_model} serializer '
                f'{parent_serializer} declared sublists:{lb}{lb.join([str(pair) for pair in cls_sublists])}'
                f'{lb}{lb}Found views:{lb}{lb.join([str(v) for v in found_classes])}'
            )
