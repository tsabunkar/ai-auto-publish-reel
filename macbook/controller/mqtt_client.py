import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

from awscrt import io
from awscrt.mqtt import Connection, QoS
from awsiot import mqtt_connection_builder

from macbook.shared.config import MacBookConfig
from macbook.shared.constants import (
    MQTT_KEEPALIVE_SECS,
    MQTT_PING_TIMEOUT_MS,
    MQTT_RECONNECT_MAX_SECS,
    MQTT_RECONNECT_MIN_SECS,
)
from macbook.shared.exceptions import MQTTConnectionError
from macbook.shared.logger import get_logger

logger = get_logger("mqtt_client")

MessageCallback = Callable[[dict[str, Any]], Awaitable[None]]


class MQTTClient:
    def __init__(self, config: MacBookConfig) -> None:
        self._config = config
        self._connection: Connection | None = None
        self._subscriptions: dict[str, MessageCallback] = {}
        self._connected = asyncio.Event()

    def _on_connection_interrupted(self, _connection: object, error: Exception, **_kwargs: object) -> None:
        logger.warning("MQTT connection interrupted", extra={"error": str(error)})
        self._connected.clear()

    def _on_connection_resumed(
        self, _connection: object, _return_code: object, session_present: bool, **_kwargs: object
    ) -> None:
        logger.info(
            "MQTT connection resumed",
            extra={"session_present": session_present},
        )
        self._connected.set()

    async def connect(self) -> None:
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(None, self._connect_sync)
        await future

    def _connect_sync(self) -> None:
        event_loop_group = io.EventLoopGroup(1)
        host_resolver = io.DefaultHostResolver(event_loop_group)
        client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

        self._connection = mqtt_connection_builder.websockets_with_default_aws_signing(
            region=self._config.aws_region,
            client_bootstrap=client_bootstrap,
            client_id="macbook-control-plane",
            clean_session=False,
            keep_alive_secs=MQTT_KEEPALIVE_SECS,
            ping_timeout_ms=MQTT_PING_TIMEOUT_MS,
            reconnect_min_timeout_secs=MQTT_RECONNECT_MIN_SECS,
            reconnect_max_timeout_secs=MQTT_RECONNECT_MAX_SECS,
            on_connection_interrupted=self._on_connection_interrupted,
            on_connection_resumed=self._on_connection_resumed,
            endpoint=self._config.iot_endpoint,
        )

        connect_future = self._connection.connect()
        connect_future.result()
        self._connected.set()
        logger.info(
            "MQTT connected",
            extra={"endpoint": self._config.iot_endpoint},
        )

    async def subscribe(
        self, topic: str, callback: MessageCallback
    ) -> None:
        self._subscriptions[topic] = callback
        loop = asyncio.get_event_loop()

        def _subscribe_sync() -> None:
            if self._connection is None:
                raise MQTTConnectionError("Not connected")
            sub_future = self._connection.subscribe(
                topic=topic,
                qos=QoS.AT_LEAST_ONCE,
                callback=lambda payload: self._on_message(topic, payload),
            )
            sub_future.result()

        await loop.run_in_executor(None, _subscribe_sync)
        logger.info("MQTT subscribed", extra={"topic": topic})

    def _on_message(self, topic: str, payload: bytes) -> None:
        try:
            data = json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError as exc:
            logger.error("MQTT message parse failed", extra={"error": str(exc)})
            return

        callback = self._subscriptions.get(topic)
        if callback is None:
            logger.warning("No handler for topic", extra={"topic": topic})
            return

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(callback(data))
        except Exception as exc:
            logger.exception(
                "MQTT callback failed",
                extra={"topic": topic, "error": str(exc)},
            )
        finally:
            loop.close()

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        await self._connected.wait()
        loop = asyncio.get_event_loop()

        def _publish_sync() -> None:
            if self._connection is None:
                raise MQTTConnectionError("Not connected")
            self._connection.publish(
                topic=topic,
                payload=json.dumps(payload, default=str).encode("utf-8"),
                qos=QoS.AT_LEAST_ONCE,
            )

        await loop.run_in_executor(None, _publish_sync)
        logger.debug("MQTT published", extra={"topic": topic})

    async def disconnect(self) -> None:
        if self._connection is not None:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._connection.disconnect)
            logger.info("MQTT disconnected")
