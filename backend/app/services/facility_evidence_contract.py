from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

FACILITY_EVIDENCE_SCHEMA_VERSION="oomnik-facility-evidence/0.1"
AVAILABILITY_VALUES={"AVAILABLE","YES","LIMITED","WAITLIST","UNAVAILABLE","NO","UNKNOWN"}

@dataclass(frozen=True)
class FacilityFact:
    value: Any
    source_type: str
    observed_at: str|None=None
    provider_reported_at: str|None=None
    status: str="UNKNOWN"
    previous_value: Any=None

    @property
    def decision_usable(self)->bool:
        if self.source_type=="PROVIDER" and self.status not in {"CONFLICT","REVIEW_REQUIRED"}:
            return True
        return self.status in {"REGULATORY_VERIFIED","VERIFIED"}

def license_fact(value:Any, *, regulatory_verified:bool, observed_at:str|None=None)->FacilityFact:
    return FacilityFact(value=value,source_type="REGULATORY" if regulatory_verified else "PROVIDER",observed_at=observed_at,status="REGULATORY_VERIFIED" if regulatory_verified else "PROVIDER_REPORTED")

def availability_fact(value:Any, *, source_type:str, observed_at:str|None=None)->dict[str,Any]:
    normalized=str(value or "UNKNOWN").upper()
    if normalized not in AVAILABILITY_VALUES: normalized="UNKNOWN"
    return {"value":normalized,"source_type":source_type,"observed_at":observed_at,"status":"LAST_REPORTED_AVAILABILITY","final_status":"REQUIRES_DIRECT_VERIFICATION"}

def room_price(*, room_type:str, base_rent:float|None, qualifier:str="UNKNOWN", care_fee:float|None=None, mandatory_monthly_fees:float|None=None, second_person_fee:float|None=None, entrance_fee:float|None=None)->dict[str,Any]:
    known=[base_rent,care_fee,mandatory_monthly_fees,second_person_fee]
    total=sum(x for x in known if isinstance(x,(int,float))) if isinstance(base_rent,(int,float)) else None
    total_complete=isinstance(base_rent,(int,float)) and all(x is not None for x in (care_fee,mandatory_monthly_fees))
    return {"room_type":room_type,"base_monthly_rent":base_rent,"pricing_qualifier":qualifier,"care_fee":care_fee,"mandatory_monthly_fees":mandatory_monthly_fees,"second_person_fee":second_person_fee,"entrance_fee":entrance_fee,"total_known_monthly_cost":total,"total_affordability_status":"KNOWN" if total_complete else "PENDING"}
