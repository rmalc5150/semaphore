SELECT source, provider_id, event_date, date_basis,
       length(data_json) AS payload_characters,
       substr(data_json, 1, 200) AS payload_preview
FROM optima_regulatory_pilot.regulatory_events_windows
WHERE window_id = 'b494577cf540d8f1ebace452c1b518d682bbc76f7ad309b055a98a5dc3e35910'
LIMIT 3;

-- All columns for a small random sample of the three verified repair windows.
SELECT *
FROM optima_regulatory_pilot.regulatory_events_windows
WHERE window_id IN (
  'b494577cf540d8f1ebace452c1b518d682bbc76f7ad309b055a98a5dc3e35910',
  'bb881a4d601ab0f95cc120b90e0f3cd34bf67a65327957e84ca9fc4178446f6d',
  '6cdaf33ee21c535e17195bec838df5e81524381ffe21b4ee764d79ebb98bcf25'
)
ORDER BY rand()
LIMIT 20;
