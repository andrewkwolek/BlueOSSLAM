# BlueOSSLAM

A Simultaneous Localization and Mapping (SLAM) implementation for BlueROV2 underwater vehicles using the Ping360 sonar.

## Overview

BlueOSSLAM is an extension for the BlueOS ecosystem that provides sonar-based SLAM capabilities for underwater vehicles. It processes data from the Ping360 mechanical scanning sonar to create visual representations of the underwater environment and extract features for mapping and navigation.

## Features

- **Real-time Sonar Visualization**: View sonar data in both rectangular and polar coordinate formats
- **CFAR Feature Extraction**: Uses Constant False Alarm Rate (CFAR) algorithms to detect features in sonar data
- **Point Cloud Generation**: Creates point clouds from extracted sonar features
- **Data Recording**: Save sonar scans for offline processing and analysis
- **Adjustable Parameters**: Fine-tune CFAR parameters via the web interface
- **BlueOS Integration**: Runs as a containerized extension within the BlueOS ecosystem

## Installation

### Requirements

- BlueOS compatible ROV (such as BlueROV2)
- Ping360 mechanical scanning sonar
- BlueOS installation

### Installation via BlueOS

1. Open BlueOS web interface
2. Navigate to the Extensions tab
3. Click "Install Extension"
4. Enter `andrewkwolek3/blueos-blueos-slam:main` as the extension name
5. Click "Install"

### Manual Installation

To build and run the container locally:

```bash
docker build -t blueos-slam .
docker run -p 9050:9050 -p 14555:14555/udp -p 9092:9092/udp --name blueos-slam blueos-slam
```

## Usage

After installation, access the web interface at:

```
http://<vehicle-ip>:9050
```

### Web Interface

The web interface provides:

- Sonar strength spectrum visualization
- CFAR processed data visualization
- Sonar point cloud visualization
- Polar view of the sonar scan
- Controls for adjusting CFAR parameters
- Recording controls for saving sonar data

### CFAR Parameter Adjustment

You can adjust the following parameters:

- **Ntc (Training Cells)**: Number of cells used for background estimation
- **Ngc (Guard Cells)**: Number of cells between the cell under test and training cells
- **Pfa (False Alarm Rate)**: Probability of false alarm threshold
- **Strength Threshold**: Minimum signal strength to be considered a detection

### Data Recording

Click the "Start Recording" button to begin recording sonar data. Data is saved in HDF5 format in the `/app/sonar_data` directory inside the container.

## Configuration

Configuration settings can be found in `app/src/settings.py`. Key settings include:

- **LIVE_SONAR**: Whether to use live sonar data or replay recorded data
- **UDP_PORT**: UDP port for communication with the Ping360
- **SONAR_FILE**: Path to recorded sonar data for replay mode
- **WATER_SOS**: Speed of sound in water (m/s)

## Development

### Project Structure

- **app/src/ping/**: Sonar data processing and feature extraction
- **app/src/mavlink/**: Vehicle data management via MAVLink
- **app/src/video/**: Video processing for visual odometry
- **app/src/static/**: Web interface files
- **app/src/main.py**: Main application entry point

### Building from Source

1. Clone this repository:
```bash
git clone https://github.com/andrewkwolek/BlueOSSLAM.git
cd BlueOSSLAM
```

2. Build the Docker image:
```bash
docker build -t blueos-slam .
```

3. Run the container:
```bash
docker run -p 9050:9050 -p 14555:14555/udp -p 9092:9092/udp --name blueos-slam blueos-slam
```

## Technical Details

### Sonar Processing

BlueOSSLAM uses several CFAR algorithms for feature extraction:
- Cell Averaging (CA) CFAR
- Greatest-of Cell-Averaging (GOCA) CFAR
- Smallest-of Cell-Averaging (SOCA) CFAR
- Order Statistic (OS) CFAR

### Web API

The application provides several REST API endpoints:

- **GET /v1.0/sonar_scan**: Get the current sonar scan visualization
- **GET /v1.0/cfar_scan**: Get the CFAR-processed scan visualization
- **GET /v1.0/costmap**: Get the point cloud visualization
- **GET /v1.0/polar_scan**: Get the polar view visualization
- **POST /v1.0/record_ping**: Toggle sonar recording
- **POST /v1.0/update_cfar_params**: Update CFAR parameters

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgements

- BlueRobotics for the BlueOS platform
- BlueRobotics for the Ping360 sonar and Python libraries