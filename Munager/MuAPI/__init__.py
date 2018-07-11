import json
from logging import getLogger
from urllib.parse import urljoin, urlencode

from tornado import gen
from tornado.httpclient import AsyncHTTPClient, HTTPRequest


class MuAPIError(Exception):
    pass


class User:
    def __init__(self, **entries):
        # for IDE hint
        self.id = None
        self.user_name = None
        self.passwd = None
        self.port = None
        self.method = None
        self.enable = None
        self.u = None
        self.d = None
        self.transfer_enable = None
        self.plugin = None
        self.plugin_opts = None
        self.__dict__.update(entries)
        # from Mu api
        # passwd: ss password
        # method: ss method

    @property
    def available(self):
        return self.u + self.d < self.transfer_enable and self.enable == 1


class MuAPI:
    def __init__(self, config):
        self.logger = getLogger()
        self.config = config
        self.node_id = self.config.get('node_id')
        self.url_base = self.config.get('sspanel_url')
        # self.delay_sample = self.config.get('delay_sample')
        self.client = AsyncHTTPClient()

    def _get_request(self, path, query=dict(), method='GET', json_data=None, form_data=None):
        url = urljoin(self.url_base, path)
        token = self.config.get('token', '')

        if method == 'GET':
            query.update({'token': token})
            query_s = '?' + urlencode(query)
            url += query_s
        elif method == 'POST':
            json_data['token'] = token

        req_para = dict(
            url=url,
            method=method,
            use_gzip=True,
        )
        headers = {
            'User-Agent': self.config.get('ua', 'shadowmanager')
        }
        if json_data:
            headers.update({
                'Content-Type': 'application/json; charset=utf-8',
            })
            req_para.update(
                body=json.dumps(json_data),
            )
        elif form_data:
            headers.update({
                'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
            })
            req_para.update(
                body=urlencode(form_data),
            )
        req_para.update(headers=headers)
        return HTTPRequest(**req_para)

    @gen.coroutine
    def _make_fetch(self, _request):
        try:
            response = yield self.client.fetch(_request)
            content = response.body.decode('utf-8')
            cont_json = json.loads(content, encoding='utf-8')
            if cont_json.get('ret') != 1:
                return False
            else:
                return True
        except Exception as e:
            self.logger.warning('exception at fetching url: {url}.'.format(url=_request.url))
            self.logger.exception(e)
            return False

    @gen.coroutine
    def get_users(self, key) -> dict:
        request = self._get_request('/api/users/nodes/{}'.format(self.node_id))
        response = yield self.client.fetch(request)
        content = response.body.decode('utf-8')
        cont_json = json.loads(content, encoding='utf-8')
        if cont_json.get('ret') != 1:
            raise MuAPIError(cont_json)
        ret = dict()
        for user in cont_json.get('data'):
            user['plugin'] = 'None'
            user['plugin_opts'] = 'None'
            ret[user.get(key)] = User(**user)
        return ret

    @gen.coroutine
    def post_online_user(self, amount):
        request = self._get_request(
            path='/api/nodes/online',
            method='POST',
            json_data={
                'node_id': self.node_id,
                'online_user': amount
            }
        )
        result = yield self._make_fetch(request)
        return result

    @gen.coroutine
    def upload_throughput(self, users) -> dict:
        """
        :param users:
            [
                {
                    "user_id": ,
                    "u": ,
                    "d":
                },
                ...
            ]
        :return:
        """
        json_data = dict(
            node_id=self.node_id,
            data=users
        )
        request = self._get_request('/api/traffic/upload', method='POST', json_data=json_data)
        response = yield self.client.fetch(request)
        content = response.body.decode('utf-8')
        cont_json = json.loads(content, encoding='utf-8')
        if cont_json.get('ret') != 1:
            raise MuAPIError(cont_json)
        return cont_json.get('data')

    @gen.coroutine
    def post_online_ip(self, data):
        json_data = dict(
            node_id=self.node_id,
            data=data
        )
        request = self._get_request(
            path='/api/nodes/aliveip',
            method='POST',
            json_data=json_data
        )
        result = yield self._make_fetch(request)
        return result

    @gen.coroutine
    def is_node_traffic_run_out(self):
        request = self._get_request(
            path='/api/nodes/{}'.format(self.node_id)
        )
        response = yield self.client.fetch(request)
        content = response.body.decode('utf-8')
        cont_json = json.loads(content, encoding='utf-8')
        if cont_json.get('ret') != 1:
            raise MuAPIError(cont_json)
        return cont_json.get('data', [])

    # @gen.coroutine
    # def get_delay(self) -> list:
    #     request = self._get_request(
    #         path='/mu/v2/node/delay',
    #         query=dict(
    #             sample=self.delay_sample,
    #         ),
    #     )
    #     response = yield self.client.fetch(request)
    #     content = response.body.decode('utf-8')
    #     cont_json = json.loads(content, encoding='utf-8')
    #     if cont_json.get('ret') != 1:
    #         raise MuAPIError(cont_json)
    #     return cont_json.get('data', [])

    # @gen.coroutine
    # def post_delay_info(self, formdata):
    #     request = self._get_request(
    #         path='/mu/v2/node/delay_info',
    #         method='POST',
    #         form_data=formdata,
    #     )
    #     result = yield self._make_fetch(request)
    #     return result

    # @gen.coroutine
    # def post_load(self, formdata):
    #     request = self._get_request(
    #         path='/mu/v2/node/info',
    #         method='POST',
    #         form_data=formdata,
    #     )
    #     result = yield self._make_fetch(request)
    #     return result
