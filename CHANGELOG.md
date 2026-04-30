# Changelog

All notable changes to HUsim are documented in this file.

## [1.0.0] - 2026-04-30

### Added

#### Core Simulation
- MineSim-Dynamic JSON scenario parser with full vehicle trajectory support
- Real-time WebSocket frame streaming for live simulation playback
- ORCA (Optimal Reciprocal Collision Avoidance) algorithm integration
- Priority-based intersection management for multi-vehicle fleet coordination
- HTML5 Canvas 2D renderer with MineSim-style map visualization

#### Weather Optimization
- Weather-adaptive parameter engine covering 6 weather types (clear, rain, snow, fog, ice, dust)
- 5 ground condition variants (dry, wet, muddy, icy, gravel)
- Levin Telematics Dataset calibration from 15,847 real vehicle measurements
- Automatic speed factor, braking distance, and safety margin calculation

#### Vehicle Models
- Excavator-truck loading cycle model based on Manyele (2017) data (62,000 measurements)
- Engine temperature physics model for XG90G and NTE200 trucks
- Vehicle load and road grade parameter system affecting speed and braking

#### Event Zones
- Dynamic hazard zone management (rockfall, road works, water puddles, dust clouds)
- Real-time event zone rendering on simulation canvas
- Speed restriction enforcement when vehicles enter hazard zones

#### Metrics & Reporting
- Real-time safety score, efficiency score, smoothness score, and task completion tracking
- Automated PDF report generation with simulation summary
- SQLite session history with result persistence

#### Frontend UI
- Full Turkish language interface (tr.ts string catalog)
- Interactive map with mouse zoom/pan controls and north arrow overlay
- Scenario selector with type/difficulty filters
- Weather panel with live parameter preview
- Real-time metrics dashboard
- Fleet panel showing per-vehicle status
- Event control panel for placing and removing hazard zones
- Scenario comparison mode (normal vs. weather-optimized)
- Scenario generator for custom intersection configurations

#### Demo Scenarios
- 5 pre-built collision-free demo scenarios (T-intersection, 4-way, straight, multi-truck)
- Dapai and Jiangtong real MineSim-Dynamic scenarios included
