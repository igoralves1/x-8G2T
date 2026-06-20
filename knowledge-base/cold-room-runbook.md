device:sensor_001
# Cold Room Temperature Runbook (sensor_001)

## Normal operating range
The warehouse cold room must stay between **2 °C and 8 °C**. The set point is
4 °C. Brief excursions during door openings are expected but should recover
within 10 minutes.

## Alarm thresholds
- **Warning**: temperature > 6 °C sustained for 15 minutes.
- **Critical**: temperature > 8 °C at any reading, or > 6 °C for 30+ minutes.

## Common root causes for high temperature
1. **Door left open** – most frequent. Check door sensor and recent access logs.
2. **Condenser fan failure** – temperature climbs slowly and steadily; vibration
   on the compressor often drops to zero.
3. **Refrigerant low / leak** – gradual loss of cooling capacity over days.
4. **Defrost cycle stuck** – cyclic spikes every few hours.

## Recommended actions
- For a single brief spike that recovers: log, no action.
- For sustained warming: dispatch a technician to inspect the condenser and door
  seal, and verify the defrost schedule.
- If temperature exceeds 10 °C, treat stored goods as at-risk and escalate.
