# src/services/neogate_client.py
from urllib.parse import quote_plus
import requests
from src.core.config import settings
from .sim_manager import SIMManager
from datetime import datetime, timezone
from fastapi import HTTPException


class NeoGateTG400Client:
    def __init__(self):
        self.base_url = settings.NEOGATE_BASE_URL
        self.api_username = settings.NEOGATE_API_USERNAME
        self.api_password = settings.NEOGATE_API_PASSWORD
        self.sim_manager = SIMManager()
        self.orange_pin = settings.ORANGE_MONEY_PIN

    def send_ussd_request(self, gsm_port_index: int, ussd_code: str, sim_name: str = None) -> str:
        """Send USSD request via specified GSM port."""
        encoded_ussd = quote_plus(ussd_code)
        url = (
            f"{self.base_url}/cgi/WebCGI?"
            f"1500102=&"
            f"account={self.api_username}&"
            f"password={self.api_password}&"
            f"port={gsm_port_index}&"
            f"content={encoded_ussd}"
        )
        print(f"🚀 Sending USSD to port {gsm_port_index}: {ussd_code}")
        print(f"🔗 URL: {url}")
        try:
            response = requests.get(url, timeout=30)
            print(f"✅ Response: {response.text}")
            return response.text
        except requests.RequestException as e:
            print(f"❌ API Request failed: {e}")
            return None

    def send_deposit_with_confirmation(self, recipient_phone: str, amount: float) -> dict:
        """
        Send deposit with interactive confirmation flow via USSD.
        """
        sim_name, port_index = self.sim_manager.sims["orange_money_1"]
        print(f"💰 Initiating deposit of {amount} to {recipient_phone}")

        # Step 1: Initiate deposit (gets confirmation menu)
        deposit_code = f"*142*1*{amount}*{recipient_phone}*1*{self.orange_pin}#"
        step1_response = self.send_ussd_request(port_index, deposit_code)
        print(f"📋 Step 1 Response: {step1_response}")

        # Check for confirmation menu
        if step1_response and "Confirmer" in step1_response and "1.Confirmer" in step1_response:
            print("✅ Got confirmation menu, proceeding to confirm...")

            # Step 2: Confirm transaction
            confirmation_code = "1"  # Select "1.Confirmer"
            step2_response = self.send_ussd_request(port_index, confirmation_code)
            print(f"✅ Step 2 Response: {step2_response}")

            # Step 3: Check if PIN required after confirmation
            if step2_response and ("code secret" in step2_response.lower() or "pin" in step2_response.lower()):
                print("🔐 PIN required, sending PIN...")
                step3_response = self.send_ussd_request(port_index, self.orange_pin)
                print(f"✅ Step 3 Response: {step3_response}")

                return {
                    'status': 'completed',
                    'sim_used': sim_name,
                    'step1_response': step1_response,
                    'step2_response': step2_response,
                    'step3_response': step3_response,
                    'final_status': 'success' if step3_response and "success" in step3_response.lower() else 'pending'
                }

            return {
                'status': 'completed',
                'sim_used': sim_name,
                'step1_response': step1_response,
                'step2_response': step2_response,
                'final_status': 'success' if step2_response and "success" in step2_response.lower() else 'pending'
            }

        # Step 1 failed: no confirmation menu received
        return {
            'status': 'failed',
            'sim_used': sim_name,
            'response': step1_response,
            'reason': 'No confirmation menu received'
        }
    

    def purchase_credit(self, recipient_phone: str, amount: float):
        """
        Purchase airtime/credit using USSD:
        *142*4*<phone>*<amount>*<PIN>#
        """
        orange_pin = self.orange_pin
        sim_name, port_index = self.sim_manager.sims["orange_money_2"]

        # Build USSD request
        ussd_code = f"*142*4*{recipient_phone}*{amount}*{orange_pin}#"

        print(f"📱 Purchasing {amount} credit for {recipient_phone}")
        print(f"🔗 USSD Code: {ussd_code}")

        # Send to NeoGate
        response = self.send_ussd_request(port_index, ussd_code)

        if response is None:
            raise HTTPException(status_code=500, detail="No response from NeoGate device")


        return {
            "sim_used": sim_name,
            "ussd_code": ussd_code,
            "response": response,
            "amount": amount,
            "recipient": recipient_phone,
            "timestamp": datetime.now(timezone.utc).isoformat()        
        }
    
    def withdraw_cash(self, agent_number: str, amount: float):
        """
        Initiate withdrawal and return immediately - don't wait for confirmation.
        Compatible with FastAPI + async SQLAlchemy.
        """
        orange_pin = self.orange_pin
        sim_name, port_index = self.sim_manager.sims["orange_money_1"]

        amount_str = str(amount)
        agent_number_str = str(agent_number)

        ussd_code = f"*142*2*1*{amount_str}*{agent_number_str}*1*{orange_pin}#"

        print(f"💰 Withdrawing {amount_str} from agent {agent_number_str}")
        print(f"🔗 USSD Code: {ussd_code}")

        # Send USSD request
        response = self.send_ussd_request(port_index, ussd_code)


        return {
            "status": "processing",
            "message": "Withdrawal initiated. Checking confirmation in background.",
            "sim_used": sim_name,
            "initial_response": response
        }

