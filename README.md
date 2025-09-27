# MQTT Publisher & Subscriber GUI Applications

A pair of professional MQTT client applications built with Python and Tkinter, designed to work seamlessly together for MQTT message publishing and subscribing operations.

## 📋 Overview

This repository contains two complementary MQTT GUI applications:

- **MQTT Publisher** - A feature-rich message publishing tool with template support
- **MQTT Subscriber** - A clean and efficient message subscription client

Both applications share a consistent design language and user experience, making them feel like parts of a unified MQTT toolkit.

## 🚀 Features

### MQTT Publisher (v1.4.16)
- **Template System**: Pre-built payload templates for common IoT scenarios
- **Dynamic Templates**: Support for variable substitution in templates
- **Payload Preview**: Real-time preview of formatted JSON messages
- **Connection Management**: Persistent broker settings and connection status
- **Message History**: Topic history with auto-completion
- **QoS Support**: Full Quality of Service level support (0, 1, 2)
- **Automatic Saving**: All settings saved automatically on exit

### MQTT Subscriber (v1.0.7)
- **Topic Subscription**: Subscribe to multiple MQTT topics simultaneously
- **Real-time Messages**: Live display of incoming messages with timestamps
- **Message Parsing**: Automatic JSON formatting for better readability
- **Connection Management**: Robust connection handling with status indicators
- **Topic History**: Persistent topic history across sessions
- **QoS Support**: Full Quality of Service level support (0, 1, 2)
- **Automatic Saving**: All settings saved automatically on exit

## 🛠️ Installation

### Prerequisites
- Python 3.7 or higher
- Required Python packages (install via pip)

### Setup
1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/mqtt-gui-apps.git
   cd mqtt-gui-apps
   ```

2. Install required dependencies:
   ```bash
   pip install paho-mqtt pyyaml
   ```

## 🎯 Usage

### Running the Applications

**MQTT Publisher:**
```bash
cd Publisher
python mqtt_publisher_gui.py
```

**MQTT Subscriber:**
```bash
cd Subscriber
python mqtt_subscriber_gui.py
```

### Getting Started

1. **Configure MQTT Broker**: Enter your broker details (host, port, credentials)
2. **Connect**: Click the "Connect" button to establish MQTT connection
3. **Publish/Subscribe**: Use the respective applications for your MQTT operations

## 📁 Project Structure

```
mqtt-gui-apps/
├── Publisher/
│   ├── mqtt_publisher_gui.py      # Main publisher application
│   ├── mqtt_client.py             # MQTT client wrapper
│   ├── config_manager.py          # Configuration management
│   ├── template_manager.py        # Template system
│   ├── mqtt_publisher_config.json # Publisher settings
│   └── payload_templates/         # Template files
│       ├── dynamic_light_control.yaml
│       ├── light_control.yaml
│       ├── smart_home_control.yaml
│       └── ...
├── Subscriber/
│   ├── mqtt_subscriber_gui.py     # Main subscriber application
│   ├── mqtt_client.py             # MQTT client wrapper
│   ├── config_manager.py          # Configuration management
│   └── mqtt_subscriber_config.json # Subscriber settings
└── README.md                      # This file
```

## 🔧 Configuration

Both applications automatically save your settings including:
- MQTT broker connection details
- Window position and size
- Topic/message history
- All configuration preferences

Settings are stored in JSON files and loaded automatically on startup.  The configuration files do not exist in the repository but they will be created the first time the application is run.  By defauly these configuration files will be created in the directory from which the program runs.

## 📝 Template System (Publisher)

The publisher includes a comprehensive template system:

- **Pre-built Templates**: Common IoT scenarios (lighting, sensors, smart home)
- **Dynamic Variables**: Templates with placeholder substitution
- **JSON Formatting**: Automatic payload formatting and validation
- **Custom Templates**: Create your own YAML-based templates

## 🎨 User Interface

Both applications feature:
- **Consistent Design**: Unified look and feel across both apps
- **Professional Styling**: Clean, modern interface with proper theming
- **Responsive Layout**: Adaptive UI that works on different screen sizes
- **Keyboard Shortcuts**: F1 for help, Enter for quick actions
- **Status Indicators**: Real-time connection and operation status

## 🔒 Security Features

- **Credential Management**: Secure storage of broker credentials
- **Connection Validation**: Proper error handling and validation
- **Input Sanitization**: Protection against malformed inputs

## 🐛 Troubleshooting

### Common Issues

1. **Connection Failed**: Verify broker address, port, and credentials
2. **Import Errors**: Ensure all required packages are installed
3. **Permission Issues**: Check file permissions for configuration files

### Getting Help

- Press F1 in either application for built-in help
- Check the status log for detailed error messages
- Verify your MQTT broker is accessible and properly configured

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## 📄 License

This project is open source. Please check the license file for details.

## 🔄 Version History

- **Publisher v1.4.16**: Latest stable release with template system and enhanced UI
- **Subscriber v1.0.7**: Initial stable release with full feature parity

## 📞 Support

For issues, questions, or contributions, please use the GitHub issue tracker.

---

**Note**: These applications are designed to work with any standard MQTT broker (Mosquitto, HiveMQ, AWS IoT, etc.) and support MQTT 3.1.1 protocol.
