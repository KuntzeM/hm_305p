# hm305p
Thanks [markrages](https://github.com/markrages/py_test_interface) and [JackDoan](https://github.com/JackDoan/py_test_interface)!

Modified by me to record measurements in a loop and write into a csv.

## dependencies 
`pip install -r requirements.txt`

- pyserial: read measurements
- pandas, numpy, matplotlib: future features (plot measurements)

## usage
usage: measure_hm305.py [-h] --port PORT [--voltage VOLTAGE] [--current CURRENT] [--csv CSV] [--debug]

optional arguments:
  -h, --help         show this help message and exit
  
  --port PORT        serial port
  
  --voltage VOLTAGE  set voltage
  
  --current CURRENT  set current
  
  --csv CSV          path to csv, if set write measurements to csv
  
  --debug            enable verbose logging


## additional
[measure_hm305.py](measure_hm305.py) controls the HM305P power supply from Hanmatek (and others).  These supplies are USB controllable, but they just show as an CH341 serial port.  The protocol is described by http://nightflyerfireworks.com/home/fun-with-cheap-programable-power-supplies
