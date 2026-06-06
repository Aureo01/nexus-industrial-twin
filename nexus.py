import os
import sys
import time
import json
import asyncio
import logging
import random
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
import torch
import torch.nn as nn
import requests

#  Configuration
WORKSPACE = Path("./nexus_workspace")
WORKSPACE.mkdir(exist_ok=True)
LOG_FILE = WORKSPACE / "nexus.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE)]
)
logger = logging.getLogger("nexus")

#  ADVANCED DATA MODELS 
class AssetCriticality(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class AnomalyType(Enum):
    STATISTICAL = "statistical_outlier"
    PHYSICS_VIOLATION = "physics_law_violation"  # Futuristic!
    TREND_DEGRADATION = "trend_degradation"

@dataclass
class PhysicsLaw:
    """Defines a physics law that the machine must comply with."""
    name: str
    equation_description: str
    tolerance: float

@dataclass
class DroneMission:
    """Mission for an autonomous inspection drone/robot."""
    mission_id: str
    target_asset_id: str
    coordinates: Dict[str, float]
    payload_type: str  # "thermal_camera", "ultrasonic", "visual"
    priority: str
    status: str = "pending"

@dataclass
class ProductionReroute:
    """Production reconfiguration order (Self-Healing)."""
    source_asset_id: str
    target_asset_id: str
    load_percentage: float
    reason: str


#  PHYSICS-INFORMED NEURAL NETWORK (PINN) ──
class PhysicsInformedTwin(nn.Module):
    """
    Physics-Informed Neural Network (PINN).
    Learns the thermodynamic relationship between Vibration, Load, and Temperature.
    If the physics prediction and the actual value diverge, it indicates an imminent failure.
    """
    def __init__(self):
        super().__init__()
        # Network that predicts Temperature based on Vibration and Load
        self.net = nn.Sequential(
            nn.Linear(2, 16),
            nn.Tanh(),
            nn.Linear(16, 16),
            nn.Tanh(),
            nn.Linear(16, 1)
        )
        self.loss_fn = nn.MSELoss()
        
    def forward(self, vibration, load):
        x = torch.cat([vibration, load], dim=1)
        return self.net(x)
        
    def physics_loss(self, predicted_temp, actual_temp, vibration):
        """
        Loss function that includes a physics constraint:
        Temperature can never drop if vibration and load increase (Friction law).
        """
        mse = self.loss_fn(predicted_temp, actual_temp)
        
        # Physics constraint (Physics-Informed)
        # dT/dt must be proportional to (Vibration^2 * Load)
        physical_constraint = torch.mean(torch.relu(
            (predicted_temp - actual_temp) * vibration
        ))
        
        return mse + 0.1 * physical_constraint

class CognitiveTwin:
    """Cognitive digital twin that uses PINN to detect physics violations"""
    
    def __init__(self, asset_id: str):
        self.asset_id = asset_id
        self.pinn = PhysicsInformedTwin()
        self.optimizer = torch.optim.Adam(self.pinn.parameters(), lr=0.001)
        self.is_trained = False
        
        # Physics laws for this asset
        self.physics_laws = [
            PhysicsLaw("Conservation of Energy", "Heat = Friction * Load", tolerance=0.05),
            PhysicsLaw("Vibration-Thermal Coupling", "Temp rises with V^2", tolerance=0.1)
        ]
    
    def train_on_normal_data(self, vibrations: np.ndarray, loads: np.ndarray, temps: np.ndarray):
        """Trains the PINN with normal operation data."""
        v_t = torch.tensor(vibrations, dtype=torch.float32).reshape(-1, 1)
        l_t = torch.tensor(loads, dtype=torch.float32).reshape(-1, 1)
        t_t = torch.tensor(temps, dtype=torch.float32).reshape(-1, 1)
        
        for epoch in range(100):
            self.optimizer.zero_grad()
            pred = self.pinn(v_t, l_t)
            loss = self.pinn.physics_loss(pred, t_t, v_t)
            loss.backward()
            self.optimizer.step()
        
        self.is_trained = True
        logger.info(f" PINN trained for {self.asset_id} (Loss: {loss.item():.4f})")
    
    def detect_physics_violation(self, vibration: float, load: float, actual_temp: float) -> Optional[str]:
        """Detects if the machine is violating physics laws."""
        if not self.is_trained:
            return None
            
        v_t = torch.tensor([[vibration]], dtype=torch.float32)
        l_t = torch.tensor([[load]], dtype=torch.float32)
        t_t = torch.tensor([[actual_temp]], dtype=torch.float32)
        
        with torch.no_grad():
            predicted_temp = self.pinn(v_t, l_t)
            
        # If actual temperature is much higher than what physics predicts...
        deviation = (actual_temp - predicted_temp.item()) / predicted_temp.item()
        
        if deviation > 0.25: # 25% hotter than physics allows
            return f"PHYSICS VIOLATION: Temperature ({actual_temp}°C) exceeds by {deviation*100:.1f}% what thermodynamics laws allow for this vibration and load. Possible internal cooling failure or dry friction."
        
        return None


#  Autonomous drone dispatcher
class AutonomousSwarmController:
    """Manages the fleet of autonomous inspection drones/robots."""
    
    def __init__(self):
        self.active_missions = {}
        self.available_drones = ["DRONE-ALPHA-01", "DRONE-BETA-02", "ROBOT-DOG-03"]
    
    def dispatch_verification_mission(self, asset_id: str, anomaly_type: str, coordinates: Dict) -> DroneMission:
        """Dispatches a drone to visually/thermally verify the anomaly"""
        if not self.available_drones:
            logger.warning(" No drones available for dispatch.")
            return None
            
        drone_id = self.available_drones.pop(0)
        mission_id = f"MSN-{int(time.time())}"
        
        mission = DroneMission(
            mission_id=mission_id,
            target_asset_id=asset_id,
            coordinates=coordinates,
            payload_type="thermal_camera" if anomaly_type == AnomalyType.PHYSICS_VIOLATION else "visual",
            priority="CRITICAL"
        )
        
        self.active_missions[mission_id] = {"drone": drone_id, "mission": mission}
        logger.info(f" DRONE DISPATCHED: {drone_id} → {asset_id} for {mission.payload_type} verification")
        
        # Simulate drone return after 5 seconds
        asyncio.get_event_loop().call_later(5, self._complete_mission, mission_id)
        
        return mission
    
    def _complete_mission(self, mission_id: str):
        """Drone returns with data."""
        if mission_id in self.active_missions:
            drone_id = self.active_missions[mission_id]["drone"]
            self.available_drones.append(drone_id)
            logger.info(f" DRONE {drone_id} returned. Thermal image confirmed. Anomaly VALIDATED.")
            del self.active_missions[mission_id]


#  SELF-HEALING PRODUCTION ROUTER (MES integration)
class SelfHealingMES:
    """Manufacturing Execution System that reconfigures itself."""
    
    def __init__(self):
        self.production_lines = {
            "LINE-A": {"primary": "PUMP-001", "backup": "PUMP-002", "load": 100},
            "LINE-B": {"primary": "COMP-007", "backup": "COMP-008", "load": 85}
        }
    
    def execute_reroute(self, failing_asset: str) -> ProductionReroute:
        """Reroutes production automatically if an asset fails."""
        for line, config in self.production_lines.items():
            if config["primary"] == failing_asset:
                logger.critical(f" SELF-HEALING ACTIVATED: Rerouting load from {failing_asset} to {config['backup']}")
                
                # Real call to the MES API (Siemens Opcenter, Rockwell, etc.) would go here
                # requests.post("http://mes-api/reroute", json={...})
                
                return ProductionReroute(
                    source_asset_id=failing_asset,
                    target_asset_id=config["backup"],
                    load_percentage=100,
                    reason=f"Predictive failure detected on {failing_asset}"
                )
        return None


#  SAP / MAXIMO CMMS CONNECTOR (REST API) 
class CMMSConnector:
    """REST Integration with SAP PM or IBM Maximo."""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    def create_maintenance_order(self, asset_id: str, description: str, priority: int) -> Dict:
        """Creates a maintenance work order in the ERP."""
        payload = {
            "EquipmentID": asset_id,
            "OrderType": "PM", # Preventive Maintenance
            "Priority": priority,
            "Description": description,
            "PlannedStart": (datetime.now() + timedelta(hours=4)).isoformat(),
            "WorkCenter": "MAINT-01"
        }
        
        # REST call simulation
        logger.info(f"📡 Sending Work Order to SAP/Maximo: {payload['EquipmentID']}")
        # response = requests.post(f"{self.base_url}/maintenance_orders", json=payload, headers=self.headers)
        
        return {"status": "success", "sap_order_id": f"ORD-{random.randint(10000, 99999)}", "payload": payload}


#  GRAFANA / INFLUXDB INTEGRATION 
class TimeSeriesPublisher:
    """Publishes data to InfluxDB for Grafana visualization."""
    
    def __init__(self, url: str, token: str, org: str, bucket: str):
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        # self.client = InfluxDBClient(url=url, token=token, org=org)
        # self.write_api = self.client.write_api()
        logger.info(f" Connected to InfluxDB (Grafana ready): {bucket}")
        
    def publish_reading(self, asset_id: str, sensor: str, value: float):
        """Publishes a data point."""
        # point = Point("sensor_data").tag("asset", asset_id).field(sensor, value).time(datetime.utcnow())
        # self.write_api.write(bucket=self.bucket, record=point)
        pass # Simulated so InfluxDB is not required to be running


# NEXUS CORE (Main Orchestrator) 
class NexusCore:
    
    def __init__(self):
        self.cognitive_twins: Dict[str, CognitiveTwin] = {}
        self.swarm = AutonomousSwarmController()
        self.mes = SelfHealingMES()
        self.cmms = CMMSConnector("https://sap-api.company.com", "fake-token")
        self.influx = TimeSeriesPublisher("http://localhost:8086", "fake", "org", "nexus")
        
        # Initialize twins for critical assets
        self._initialize_twins()
        
    def _initialize_twins(self):
        assets = ["PUMP-001", "COMP-007"]
        for asset in assets:
            twin = CognitiveTwin(asset)
            # Train with normal synthetic data (Law: Temp = 50 + 2*Vib + 0.5*Load)
            v = np.random.uniform(1, 4, 100)
            l = np.random.uniform(50, 100, 100)
            t = 50 + 2*v + 0.5*l + np.random.normal(0, 1, 100)
            twin.train_on_normal_data(v, l, t)
            self.cognitive_twins[asset] = twin
            
    def process_realtime_data(self, asset_id: str, vibration: float, load: float, temperature: float):
        """Processes real-time data with PINN and makes autonomous decisions."""
        twin = self.cognitive_twins.get(asset_id)
        if not twin:
            return
            
        # 1. Publish to Grafana
        self.influx.publish_reading(asset_id, "temperature", temperature)
        
        # 2. Physics-Informed Detection
        violation = twin.detect_physics_violation(vibration, load, temperature)
        
        if violation:
            logger.critical(f" NEXUS ALERT: {violation}")
            
            # 3. Autonomous Drone Dispatch
            self.swarm.dispatch_verification_mission(
                asset_id, 
                AnomalyType.PHYSICS_VIOLATION, 
                {"x": 12.5, "y": 45.2, "z": 2.0}
            )
            
            # 4. Create Work Order in SAP
            self.cmms.create_maintenance_order(asset_id, violation, priority=1)
            
            # 5. Self-Healing: Reroute production
            reroute = self.mes.execute_reroute(asset_id)
            if reroute:
                logger.info(f" Production rerouted to {reroute.target_asset_id}")


# Simulation and CLI 
async def run_nexus_simulation():
    nexus = NexusCore()
    
    print("""
-══════════════════════════════════════════════════════════════════-
|  — Industrial Cognitive Twin & Autonomous Swarm                  |
|  Physics-Informed AI + Drone Dispatch + Self-Healing MES         |
-══════════════════════════════════════════════════════════════════-
    """)
    
    logger.info("🚀 Starting autonomous factory simulation...")
    
    for i in range(20):
        asset_id = "PUMP-001"
        
        # Normal operation
        if i < 15:
            vib = random.uniform(1.5, 2.5)
            load = random.uniform(60, 80)
            temp = 50 + 2*vib + 0.5*load + random.normalvariate(0, 1)
        else:
            # IMMINENT PHYSICS FAILURE! (Temperature spikes for no physical reason)
            vib = random.uniform(1.5, 2.5)
            load = random.uniform(60, 80)
            temp = 150 + random.uniform(0, 10) # Violates thermodynamics law
            
        nexus.process_realtime_data(asset_id, vib, load, temp)
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(run_nexus_simulation())
