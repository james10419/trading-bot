import sys
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import threading
import pythoncom
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QObject, pyqtSignal

# --- FastAPI App Definition ---
app = FastAPI(title="Kiwoom REST Bridge")

class OrderRequest(BaseModel):
    rq_name: str
    screen_no: str
    acc_no: str
    order_type: int # 1: Buy, 2: Sell
    code: str
    qty: int
    price: int
    hoga: str # "00": Limit, "03": Market

class ConditionRequest(BaseModel):
    screen_no: str
    condition_name: str
    index: int

# Global Kiwoom Instance
kiwoom = None

# --- Kiwoom Controller Class ---
class KiwoomController(QAxWidget):
    def __init__(self):
        super().__init__()
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")
        self._set_event_handlers()
        
        # State
        self.msg_queue = []
        self.condition_list = {}
        self.tr_data = {}
        
    def _set_event_handlers(self):
        self.OnEventConnect.connect(self._on_event_connect)
        self.OnReceiveTrData.connect(self._on_receive_tr_data)
        self.OnReceiveConditionVer.connect(self._on_receive_condition_ver)
        self.OnReceiveTrCondition.connect(self._on_receive_tr_condition)
        self.OnReceiveRealCondition.connect(self._on_receive_real_condition)
        self.OnReceiveMsg.connect(self._on_receive_msg)

    # --- Events ---
    def _on_event_connect(self, err_code):
        if err_code == 0:
            print("Successfully connected to Kiwoom")
            self.dynamicCall("GetConditionLoad()") # Load conditions
        else:
            print(f"Connection Failed: {err_code}")

    def _on_receive_msg(self, scr_no, rq_name, tr_code, msg):
        print(f"[MSG] {scr_no} | {rq_name} | {msg}")

    def _on_receive_tr_data(self, scr_no, rq_name, tr_code, record_name, prev_next):
        # Handle specific TR responses if needed
        pass

    def _on_receive_condition_ver(self, ret, msg):
        if ret == 1:
            print("Condition List Loaded")
            raw_conditions = self.dynamicCall("GetConditionNameList()")
            # Parse Format: "Index^Name;Index^Name;..."
            if raw_conditions:
                for chunk in raw_conditions.split(';'):
                    if not chunk: continue
                    idx, name = chunk.split('^')
                    self.condition_list[name] = int(idx)
            print(f"Loaded {len(self.condition_list)} conditions")

    def _on_receive_tr_condition(self, scr_no, code_list, condition_name, index, next_req):
        codes = code_list.split(';')[:-1]
        print(f"[CONDITION] {condition_name}: Found {len(codes)} stocks")
        self.tr_data['last_condition_result'] = codes

    def _on_receive_real_condition(self, code, type, condition_name, condition_index):
        # Real-time condition updates
        action = "INSERT" if type == "I" else "DELETE"
        print(f"[REALTIME] {condition_name} ({action}): {code}")

    # --- Actions ---
    def login(self):
        self.dynamicCall("CommConnect()")

    def send_order(self, req: OrderRequest):
        # SendOrder(RQName, ScreenNo, AccNo, OrderType, Code, Qty, Price, Hoga, OrgOrderNo)
        ret = self.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                               [req.rq_name, req.screen_no, req.acc_no, req.order_type, req.code, 
                                req.qty, req.price, req.hoga, ""])
        return ret

    def get_account_list(self):
        accounts = self.dynamicCall("GetLoginInfo(QString)", "ACCNO")
        if accounts:
            return accounts.split(';')[:-1]
        return []

    def start_condition(self, req: ConditionRequest):
        # SendCondition(ScreenNo, ConditionName, Index, SearchType)
        # SearchType: 0 (General), 1 (Real-time)
        ret = self.dynamicCall("SendCondition(QString, QString, int, int)",
                               req.screen_no, req.condition_name, req.index, 0)
        return ret

# --- Wrapper for Thread Safety ---
# FastAPI runs in threads, but QAxWidget must run in the Main Thread (Qt Loop).
# We can't easily bridge them in a simple script without complex worker signals.
# For simplicity in this "Prototype", we will assume this script is running in 
# a proper generic setup or we accept some blocking limit. 
# A better production approach for FastAPI + PyQt is using QThread or 
# just running FastAPI via uvicorn in a separate thread while main thread holds QApplication.

# For this execution, we will start FastAPI in a daemon thread.

def start_api():
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="info")
    server = uvicorn.Server(config)
    server.run()

@app.get("/status")
def get_status():
    return {"status": "running", "connected": kiwoom is not None}

@app.get("/accounts")
def get_accounts():
    if not kiwoom: raise HTTPException(503, "Kiwoom logic not ready") # Basic check
    # Note: Cross-thread COM calls are tricky. In Python 32-bit OCX, 
    # simple reading might fail if not properly marshaled.
    # We will attempt a direct call for now.
    return kiwoom.get_account_list()

@app.post("/order")
def place_order(req: OrderRequest):
    if not kiwoom: raise HTTPException(503, "Kiwoom logic not ready")
    ret = kiwoom.send_order(req)
    if ret == 0:
        return {"status": "success", "message": "Order Sent"}
    else:
        return {"status": "error", "code": ret}

@app.post("/condition")
def run_condition(req: ConditionRequest):
    if not kiwoom: raise HTTPException(503, "Kiwoom logic not ready")
    
    # Check if index matches name
    real_idx = kiwoom.condition_list.get(req.condition_name)
    if real_idx is None:
         raise HTTPException(404, "Condition Name not found")
         
    ret = kiwoom.start_condition(req)
    if ret == 1:
        return {"status": "success", "message": "Condition Search Started"}
    else:
         return {"status": "error", "code": ret}

@app.get("/condition_list")
def get_condition_list():
    if not kiwoom: return {}
    return kiwoom.condition_list

if __name__ == "__main__":
    # 1. Initialize Qt App
    qapp = QApplication(sys.argv)
    
    # 2. Update Global Instance
    kiwoom = KiwoomController()
    kiwoom.login()

    # 3. Start FastAPI in separate thread
    # NOTE: This is Experimental. Managing Loop + Qt + COM often produces 'CoInitialize' errors.
    # The 'proper' way is a dedicated process or very careful threading. 
    # We will try the thread approach for simplicity.
    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()

    # 4. Run Qt Main Loop
    sys.exit(qapp.exec_())
