import json

import tornado.testing
import tornado.web

from server import Dial_Set_Easing_Dial


class FakeDialHandler:
    def __init__(self):
        self.easing_calls = []
        self.reload_calls = []

    def dial_set_easing_dial(self, dial_uid, step=None, period=None):
        self.easing_calls.append((dial_uid, step, period))
        return True

    def dial_reload_info_from_database(self, dial_uid):
        self.reload_calls.append(dial_uid)
        return {}


class FakeConfig:
    def __init__(self):
        self.updates = []

    def is_valid_api_key(self, key):
        return key == 'testkey'

    def update_dial_db_cell_with_dict(self, dial_uid, values_dict):
        self.updates.append((dial_uid, values_dict))


class EasingDialTestCase(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        self.fake_handler = FakeDialHandler()
        self.fake_config = FakeConfig()
        handlers_config = {"handler": self.fake_handler, "config": self.fake_config}
        return tornado.web.Application([
            (r"/api/v0/dial/([0-9A-F]*?)/easing/dial", Dial_Set_Easing_Dial, handlers_config),
        ])

    def test_step_only_does_not_crash(self):
        response = self.fetch("/api/v0/dial/ABC123/easing/dial?key=testkey&step=5")
        body = json.loads(response.body)

        assert response.code == 200
        assert body['status'] == 'ok'
        assert self.fake_config.updates == [('ABC123', {'easing_dial_step': 5})]

    def test_period_only_does_not_crash(self):
        response = self.fetch("/api/v0/dial/ABC123/easing/dial?key=testkey&period=250")
        body = json.loads(response.body)

        assert response.code == 200
        assert body['status'] == 'ok'
        assert self.fake_config.updates == [('ABC123', {'easing_dial_period': 250})]

    def test_step_and_period_both_update(self):
        response = self.fetch("/api/v0/dial/ABC123/easing/dial?key=testkey&step=5&period=250")
        body = json.loads(response.body)

        assert response.code == 200
        assert body['status'] == 'ok'
        assert self.fake_config.updates == [
            ('ABC123', {'easing_dial_step': 5, 'easing_dial_period': 250})
        ]
