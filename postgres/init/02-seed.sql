-- =============================================================================
-- Minimal seed data so the stack is queryable immediately after boot.
-- =============================================================================

INSERT INTO devices (external_id, name, device_type, location, latitude, longitude, firmware_version, metadata)
VALUES
  ('sensor_001',  'Cold Room Temp/Humidity', 'sensor',  'Warehouse A - Cold Room', -23.55052, -46.63331, '1.4.2', '{"unit":"C","sample_rate_s":10}'),
  ('sensor_002',  'Compressor Vibration',     'sensor',  'Plant Floor - Line 1',    -23.55060, -46.63340, '1.4.2', '{"unit":"mm/s","sample_rate_s":5}'),
  ('gateway_001', 'Line 1 Modbus Gateway',    'gateway', 'Plant Floor - Line 1',    -23.55060, -46.63340, '2.0.1', '{"protocol":"modbus-tcp"}'),
  ('camera_001',  'Line 1 Inspection Camera', 'camera',  'Plant Floor - Line 1',    -23.55061, -46.63341, '3.1.0', '{"resolution":"1920x1080"}')
ON CONFLICT (external_id) DO NOTHING;

-- Example alarm rules
INSERT INTO alarm_rules (device_id, metric_name, condition, threshold_value, threshold_max, severity, message_template)
SELECT device_id, 'temperature', 'gt', 8.0, NULL, 'critical', 'Cold room temperature {value}C exceeds 8C limit'
FROM devices WHERE external_id = 'sensor_001'
ON CONFLICT DO NOTHING;

INSERT INTO alarm_rules (device_id, metric_name, condition, threshold_value, threshold_max, severity, message_template)
SELECT device_id, 'vibration', 'gt', 7.1, NULL, 'warning', 'Compressor vibration {value}mm/s above ISO 10816 zone C'
FROM devices WHERE external_id = 'sensor_002'
ON CONFLICT DO NOTHING;

-- Default admin user (password: change-me-now  -> bcrypt). Replace in production.
INSERT INTO users (username, email, password_hash, full_name, role)
VALUES ('admin', 'admin@x-8g2t.local',
        '$2b$12$M2t9q3oFkF8N6jJ0t4xq1uM6yQyq7m0Q0pXxq6m3kQ8oQ8oQ8oQ8',
        'Platform Administrator', 'admin')
ON CONFLICT (username) DO NOTHING;
