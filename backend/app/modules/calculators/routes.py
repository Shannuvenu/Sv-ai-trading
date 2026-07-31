from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.modules.calculators import (
    sip_calculator, lumpsum_calculator, cagr_calculator,
    emi_calculator, compound_interest, fd_calculator, rd_calculator,
)

router = APIRouter(prefix="/calculators", tags=["Calculators"])


class CalcResult(BaseModel):
    result: dict


@router.get("/sip")
def calc_sip(
    monthly: float = Query(..., gt=0),
    years: int = Query(..., gt=0),
    rate: float = Query(..., ge=0, le=50),
):
    return {"result": sip_calculator(monthly, years, rate)}


@router.get("/lumpsum")
def calc_lumpsum(
    principal: float = Query(..., gt=0),
    years: int = Query(..., gt=0),
    rate: float = Query(..., ge=0, le=50),
):
    return {"result": lumpsum_calculator(principal, years, rate)}


@router.get("/cagr")
def calc_cagr(
    initial: float = Query(..., gt=0),
    final: float = Query(..., gt=0),
    years: float = Query(..., gt=0),
):
    return {"result": cagr_calculator(initial, final, years)}


@router.get("/emi")
def calc_emi(
    principal: float = Query(..., gt=0),
    years: int = Query(..., gt=0),
    rate: float = Query(..., ge=0, le=50),
):
    return {"result": emi_calculator(principal, years, rate)}


@router.get("/compound")
def calc_compound(
    principal: float = Query(..., gt=0),
    years: int = Query(..., gt=0),
    rate: float = Query(..., ge=0, le=50),
    compounding: int = Query(1, ge=1, le=365),
):
    return {"result": compound_interest(principal, years, rate, compounding)}


@router.get("/fd")
def calc_fd(
    principal: float = Query(..., gt=0),
    years: float = Query(..., gt=0),
    rate: float = Query(..., ge=0, le=20),
):
    return {"result": fd_calculator(principal, years, rate)}


@router.get("/rd")
def calc_rd(
    monthly: float = Query(..., gt=0),
    months: int = Query(..., gt=0),
    rate: float = Query(..., ge=0, le=20),
):
    return {"result": rd_calculator(monthly, months, rate)}
