import asyncio
import sys
from pathlib import Path

# Ensure repo root on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from intake.job_requisition_api import create_job, JobCreateRequest
from shared.db.database import async_session

async def run():
    req = JobCreateRequest(title='Smoke Job Direct', department='Eng')
    async with async_session() as db:
        try:
            res = await create_job(req, db=db, user={'sub':'test-user'})
            print('create_job res=', res)
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(run())
