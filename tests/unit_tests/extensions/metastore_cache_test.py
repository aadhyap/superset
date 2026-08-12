# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from typing import Any
from uuid import uuid3

from flask import Flask
from pytest_mock import MockerFixture

from superset.extensions.metastore_cache import SupersetMetastoreCache
from superset.key_value.types import (
    JsonKeyValueCodec,
    PickleKeyValueCodec,
)

KEY = "foo"


def build_cache(app: Flask, config: dict[str, Any]) -> SupersetMetastoreCache:
    cache = SupersetMetastoreCache.factory(app, config, [], {})
    assert isinstance(cache, SupersetMetastoreCache)
    return cache


def test_factory_defaults_to_json_codec(app: Flask) -> None:
    """Without an explicit `CODEC`, the safe JSON codec is used."""
    cache = build_cache(app, {})
    assert isinstance(cache.codec, JsonKeyValueCodec)


def test_factory_uses_explicitly_configured_pickle_codec(app: Flask) -> None:
    """Pickle deserialization requires an explicit opt-in via `CODEC`."""
    codec = PickleKeyValueCodec()
    cache = build_cache(app, {"CODEC": codec})
    assert cache.codec is codec


def test_factory_uses_explicitly_configured_json_codec(app: Flask) -> None:
    codec = JsonKeyValueCodec()
    cache = build_cache(app, {"CODEC": codec})
    assert cache.codec is codec


def test_get_treats_undecodable_entry_as_miss(
    app: Flask, mocker: MockerFixture
) -> None:
    """A value written by another codec (e.g. legacy pickle entries) is a miss."""
    cache = build_cache(app, {})
    entry = mocker.MagicMock()
    entry.value = PickleKeyValueCodec().encode({"foo": "bar"})
    entry.is_expired.return_value = False
    mocker.patch(
        "superset.daos.key_value.KeyValueDAO.get_entry",
        return_value=entry,
    )
    assert cache.get(KEY) is None
    assert cache.has(KEY) is False


def test_get_treats_undecodable_pickle_entry_as_miss(
    app: Flask, mocker: MockerFixture
) -> None:
    """A pickle-configured cache reading a JSON entry is a miss, not an error."""
    cache = build_cache(app, {"CODEC": PickleKeyValueCodec()})
    entry = mocker.MagicMock()
    entry.value = JsonKeyValueCodec().encode({"foo": "bar"})
    entry.is_expired.return_value = False
    mocker.patch(
        "superset.daos.key_value.KeyValueDAO.get_entry",
        return_value=entry,
    )
    assert cache.get(KEY) is None


def test_get_returns_json_encoded_entry(app: Flask, mocker: MockerFixture) -> None:
    cache = build_cache(app, {})
    entry = mocker.MagicMock()
    entry.value = JsonKeyValueCodec().encode({"foo": "bar"})
    entry.is_expired.return_value = False
    mocker.patch(
        "superset.daos.key_value.KeyValueDAO.get_entry",
        return_value=entry,
    )
    assert cache.get(KEY) == {"foo": "bar"}


def test_get_key_is_namespaced(app: Flask) -> None:
    cache = build_cache(app, {"CACHE_KEY_PREFIX": "prefix"})
    assert cache.get_key(KEY) == uuid3(cache.namespace, KEY)
