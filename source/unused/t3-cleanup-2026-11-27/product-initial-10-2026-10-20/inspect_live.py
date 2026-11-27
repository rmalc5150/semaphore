from pathlib import Path
p=Path('/home/ec2-user/product-initial-10-2026-10-20/populate.py')
exec(p.read_text().split("assert run('SELECT COUNT(*) FROM tracking.products')")[0])
print(run("SELECT review_status,COUNT(*) FROM tracking.companies WHERE archived_at IS NULL GROUP BY review_status; SHOW COLUMNS FROM tracking.companies; SELECT COUNT(*) FROM tracking.products; SHOW TRIGGERS FROM tracking WHERE `Table`='companies';"))
