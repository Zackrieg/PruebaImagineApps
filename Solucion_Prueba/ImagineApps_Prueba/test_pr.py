from apis import *
import httpx
import pytest

from fastapi import FastAPI
from main import app

BASE_URL = "http://localhost:8000"

class DotDict(dict):
    _getattr_ = dict.get
    _setattr_ = dict.__setitem__
    _delattr_ = dict.__delitem__

form_data = DotDict()
form_data.username = "Leidy"
form_data.password = "avispita"


@pytest.mark.asyncio
async def test_token():
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        response = await login_for_access_token(form_data)
        token_data = response
        assert "access_token" in token_data

@pytest.mark.asyncio
async def test_create_subject_with_token():
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        response_token = await login_for_access_token(form_data)
        print(response_token)
        response = await create_subject({"name": "Artes"}, response_token["access_token"])
        assert response.status_code == 200  # Debe ser un estado de éxito
        assert response.json()["name"] == "Artes"