# HUsim — Mine Fleet Simulation Control System

An autonomous truck fleet simulation system for open-pit mines.
Built on top of MineSim-Dynamic (BUAA-TRANS-Mine-Group, Beihang University).

## Features
- Weather-adaptive parameter optimization (6 weather types × 5 ground conditions)
- ORCA collision avoidance algorithm (van den Berg et al., 2011)
- Real MineSim scenario data (Dapai & Jiangtong intersections)
- Fleet coordination with priority-based intersection management
- Excavator-truck Load-Haul-Dump cycle simulation
- Engine temperature monitoring
- Dynamic event zones (rockfall, road work, etc.)
- Turkish language interface
- PDF report generation

## Requirements
- Python 3.10+
- Node.js 18+

## How to Run

**Terminal 1 — Backend:**
```bash
cd husim/backend
venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd husim/frontend
npm install
npm run dev
```

Open in browser: http://localhost:5173

## Tech Stack
- Backend: Python, FastAPI, SQLite
- Frontend: TypeScript, React, HTML5 Canvas
- Algorithm: ORCA (Optimal Reciprocal Collision Avoidance)

## References
- Chen et al. (2025). MineSim. Science Direct.
- van den Berg et al. (2011). Reciprocal n-Body Collision Avoidance. Robotics Research.
- Manyele (2017). Investigation of Excavator Performance Factors. Engineering, 9.
