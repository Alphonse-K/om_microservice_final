from src.core.config import settings
import random


class SIMManager:
    def __init__(self):
        self.sims = settings.MOBILE_MONEY_SIMS
        self.config = getattr(settings, 'SIM_CONFIG', {})
        self.failed_sims = set()
        self.current_index = 0  # 0 or 1 for 2 SIMs

    def get_available_sims(self):
        """Get SIMs that haven't failed"""
        return {name: port for name, port in self.sims.items() 
                if name not in self.failed_sims}

    def get_sim_round_robin(self):
        """Simple toggle between 2 SIMs"""
        available_sims = list(self.get_available_sims().items())
        
        if not available_sims:
            self.failed_sims.clear()
            available_sims = list(self.sims.items())
        
        # Simple toggle: 0→1, 1→0
        position = self.current_index % len(available_sims)
        sim_name, port_index = available_sims[position]
        
        # Toggle for next call
        self.current_index = 1 - self.current_index
        
        print(f"🔄 Round-robin: Using {sim_name} on port {port_index}")
        return sim_name, port_index

    def get_sim_random(self):
        """Random SIM selection"""
        available_sims = list(self.get_available_sims().items())
        
        if not available_sims:
            self.failed_sims.clear()
            available_sims = list(self.sims.items())
        
        sim_name, port_index = random.choice(available_sims)
        print(f"🎲 Random: Using {sim_name} on port {port_index}")
        return sim_name, port_index

    def get_sim_primary(self):
        """Use primary SIM, fallback to secondary"""
        primary = self.config.get('primary_sim', 'orange_money_1')
        secondary = self.config.get('secondary_sim', 'orange_money_2')
        
        available_sims = self.get_available_sims()
        
        if primary in available_sims:
            return primary, available_sims[primary]
        elif secondary in available_sims:
            return secondary, available_sims[secondary]
        else:
            # Fallback to any available
            available = list(available_sims.items())
            if available:
                return random.choice(available)
            else:
                self.failed_sims.clear()
                return primary, self.sims[primary]

    def mark_sim_failed(self, sim_name):
        """Mark SIM as failed"""
        self.failed_sims.add(sim_name)
        print(f"🚫 Marked {sim_name} as failed")

    def mark_sim_recovered(self, sim_name):
        """Mark SIM as recovered"""
        if sim_name in self.failed_sims:
            self.failed_sims.remove(sim_name)
            print(f"✅ Marked {sim_name} as recovered")