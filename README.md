<div align="center">

# HUsim
### Mine Fleet Simulation Control System

Python 3.10+ | React 18 | TypeScript | FastAPI | MIT License

A weather-adaptive autonomous truck fleet simulation platform for open-pit mines.
Built on MineSim-Dynamic (Beihang University)
Hacettepe University Mining Engineering — Senior Capstone Project 2026

</div>

## Overview

HUsim extends the MineSim-Dynamic simulation framework with a real-time
web-based control interface. The system integrates weather-adaptive parameter
optimization, ORCA collision avoidance, and fleet coordination — enabling
researchers and engineers to analyze how environmental conditions affect
autonomous mine truck operations.

Key Innovation: Weather conditions (rain, snow, fog, ice) are mapped to
simulation parameters in real-time using data calibrated from 15,847 real
vehicle measurements (Levin Telematics Dataset).

## Features

- Weather Optimization: 6 weather types x 5 ground conditions → automatic parameter calculation
- Fleet Coordination: Priority-based intersection management for multi-vehicle scenarios
- ORCA Collision Avoidance: Mathematically proven collision-free motion (van den Berg et al., 2011)
- Excavator-Truck Cycle: Real Load-Haul-Dump simulation with data from Manyele (2017)
- Engine Temperature: Physics-based thermal model for XG90G and NTE200 trucks
- Event Zones: Dynamic hazards — rockfall, road works, water puddles, dust clouds
- Real-time Metrics: Safety, efficiency, smoothness and task completion scoring
- PDF Reports: Automated simulation report generation
- Interactive Map: Mouse zoom/pan, MineSim-style 2D visualization
- Turkish Interface: Full Turkish language UI

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+

### Installation

Clone the repository:
```
git clone https://github.com/Alicemal66/HUsim.git
cd HUsim
```

Backend setup:
```
cd husim/backend
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

Frontend setup:
```
cd husim/frontend
npm install
```

### Running

Terminal 1 - Backend:
```
cd husim/backend
venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

Terminal 2 - Frontend:
```
cd husim/frontend
npm run dev
```

Open in browser: http://localhost:5173

## Architecture

```
HUsim/
├── husim/
│   ├── backend/                    # Python / FastAPI
│   │   ├── main.py                 # API entry point and endpoints
│   │   ├── scenario_loader.py      # MineSim JSON parser + ORCA integration
│   │   ├── weather_optimizer.py    # Weather to parameter conversion engine
│   │   ├── orca_solver.py          # ORCA collision avoidance algorithm
│   │   ├── excavator_model.py      # Excavator-truck loading cycle model
│   │   ├── engine_model.py         # Engine temperature physics model
│   │   ├── event_zones.py          # Dynamic hazard zone management
│   │   ├── load_system.py          # Vehicle load and grade parameter system
│   │   ├── dataset_calibration.py  # Levin Telematics calibration
│   │   ├── database.py             # SQLite session management
│   │   ├── metrics_service.py      # Safety and efficiency metric calculation
│   │   ├── report_generator.py     # PDF report generation
│   │   └── demo_scenarios/         # Static collision-free demo JSON files
│   └── frontend/                   # TypeScript / React
│       └── src/
│           ├── components/
│           │   ├── SimulationViewer.tsx  # Canvas 2D renderer
│           │   ├── WeatherPanel.tsx      # Weather input form
│           │   ├── ScenarioSelector.tsx  # Scenario list with filters
│           │   └── MetricsPanel.tsx      # Real-time metric dashboard
│           ├── store.ts                  # Global state management
│           └── tr.ts                     # Turkish language strings
└── MineSim-Dynamic-main/           # Base simulation framework
    └── inputs/
        ├── Scenario-dapai_intersection_1_3_4.json
        └── Scenario-jiangtong_intersection_9_3_2.json
```

## API Reference

```
GET  /api/health                  - System status check
GET  /api/scenarios               - List all scenarios
GET  /api/scenarios/{id}/frames   - Get simulation frame data
POST /api/scenarios/run           - Start simulation
POST /api/weather/optimize        - Calculate optimized parameters
POST /api/reports/generate        - Generate PDF report
WS   /ws/simulation/{id}          - Real-time frame stream
```

## Key Parameters

```
Real scenarios:        2 (Dapai, Jiangtong)       MineSim-Dynamic
Telemetry records:     15,847 vehicles              Levin Dataset (Kaggle)
Loading records:       62,000 measurements          Manyele (2017)
XG90G empty speed:     15.3 m/s                     Komatsu specs
XG90G loaded speed:    8.9 m/s                      Komatsu specs
Loading time (XG90G):  160-197 seconds              Manyele (2017)
Full cycle time:       19.765 minutes               Mnzool et al. (2024)
ORCA time horizon:     5 seconds                    van den Berg (2011)
```

## References

- Chen et al. (2025). MineSim. Science Direct. DOI: 10.1016/j.aap.2025.107904
- van den Berg et al. (2011). Reciprocal n-Body Collision Avoidance. Robotics Research.
- Manyele (2017). Excavator Performance Factors. Engineering, 9, 599-624.
- Mnzool et al. (2024). Cycle time optimization. Mining of Mineral Deposits, 18(1).
- Levin Vehicle Telematics Dataset. Kaggle, 2023.

## Tech Stack

```
Backend:   Python 3.10, FastAPI, SQLAlchemy, SQLite, NumPy, ReportLab
Frontend:  TypeScript, React 18, Vite, HTML5 Canvas API
Algorithm: ORCA (Optimal Reciprocal Collision Avoidance)
Base:      MineSim-Dynamic (BUAA-TRANS-Mine-Group)
```

## License

MIT License — see LICENSE file for details.

## Acknowledgments

- MineSim-Dynamic by BUAA-TRANS-Mine-Group (Beihang University)
- ORCA algorithm by University of North Carolina
- Hacettepe University Mining Engineering Department
