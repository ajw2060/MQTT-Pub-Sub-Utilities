"""
MQTT Client Module for MQTT Publisher GUI

This module provides a high-level interface for MQTT communication, handling connection,
disconnection, and message publishing. It encapsulates the paho-mqtt client to provide
a more Pythonic and type-safe API for the MQTT Publisher application.

Key Features:
- Connection management with automatic reconnection
- Thread-safe message publishing
- Callback-based event handling
- Type hints for better IDE support
"""

import paho.mqtt.client as mqtt
from typing import Optional, Callable, Any, Dict

class MqttClient:
    """Handles MQTT connection and message publishing."""
    
    def __init__(self):
        """Initialize the MQTT client with default settings."""
        self.client: Optional[mqtt.Client] = None
        self.on_connect_callback: Optional[Callable] = None
        self.on_disconnect_callback: Optional[Callable] = None
        self.connected = False
    
    def connect(self, broker: str, port: int, username: str = None, password: str = None) -> None:
        """Connect to an MQTT broker.
        
        Args:
            broker: Broker hostname or IP address
            port: Broker port number
            username: Optional username for authentication
            password: Optional password for authentication
            
        Raises:
            ValueError: If connection parameters are invalid
            ConnectionError: If connection to the broker fails
        """
        if not broker or not port:
            raise ValueError("Broker and port are required")
        
        # Set a fixed client ID for this app
        client_id = "MQTT_Publisher_GUI"
        self.client = mqtt.Client(
            client_id=client_id,
            clean_session=True,
            reconnect_on_failure=False  # Disable automatic reconnection
        )
        
        # Set connection timeout to 5 seconds
        self.client.connect_timeout = 5.0
        
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        
        if username:
            self.client.username_pw_set(username, password)
        
        try:
            # Connect with a timeout
            self.client.connect(broker, port, keepalive=60)
            # Start the network loop with a short timeout to avoid blocking
            self.client.loop_start()
            # Wait for connection result (up to connect_timeout seconds)
            self.client._connect_timeout = self.client.connect_timeout
            self.client._connect_event = True
        except Exception as e:
            self.connected = False
            # Provide more detailed error message
            error_msg = f"Failed to connect to MQTT broker at {broker}:{port}"
            if username:
                error_msg += f" with username '{username}'"
            error_msg += f". Please check your connection settings and try again.\n\nError details: {str(e)}"
            raise ConnectionError(error_msg)
    
    def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
    
    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False) -> bool:
        """Publish a message to an MQTT topic.
        
        Args:
            topic: Topic to publish to
            payload: Message payload
            qos: Quality of Service level (0, 1, or 2)
            retain: Whether the message should be retained
            
        Returns:
            True if publish was successful, False otherwise
        """
        if not self.client or not self.connected:
            return False
            
        result = self.client.publish(topic, payload, qos=qos, retain=retain)
        return result.rc == mqtt.MQTT_ERR_SUCCESS
    
    def set_callbacks(self, on_connect: Callable = None, on_disconnect: Callable = None) -> None:
        """Set callback functions for connection events.
        
        Args:
            on_connect: Function to call when connected
            on_disconnect: Function to call when disconnected
        """
        self.on_connect_callback = on_connect
        self.on_disconnect_callback = on_disconnect
    
    def _on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        """Handle MQTT connection event."""
        self.connected = reason_code == 0
        # Clear any existing reconnect flags
        client._connect_event = True
        if self.connected:
            client_id = client._client_id.decode() if isinstance(client._client_id, bytes) else client._client_id

        if self.on_connect_callback:
            self.on_connect_callback(reason_code)
    
    def _on_disconnect(self, client, userdata, disconnect_flags=None, reason_code=None, properties=None) -> None:
        """Handle MQTT disconnection event."""
        self.connected = False
        if self.on_disconnect_callback:
            self.on_disconnect_callback(reason_code)
    
    def is_connected(self) -> bool:
        """Check if the client is connected to a broker."""
        return self.connected if self.client else False
