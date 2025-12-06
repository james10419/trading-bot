import requests
import logging

class KiwoomClient:
    """
    Client for the local Kiwoom REST Bridge.
    Communicates via HTTP to 'kiwoom_bridge.py'.
    """
    def __init__(self, host="127.0.0.1", port=8000):
        self.base_url = f"http://{host}:{port}"
        
    def get_status(self):
        try:
            resp = requests.get(f"{self.base_url}/status", timeout=2)
            return resp.json().get('status') == 'running'
        except:
            return False

    def get_accounts(self):
        try:
            resp = requests.get(f"{self.base_url}/accounts", timeout=5)
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            logging.error(f"Kiwoom Client Error (get_accounts): {e}")
            return []
            
    def get_conditions(self):
        try:
            resp = requests.get(f"{self.base_url}/condition_list", timeout=5)
            if resp.status_code == 200:
                return resp.json()
            return {}
        except Exception as e:
             logging.error(f"Kiwoom Client Error (get_conditions): {e}")
             return {}

    def start_condition(self, screen_no, condition_name, index):
        """
        Triggers a conditional search on the bridge.
        """
        payload = {
            "screen_no": screen_no,
            "condition_name": condition_name,
            "index": index
        }
        try:
            resp = requests.post(f"{self.base_url}/condition", json=payload, timeout=5)
            return resp.json()
        except Exception as e:
            logging.error(f"Kiwoom Client Error (start_condition): {e}")
            return {'status': 'error', 'msg': str(e)}

    def send_order(self, rq_name, screen_no, acc_no, order_type, code, qty, price, hoga="00"):
        """
        Sends an order.
        order_type: 1 (Buy), 2 (Sell)
        hoga: "00" (Limit), "03" (Market)
        """
        payload = {
            "rq_name": rq_name,
            "screen_no": screen_no,
            "acc_no": acc_no,
            "order_type": order_type,
            "code": code,
            "qty": qty,
            "price": price,
            "hoga": hoga
        }
        try:
            resp = requests.post(f"{self.base_url}/order", json=payload, timeout=5)
            return resp.json()
        except Exception as e:
             logging.error(f"Kiwoom Client Error (send_order): {e}")
             return {'status': 'error', 'msg': str(e)}
