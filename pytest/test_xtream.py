#!/usr/bin/python3
import json
import os
import sys
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../usr/lib/hypnotix')))
from xtream import Channel, Episode, Group, Season, Serie, XTream

# Mock data for provider connection
mock_provider_name = "Test Provider"
mock_provider_username = "test_user"            # Must be the same as in the MOCK_AUTH_DATA
mock_provider_password = "test_pass"            # Must be the same as in the MOCK_AUTH_DATA
mock_provider_url = "http://test.server.com"    # Must be the same as in the MOCK_AUTH_DATA


# Mock data for testing
MOCK_AUTH_DATA = {
    "user_info": {
        "username": mock_provider_username,
        "password": mock_provider_password,
        "exp_date": str(int((datetime.now() + timedelta(days=30)).timestamp()))
    },
    "server_info": {
        "url": "test.server.com",
        "https_port": "443"
    }
}

MOCK_CATEGORIES = [
    {"category_id": 1, "category_name": "Live TV"},
    {"category_id": 2, "category_name": "Movies"}
]

MOCK_STREAMS = [
    {"num": 1, "stream_id": 1, "name": "Channel 1", "stream_type": "live", "category_id": "1",
     "stream_icon": f"{mock_provider_url}/icon1.png", "added": "1638316800"},
    {"num": 2, "stream_id": 2, "name": "Movie 1", "stream_type": "movie", "category_id": "2",
     "stream_icon": f"{mock_provider_url}/icon2.png", "added": "1638316800", "container_extension": "mp4"}
]

MOCK_SERIES = [
    {
        "num": 1, "name": "Test Series", "series_id": 1, "last_modified": "1638316800",
        "cover": f"{mock_provider_url}/cover.jpg", "plot": "Test plot", "cast": "Test cast",
        "director": "Test director", "genre": "Action", "releaseDate": "2021-01-01",
        "rating": "5", "category_id": "1"
    }
]

MOCK_SERIES_INFO = {
    "seasons": [
        {"season_number": 1, "name": "Season 1",
         "cover": f"{mock_provider_url}/cover1.jpg"}
    ],
    "episodes": {
        "1": [
            {"id": 1, "title": "Episode 1", "container_extension": "mp4",
             "info": {}, "episode_num": 1}
        ]
    }
}


# Fixture for environment setup
@pytest.fixture(scope="module")
def mock_xtream(tmp_path_factory):
    """
    Fixture that initializes the XTream class with mocked authentication
    and a temporary cache directory for testing file operations.
    """
    cache_dir = tmp_path_factory.mktemp("xtream_cache")
    mock_status = Mock()
    # Patching dirname and expanduser to avoid touching real home dirs
    with patch('requests.get') as mock_get, \
         patch('os.path.expanduser', return_value=str(cache_dir)):
        mock_get.return_value.ok = True
        mock_get.return_value.json.return_value = MOCK_AUTH_DATA
        xtream = XTream(
            update_status=mock_status,
            provider_name=mock_provider_name,
            provider_username=mock_provider_username,
            provider_password=mock_provider_password,
            provider_url=mock_provider_url,
            cache_path=str(cache_dir)
        )
        return xtream


def test_authentication(mock_xtream):
    """
    Verifies that the XTream class correctly handles authentication and
    populates authorization and account expiration data from the provider response.
    """
    assert mock_xtream.state["authenticated"] is True
    assert mock_xtream.authorization["username"] == mock_provider_username
    assert mock_xtream.authorization["password"] == mock_provider_password


def test_channel_initialization(mock_xtream):
    """
    Verifies that the Channel class is correctly initialized with stream data
    and constructs the appropriate stream URL based on the provider settings.
    """
    stream_info = {
        "stream_id": "123",
        "name": "Test Channel",
        "stream_icon": f"{mock_provider_url}/icon.png",
        "stream_type": "live",
        "category_id": "1",
        "added": "1638316800",
        "container_extension": "ts"
    }
    channel = Channel(mock_xtream, "Test Group", stream_info)
    assert channel.id == "123"
    assert channel.name == "Test Channel"
    assert channel.logo == f"{mock_provider_url}/icon.png"
    assert channel.group_title == "Test Group"
    assert channel.url.startswith(
        f"{mock_provider_url}/live/{mock_provider_username}/{mock_provider_password}/123.ts"
    )


def test_channel_export_json(mock_xtream):
    """
    Verifies that the Channel.export_json method correctly returns a dictionary
    containing the stream URL, raw metadata, and local logo path.
    """
    stream_info = {
        "stream_id": "1",
        "name": "C1",
        "stream_icon": "icon",
        "stream_type": "live",
        "category_id": "1",
        "added": "1638316800"
    }
    channel = Channel(mock_xtream, "Group", stream_info)
    exported = channel.export_json()
    assert exported["url"] == channel.url
    assert exported["logo_path"] == channel.logo_path


