from django.test import override_settings

from bedrock.wordpress import api
from bedrock.wordpress.models import BlogPost

import pytest
import responses
from pathlib2 import Path


TEST_DATA = Path(__file__).with_name('test_data')
TEST_WP_BLOGS = {
    'firefox': {
        'url': 'https://blog.mozilla.org/firefox/',
        'name': 'The Firefox Frontier',
        'num_posts': 10,
    },
}


def get_test_file_content(filename):
    with TEST_DATA.joinpath(filename).open() as fh:
        return fh.read()


def setup_responses():
    posts_url = api._api_url(TEST_WP_BLOGS['firefox']['url'], 'posts', None)
    tags_url = api._api_url(TEST_WP_BLOGS['firefox']['url'], 'tags', None)
    media_url = api._api_url(TEST_WP_BLOGS['firefox']['url'], 'media', 75)
    responses.add(responses.GET, posts_url, body=get_test_file_content('posts.json'))
    responses.add(responses.GET, tags_url, body=get_test_file_content('tags.json'))
    responses.add(responses.GET, media_url, body=get_test_file_content('media_75.json'))


@responses.activate
@override_settings(WP_BLOGS=TEST_WP_BLOGS)
def test_get_posts_data():
    setup_responses()
    data = api.get_posts_data('firefox')
    assert data['wp_blog_slug'] == 'firefox'
    assert data['posts'][0]['tags'] == ['browser', 'fastest']
    assert not data['posts'][0]['featured_media']
    assert not data['posts'][1]['featured_media']
    assert data['posts'][2]['featured_media']['id'] == 75
    assert len(responses.calls) == 3


@responses.activate
@override_settings(WP_BLOGS=TEST_WP_BLOGS)
@pytest.mark.django_db
def test_refresh_posts():
    setup_responses()
    BlogPost.objects.refresh('firefox')
    blog = BlogPost.objects.filter_by_blog('firefox')
    assert len(blog) == 3
    bp = blog.get(wp_id=10)
    assert bp.tags == ['browser', 'fastest']
    assert bp.wp_blog_slug == 'firefox'
    bp = blog.get(wp_id=74)
    assert bp.tags == ['fastest', 'privacy', 'programming', 'rust', 'security']
    assert bp.featured_media['id'] == 75
    assert bp.get_featured_image_url('large').endswith('Put-Your-Trust-in-Rust-600x315.png')


@responses.activate
@override_settings(WP_BLOGS=TEST_WP_BLOGS)
@pytest.mark.django_db
def test_filter_by_tags():
    setup_responses()
    BlogPost.objects.refresh('firefox')
    blog = BlogPost.objects.filter_by_blog('firefox')
    assert len(blog.filter_by_tags('browser')) == 1
    assert len(blog.filter_by_tags('fastest')) == 3
    assert len(blog.filter_by_tags('browser', 'jank')) == 2
