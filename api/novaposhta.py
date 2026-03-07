import asyncio

import aiohttp


class NovaPoshta:
    def __init__(self, api_key: str, loop: None = None):
        self.loop = asyncio.get_event_loop() if loop is None else loop
        self._data = {
            "apiKey": api_key,
        }
        self._session = aiohttp.ClientSession(loop=self.loop)
        self._url = 'https://api.novaposhta.ua/v2.0/json/'

    async def post_request(self, method: str, model: str = 'Address', **kwargs):
        request_data = self._data
        request_data["modelName"] = model
        request_data["calledMethod"] = method
        request_data["methodProperties"] = kwargs
        async with self._session.post(
            url=self._url,
            json=request_data
        ) as resp:
            return await resp.json()

    async def close_session(self):
        await self._session.close()