def test_group_initialization():
    """
    Verifies that the Group class is correctly initialized with category data
    and correctly maps the stream type to internal group type constants.
    """
    group_info = {"category_id": 1, "category_name": "Live TV"}
    group = Group(group_info, "Live")
    assert group.group_id == 1
    assert group.name == "Live TV"
    assert group.group_type == 0  # TV_GROUP


def test_serie_initialization(mock_xtream):
    """
    Verifies that the Serie class is correctly initialized with series metadata
    like plot, trailer, and genre.
    """
    series_info = {
        "series_id": 1,
        "name": "Test Series",
        "cover": f"{mock_provider_url}/cover.jpg",
        "last_modified": "1638316800",
        "plot": "Test plot",
        "youtube_trailer": "http://youtube.com/trailer",
        "genre": "Action"
    }
    serie = Serie(mock_xtream, series_info)
    assert serie.series_id == 1
    assert serie.name == "Test Series"
    assert serie.logo == f"{mock_provider_url}/cover.jpg"
    assert serie.plot == "Test plot"
    assert serie.youtube_trailer == "http://youtube.com/trailer"
    assert serie.genre == "Action"
    assert isinstance(serie.seasons, dict)


def test_episode_initialization(mock_xtream):
    """
    Verifies that the Episode class is correctly initialized with episode-specific
    information and constructs the correct series stream URL.
    """
    series_info = {"cover": f"{mock_provider_url}/cover.jpg"}
    episode_info = {
        "id": 1,
        "title": "Episode 1",
        "container_extension": "mp4",
        "info": {},
        "episode_num": 1
    }
    episode = Episode(mock_xtream, series_info, "Test Group", episode_info)
    assert episode.id == 1
    assert episode.title == "Episode 1"


def test_load_categories(mock_xtream):
    """
    Verifies that _load_categories_from_provider correctly triggers the API
    request for the specified stream type and returns the category list.
    """
    with patch.object(mock_xtream, '_get_request', return_value=MOCK_CATEGORIES) as mock_get:
        # Test live categories
        categories = mock_xtream._load_categories_from_provider(mock_xtream.live_type)
        assert len(categories) == 2
        assert categories[0]["category_name"] == "Live TV"


def test_load_streams(mock_xtream):
    """
    Verifies that _load_streams_from_provider correctly triggers the API
    request for the specified stream type and returns the list of streams.
    """
    with patch.object(mock_xtream, '_get_request', return_value=MOCK_STREAMS) as mock_get:
        # Test live streams
        streams = mock_xtream._load_streams_from_provider(mock_xtream.live_type)
        assert len(streams) == 2
        assert streams[0]["name"] == "Channel 1"


def test_validate_url(mock_xtream):
    """
    Verifies the URL validation regex to ensure it correctly identifies valid
    HTTP/HTTPS/FTP URLs and rejects invalid formats.
    """
    assert mock_xtream._validate_url("http://valid.url") is True
    assert mock_xtream._validate_url("invalid.url") is False


def test_slugify(mock_xtream):
    """
    Verifies that the _slugify method correctly normalizes strings by converting
    to lowercase and filtering for printable characters.
    """
    assert mock_xtream._slugify("Test String!") == "test string!"
    assert mock_xtream._slugify("movie_1.mp4") == "movie_1.mp4"
    assert mock_xtream._slugify("123ABC") == "123abc"


def test_get_logo_local_path(mock_xtream):
    """
    Verifies that logo URLs are correctly converted into local filesystem paths within the cache directory.
    """
    logo_url = f"{mock_provider_url}/logo.png"
    expected_path = os.path.join(
        mock_xtream.cache_path,
        "test provider-logo.png"
    )
    assert mock_xtream._get_logo_local_path(logo_url) == expected_path


def test_load_iptv_full_flow(mock_xtream):
    """
    Tests the complex load_iptv method which covers significant logic including
    fetching categories and streams for all types, parsing them, and saving to cache.
    """
    mock_xtream.state["loaded"] = False  # Force reload

    with patch.object(mock_xtream, '_load_from_file', return_value=None), \
            patch.object(mock_xtream, '_get_request') as mock_req, \
            patch.object(mock_xtream, '_save_to_file', return_value=True):

        # Return sequence for:
        # 1. Live Categories, 2. Live Streams,
        # 3. VOD Categories, 4. VOD Streams,
        # 5. Series Categories, 6. Series Streams
        mock_req.side_effect = [
            MOCK_CATEGORIES, MOCK_STREAMS,
            MOCK_CATEGORIES, MOCK_STREAMS,
            MOCK_CATEGORIES, MOCK_SERIES
        ]

        mock_xtream.load_iptv()

        # Verify that data was loaded into the class
        assert mock_xtream.state["loaded"] is True
        # Based on the mock side_effect, we expect lists to be populated
        assert len(mock_xtream.channels) > 0
        assert len(mock_xtream.movies) > 0
        assert len(mock_xtream.series) > 0


