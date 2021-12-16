<div id="top"></div>

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![GPL3 License][license-shield]][license-url]

<br />
<div align="center">

<h2 align="center">SunGather</h3>

  <p align="center">
    Collect data from Sungrow Inverters using ModbusTcpClient, <a href="https://github.com/rpvelloso/Sungrow-Modbus">SungrowModbusTcpClient</a> or <a href="https://github.com/bohdan-s/SungrowModbusWebClient">SungrowModbusWebClient</a> and export to various locations.
    <br />
    <br />
    <a href="https://github.com/bohdan-s/SunGather/issues">Report Bug</a>
    ·
    <a href="https://github.com/bohdan-s/SunGather/issues">Request Feature</a>
  </p>
</div>

<!-- ABOUT THE PROJECT -->
## About The Project
Access ModBus data from almost any network connected Sungow Inverter.

On first connection the tool will query your inverter, retreive the model and return the correct registers for your device. No more searching registers or creating model files.

Register information based on official documentation: <a href="https://github.com/bohdan-s/Sungrow-Inverter/blob/main/Modbus%20Information/Communication%20Protocol%20of%20PV%20Grid-Connected%20String%20Inverters_V1.1.37_EN.pdf">Communication Protocol of PV Grid-Connected String Inverters</a>

Has muliple export locations out of the box:
* Console - Log directly to screen
* MQQT - Load into MQTT, and optionally Home Assistance Discovery
* PVOutput - Load into PVOutput.org
* and more coming....

I have borrowed HEAVILY from the following projects, THANK YOU
* [solariot](https://github.com/meltaxa/solariot)
* [modbus4mqtt](https://github.com/tjhowse/modbus4mqtt)
* [ModbusTCP2MQTT](https://github.com/TenySmart/ModbusTCP2MQTT)

<p align="right">(<a href="#top">back to top</a>)</p>

### TO BO
* Commandline Arguments
* Docker
* Better Home Assistant Support


### Built With

* [Python3](https://www.python.org/)

### Requires
* [paho-mqtt>=1.5.1](https://pypi.org/project/paho-mqtt/)
* [pymodbus>=2.4.0](https://pypi.org/project/pymodbus/)
* [SungrowModbusTcpClient>=0.1.6](https://pypi.org/project/SungrowModbusTcpClient/)
* [SungrowModbusWebClient>=0.2.4](https://pypi.org/project/SungrowModbusWebClient/)

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- GETTING STARTED -->
## Getting Started
```sh
git clone https://github.com/bohdan-s/SunGather.git
```
Copy config-example.py to config.py, change values as required (see comments in file)
```sh
python3 sungather.py
```

<p align="right">(<a href="#top">back to top</a>)</p>



<!-- USAGE EXAMPLES -->
## Usage

See config-exmaple.py it contains default options and comments.

If you want to use the new Energy section in Home Assistant, add the following sensors to convert from Power to Energy:
```
sensor:
  - platform: integration
    source: sensor.inverter_active_power
  - platform: integration
    source: sensor.inverter_export_to_grid
  - platform: integration
    source: sensor.inverter_import_from_grid
```

<p align="right">(<a href="#top">back to top</a>)</p>


## Tested
* SG7.0RT with WiNet-S Dongle

<p align="right">(<a href="#top">back to top</a>)</p>


<!-- LICENSE -->
## License

Distributed under the GPL3 License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#top">back to top</a>)</p>


<!-- CONTACT -->
## Contact

Project Link: [https://github.com/bohdan-s/SungrowModbusWebClient](https://github.com/bohdan-s/SungrowModbusWebClient)

<p align="right">(<a href="#top">back to top</a>)</p>


<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

* [solariot](https://github.com/meltaxa/solariot)
* [modbus4mqtt](https://github.com/tjhowse/modbus4mqtt)
* [ModbusTCP2MQTT](https://github.com/TenySmart/ModbusTCP2MQTT)

<p align="right">(<a href="#top">back to top</a>)</p>



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/bohdan-s/SunGather.svg?style=for-the-badge
[contributors-url]: https://github.com/bohdan-s/SunGather/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/bohdan-s/SunGather.svg?style=for-the-badge
[forks-url]: https://github.com/bohdan-s/SunGather/network/members
[stars-shield]: https://img.shields.io/github/stars/bohdan-s/SunGather.svg?style=for-the-badge
[stars-url]: https://github.com/bohdan-s/SunGather/stargazers
[issues-shield]: https://img.shields.io/github/issues/bohdan-s/SunGather.svg?style=for-the-badge
[issues-url]: https://github.com/bohdan-s/SunGather/issues
[license-shield]: https://img.shields.io/github/license/bohdan-s/SunGather.svg?style=for-the-badge
[license-url]: https://github.com/bohdan-s/SunGather/blob/main/LICENSE.txt