from fastapi import APIRouter

from seed import reseed_demo, reseed_full

router = APIRouter(prefix="/dev/seed", tags=["dev-seed"])


@router.post("/reseed-demo")
async def reseed_demo_endpoint():
    await reseed_demo()
    return {"status": "ok", "mode": "demo"}


@router.post("/reseed-full")
async def reseed_full_endpoint():
    await reseed_full()
    return {"status": "ok", "mode": "full"}
