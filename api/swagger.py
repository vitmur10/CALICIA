import asyncio
import logging
from typing import Dict

import aiohttp
from aiogram import Bot
from aiogram.types import URLInputFile, Message

from bot.config import Config
from bot.db import Repo
from bot.db.models import Good


class SwaggerCRM:
    def __init__(self, api_key: str, loop: None = None):
        self.loop = asyncio.get_event_loop() if loop is None else loop
        self._headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        self._session = aiohttp.ClientSession(loop=self.loop, headers=self._headers)
        self._url = 'https://openapi.keycrm.app/v1'

    async def get_request(self, method: str, **kwargs) -> Dict:
        async with self._session.get(
            url=self._url + method,
            params=kwargs
        ) as resp:
            logging.info(await resp.text())
            return await resp.json()

    async def put_request(self, method: str, **kwargs):
        async with self._session.put(
            url=self._url + method,
            json=kwargs
        ) as resp:
            return await resp.json()

    async def post_request(self, method: str, **kwargs):
        async with self._session.post(
            url=self._url + method,
            json=kwargs
        ) as resp:
            return await resp.json()

    async def add_good(self, good: Dict, repo: Repo):
        repo.session.add(Good(id=good['sku'],
                              name=good['name'],
                              description=good['description'],
                              currency_code=good['currency_code'],
                              price=good['price'],
                              image_url=good['thumbnail_url'],
                              purchased_price=good['purchased_price'],
                              updated_at=good['updated_at']))

    async def close_session(self):
        await self._session.close()

    async def get_request_url(self, url: str):
        async with self._session.get(url=url, headers=self._headers) as resp:
            return await resp.json()
