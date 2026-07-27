from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from macbook.controller.mqtt_client import MQTTClient
from macbook.shared.config import MacBookConfig


@pytest.fixture
def config():
    cfg = MagicMock(spec=MacBookConfig)
    cfg.aws_region = "us-east-1"
    cfg.iot_endpoint = "test.iot.us-east-1.amazonaws.com"
    return cfg


class TestMQTTClient:
    @pytest.mark.asyncio
    @patch("macbook.controller.mqtt_client.mqtt_connection_builder")
    @patch("macbook.controller.mqtt_client.io.EventLoopGroup")
    @patch("macbook.controller.mqtt_client.io.DefaultHostResolver")
    @patch("macbook.controller.mqtt_client.io.ClientBootstrap")
    async def test_connect_builds_connection(
        self, _mock_bootstrap, _mock_resolver, _mock_elg, mock_builder, config
    ):
        mock_conn = MagicMock()
        mock_connect_future = MagicMock()
        mock_connect_future.result.return_value = None
        mock_conn.connect.return_value = mock_connect_future
        mock_builder.websockets_with_default_aws_signing.return_value = mock_conn

        client = MQTTClient(config)
        await client.connect()
        mock_builder.websockets_with_default_aws_signing.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe(self, config):
        client = MQTTClient(config)
        client._connection = MagicMock()
        client._connected.set()

        callback = AsyncMock()
        await client.subscribe("reel/generate", callback)

        client._connection.subscribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish(self, config):
        client = MQTTClient(config)
        client._connection = MagicMock()
        client._connected.set()

        await client.publish("reel/completed", {"job_id": "123"})

        client._connection.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, config):
        mock_conn = MagicMock()
        client = MQTTClient(config)
        client._connection = mock_conn

        await client.disconnect()

        mock_conn.disconnect.assert_called_once()