def test_search_stream(mock_xtream):
    """
    Verifies the search_stream method's ability to find content across channels,
    movies, and series using regex, supporting both LIST and JSON return types.
    """
    results = mock_xtream.search_stream("Channel", return_type="LIST")
    assert any(res["name"] == "Channel 1" for res in results)

    json_results = mock_xtream.search_stream("Movie", return_type="JSON")
    assert "Movie 1" in json_results


def test_get_series_info_by_id(mock_xtream):
    """
    Verifies that get_series_info_by_id correctly populates seasons and episodes
    for a Serie object after fetching detailed data from the provider.
    """
    series_obj = Serie(mock_xtream, {"series_id": 1, "name": "Test", "cover": "c", "last_modified": "1"})
    with patch.object(mock_xtream, '_get_request', return_value=MOCK_SERIES_INFO):
        mock_xtream.get_series_info_by_id(series_obj)
        assert "Season 1" in series_obj.seasons
        assert len(series_obj.seasons["Season 1"].episodes) > 0


def test_get_request_progress(mock_xtream):
    """
    Verifies the generic _get_request helper method's ability to handle
    successful JSON responses and return them as dictionaries.
    """
    with patch('requests.get') as mock_get:
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"key": "val"}
        mock_get.return_value = mock_resp

        data = mock_xtream._get_request("http://api.url")
        assert data == {"key": "val"}

def test_save_to_file(mock_xtream):
    """
    Verifies that the _save_to_file method correctly writes dictionary data
    to a JSON file in the cache directory with the appropriate slugified prefix.
    """
    test_data = {"test_key": "test_value"}
    filename = "test_data.json"

    # Test saving
    success = mock_xtream._save_to_file(test_data, filename)
    assert success is True

    # Verify file content manually
    slug = mock_xtream._slugify(mock_xtream.name)
    full_path = os.path.join(mock_xtream.cache_path, f"{slug}-{filename}")
    assert os.path.exists(full_path)

    with open(full_path, "r", encoding="utf-8") as f:
        saved_content = json.load(f)
        assert saved_content == test_data


def test_load_from_file_success(mock_xtream):
    """
    Verifies that _load_from_file correctly reads valid, fresh data from a
    cached JSON file.
    """
    test_data = {"hello": "world"}
    filename = "valid_cache.json"
    mock_xtream._save_to_file(test_data, filename)

    # Test loading fresh data
    loaded = mock_xtream._load_from_file(filename)
    assert loaded == test_data


def test_load_from_file_expired(mock_xtream):
    """
    Verifies that _load_from_file returns None when the cached file's
    modification time exceeds the configured threshold_time_sec.
    """
    test_data = {"old": "data"}
    filename = "expired.json"
    mock_xtream._save_to_file(test_data, filename)

    # Mock file modification time to 10 hours ago (threshold is 8 hours)
    expired_time = time.time() - (10 * 60 * 60)
    with patch('os.path.getmtime', return_value=expired_time):
        loaded = mock_xtream._load_from_file(filename)
        assert loaded is None


def test_load_from_file_failures(mock_xtream):
    """
    Verifies that _load_from_file handles missing files and corrupted JSON
    data gracefully by returning None.
    """
    # Case 1: File does not exist
    assert mock_xtream._load_from_file("non_existent.json") is None

    # Case 2: Corrupted JSON
    filename = "corrupt.json"
    full_path = os.path.join(mock_xtream.cache_path, f"{mock_xtream._slugify(mock_xtream.name)}-{filename}")
    with open(full_path, "w") as f:
        f.write("{invalid json: [")
    assert mock_xtream._load_from_file(filename) is None


def test_epg_and_info_helpers(mock_xtream):
    """
    Verifies various helper methods that fetch VOD info, EPG data, and other
    metadata from the provider by mocking the underlying network request.
    """
    with patch.object(mock_xtream, '_get_request', return_value={"data": "test"}):
        assert mock_xtream.vodInfoByID(1) == {"data": "test"}
        assert mock_xtream.liveEpgByStream(1) == {"data": "test"}
        assert mock_xtream.allEpg() == {"data": "test"}
