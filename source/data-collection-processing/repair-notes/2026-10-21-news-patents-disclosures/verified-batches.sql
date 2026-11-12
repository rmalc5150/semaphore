-- finlight; verified batch rows: 11
SELECT * FROM optima_collected_data.batch_verification_records WHERE source='finlight' AND dataset='news_articles' AND batch_group='cd8600bf3f2f566b5c1f22fbec91adfe3bc1e16df59fb310da5f0bad9ea58522' ORDER BY rand() LIMIT 20;

-- hkex_news; verified batch rows: 500
SELECT * FROM optima_collected_data.batch_verification_records WHERE source='hkex_news' AND dataset='filings' AND batch_group='f36eb2f8e78f9be4f34d08489ebcbf3fab7142030e09d3753db83b13c25f8198' ORDER BY rand() LIMIT 20;

-- uspto_odp; verified batch rows: 4
SELECT * FROM optima_collected_data.batch_verification_records WHERE source='uspto_odp' AND dataset='patent_petition_decisions' AND batch_group='6a68e3c6e32ec29c4091561df62ea3427dfcc27a64c8169919c876664b1b65ea' ORDER BY rand() LIMIT 20;

-- uspto_odp; verified batch rows: 300
SELECT * FROM optima_collected_data.batch_verification_records WHERE source='uspto_odp' AND dataset='patent_records' AND batch_group='30d676e8f9a790d6df2d2325d4600aa187bf7a934fcbf777452da84ab6701e73' ORDER BY rand() LIMIT 20;
