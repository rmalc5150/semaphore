SELECT *
FROM optima_regulatory_pilot.regulatory_events_windows
WHERE window_id IN (
  '6564bf6301b0ea6af0f3c2468c6f84a3df5252b2d603fb162716ad848bbcb679',
  '0a758784c3b45bc511fc7d96f4702f4ba10fc45b4266b1544fafd34ab16c368d',
  '0470671ff565ea7894fffbb467987224e59bbf64c25d29635c97b175d8eafcc0'
)
ORDER BY rand()
LIMIT 20;
