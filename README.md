# wifi-pineapple-berserker
Automate your Wifi Pineapple Mk. 7 Workflow!
Author: salt-or-ester
Source: https://gitgud.io/saltorester/wifi-pineapple-berserker/

```                                                                                                      
___.                                          __                    ._.._.._.
\_ |__    ____ _______  ______  ____ _______ |  | __  ____ _______  | || || |
 | __ \ _/ __ \\_  __ \/  ___/_/ __ \\_  __ \|  |/ /_/ __ \\_  __ \ | || || |
 | \_\ \\  ___/ |  | \/\___ \ \  ___/ |  | \/|    < \  ___/ |  | \/  \| \| \|
 |___  / \___  >|__|  /____  > \___  >|__|   |__|_ \ \___  >|__|     __ __ __
     \/      \/            \/      \/             \/     \/          \/ \/ \/
   
                                                                               
 ```                                                                                                                                                                                                                                       

This simple python script is an aggressive war-driver for the [Hak Wifi Pineapple Mark VII](https://shop.hak5.org/products/wifi-pineapple) to fully automate your recon, 
de-authing and handshake capturing.  Turn this thing on, take your Pineapple for a walk around town, and collect those handshakes without any effort.

Requirements:
```
python3
- requests library
```

Install:
```
pip install -r requirements.txt
```

Use:
```
Run on your local machine, not the Wifi Pineapple (better performance)
- edit berserker.py
- Modify "config" to match the server, port, username, password for your Wifi Pineapple. 
- python3 berserker.py
```

Workflow:
```
This is the workflow the script performs:
- set pineAP settings to AGGRESSIVE, broadcasting, allowing connections, auto-restart, etc
- run recon for 90 seconds, identify all APs with associated clients
- start handshake capture
- de-auth all clients related to AP, repeat 20 seconds later; total 2 mins
- handshakes captured, available for use
- repeat: move to next AP with associated clients, de-auth, etc.
```

Captures
```
The script output will tell you when a capture is collected, but many like to run this over an extended time (ie: overnight), so just take a look in your handshake directory and you'll see everything that was collected.  By default it's in /root/handshakes on the Wifi Pineapple device.
```