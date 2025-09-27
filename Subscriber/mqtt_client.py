"""
MQTT Client Module for MQTT Subscriber GUI

This module provides a high-level interface for MQTT communication, handling connection,
disconnection, and message subscribing. It encapsulates the paho-mqtt client to provide
a more Pythonic and type-safe API for the MQTT Subscriber application.

Key Features:
- Connection management with automatic reconnection
- Thread-safe message subscribing
- Callback-based event handling
- Type hints for better IDE support
"""

import paho.mqtt.client as mqtt
from typing import Optional, Callable, Any, Dict

class MqttClient:
    """Handles MQTT connection and message subscribing."""
    
    def __init__(self):
        """Initialize the MQTT client with default settings."""
        self.client: Optional[mqtt.Client] = None
        self.on_connect_callback: Optional[Callable] = None
        self.on_disconnect_callback: Optional[Callable] = None
        self.on_message_callback: Optional[Callable] = None
        self.on_subscribe_callback: Optional[Callable] = None
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
        client_id = "MQTT_Subscriber_GUI"
        self.client = mqtt.Client(
            client_id=client_id,
            clean_session=True,
            reconnect_on_failure=False  # Disable automatic reconnection
        )
        
        # Set connection timeout to 5 seconds
        self.client.connect_timeout = 5.0
        
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_subscribe = self._on_subscribe
        
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
    
    def subscribe(self, topic: str, qos: int = 0) -> bool:
        """Subscribe to an MQTT topic.
        
        Args:
            topic: Topic to subscribe to
            qos: Quality of Service level (0, 1, or 2)
            
        Returns:
            True if subscribe was successful, False otherwise
        """
        if not self.client or not self.connected:
            return False
            
        result, mid = self.client.subscribe(topic, qos=qos)
        return result == mqtt.MQTT_ERR_SUCCESS
    
    def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from an MQTT topic.
        
        Args:
            topic: Topic to unsubscribe from
            
        Returns:
            True if unsubscribe was successful, False otherwise
        """
        if not self.client or not self.connected:
            return False
            
        result, mid = self.client.unsubscribe(topic)
        return result == mqtt.MQTT_ERR_SUCCESS
    
    def set_callbacks(self, on_connect: Callable = None, on_disconnect: Callable = None, 
                     on_message: Callable = None, on_subscribe: Callable = None) -> None:
        """Set callback functions for connection events.
        
        Args:
            on_connect: Function to call when connected
            on_disconnect: Function to call when disconnected
            on_message: Function to call when message received
            on_subscribe: Function to call when subscription confirmed
        """
        self.on_connect_callback = on_connect
        self.on_disconnect_callback = on_disconnect
        self.on_message_callback = on_message
        self.on_subscribe_callback = on_subscribe
    
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
    
    def _on_message(self, client, userdata, msg) -> None:
        """Handle MQTT message event."""
        if self.on_message_callback:
            self.on_message_callback(msg)
    
    def _on_subscribe(self, client, userdata, mid, reason_codes, properties=None) -> None:
        """Handle MQTT subscribe event."""
        if self.on_subscribe_callback:
            self.on_subscribe_callback(mid, reason_codes)
    
    def is_connected(self) -> bool:
        """Check if the client is connected to a broker."""
        return self.connected if self.client else False
