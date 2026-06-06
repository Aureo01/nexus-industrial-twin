# nexus-industrial-twin

> Physics-Informed AI for predictive maintenance, autonomous drone dispatch, and self-healing production systems.

---

## What it does

NEXUS is a cognitive industrial twin that monitors factory assets in real time. Instead of relying only on statistical thresholds, it uses a **Physics-Informed Neural Network (PINN)** trained on the thermodynamic relationship between vibration, load, and temperature. When a machine starts violating physical laws — not just crossing a number — NEXUS flags it as a pre-failure condition.

From that point, the response is fully autonomous:

1. A drone is dispatched to visually or thermally verify the anomaly
2. A maintenance work order is created in SAP PM / IBM Maximo via REST
3. Production load is rerouted to a backup asset through the MES integration (Self-Healing)

All without a human in the loop until the work order lands in the technician's queue.

---

## Architecture

```
Sensor Stream (vibration, load, temperature)
        │
        ▼
┌───────────────────────┐
│  Physics-Informed     │  ← Trained on normal thermodynamic behavior
│  Neural Network       │    Detects law violations, not just outliers
│  (PINN)               │
└──────────┬────────────┘
           │ Anomaly detected
           ▼
┌──────────────────────────────────────────┐
│           NEXUS Decision Engine          │
│                                          │
│  ┌─────────────┐  ┌──────────────────┐  │
│  │ Drone       │  │ SAP / Maximo     │  │
│  │ Dispatcher  │  │ CMMS Connector   │  │
│  └─────────────┘  └──────────────────┘  │
│                                          │
│  ┌─────────────────────────────────┐    │
│  │ Self-Healing MES Router         │    │
│  │ (auto-reroutes production load) │    │
│  └─────────────────────────────────┘    │
└──────────────────────────────────────────┘
           │
           ▼
  InfluxDB → Grafana Dashboard
```

---

## Key Technical Features

### Physics-Informed Neural Network
Standard anomaly detection flags values that exceed a threshold. NEXUS goes further: it learns the physical relationship `T ≈ f(vibration², load)` from normal operating data, then detects when real temperature diverges from what thermodynamics predicts — even if both values are within "normal" ranges individually.

```python
def physics_loss(self, predicted_temp, actual_temp, vibration):
    mse = self.loss_fn(predicted_temp, actual_temp)
    # Physical constraint: temperature must rise with friction (V² * Load)
    physical_constraint = torch.mean(torch.relu(
        (predicted_temp - actual_temp) * vibration
    ))
    return mse + 0.1 * physical_constraint
```

### Autonomous Drone Dispatch
When a physics violation is confirmed, the swarm controller assigns the nearest available drone with the appropriate sensor payload (thermal camera for thermal anomalies, visual for mechanical).

### Self-Healing Production
If the failing asset is a primary production line component, NEXUS automatically reroutes 100% of the load to the configured backup asset — no operator intervention required.

### SAP PM / IBM Maximo Integration
Work orders are created via REST with priority, planned start time, and work center assignment. Compatible with SAP Plant Maintenance and IBM Maximo CMMS schemas.

---

## Stack

| Layer | Technology |
|---|---|
| Neural core | PyTorch (custom PINN) |
| Anomaly detection | Physics-Informed loss function |
| Drone coordination | Autonomous swarm controller |
| ERP integration | SAP PM / IBM Maximo REST API |
| Time series | InfluxDB + Grafana |
| Runtime | Python 3.10+, asyncio |

---

## Quick Start

```bash
git clone https://github.com/Aureo01/nexus-industrial-twin
cd nexus-industrial-twin
pip install -r requirements.txt
python nexus.py
```

The simulation runs 20 cycles. The first 15 are normal operation. Cycles 16–20 inject a thermal anomaly that violates the thermodynamic model — watch NEXUS detect it, dispatch the drone, create the work order, and reroute production automatically.

---

## Simulation Output

```
[INFO]  PINN trained for PUMP-001 (Loss: 0.0031)
[INFO]  DRONE DISPATCHED: DRONE-ALPHA-01 → PUMP-001 (thermal_camera)
[CRITICAL]  PHYSICS VIOLATION: Temperature (150°C) exceeds thermodynamic
           prediction by 87.3%. Possible dry friction or cooling failure.
[INFO]  SAP Work Order created: ORD-47291 (Priority 1, starts in 4h)
[CRITICAL]  SELF-HEALING: Rerouting PUMP-001 load → PUMP-002
[INFO]  Drone DRONE-ALPHA-01 returned. Thermal anomaly CONFIRMED.
```

---

## Production Considerations

- Replace simulated sensor input with OPC-UA, MQTT, or direct PLC integration
- Configure `CMMSConnector` with real SAP/Maximo base URL and API key
- Set up InfluxDB + Grafana for live dashboard
- Extend `PhysicsLaw` definitions per asset type (pumps, compressors, motors)
- Drone dispatch integrates with DJI SDK or ROS2 for real hardware

---

## Use Cases

- Predictive maintenance in manufacturing plants
- Condition monitoring for critical rotating equipment
- Autonomous inspection workflows
- ERP-integrated maintenance operations

---

*Built with PyTorch · asyncio · REST · InfluxDB*
