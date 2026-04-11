# Task E-03: Real Building Energy Performance from CECB

**Programme:** E (Energy & Certification)
**Feature:** E.3 — Performance energetique reelle from CECB data
**Status:** NOT STARTED — need to fetch real CECB certificates
**Effort:** M (1 sprint)
**Outcome:** Each building has real energy class A-G based on official CECB certificate

## What to do

Switzerland's CECB (Certificat d'Energie Cantonal pour les Bâtiments) provides official energy classifications A-G.
Each cantonal CECB register has an API or public lookup.

**Create a service that:**
1. Looks up CECB certificate by EGID or address
2. Extracts energy class (A-G), consumption (kWh/m2/year), emissions (CO2/m2/year)
3. Stores in Building model fields (add if missing): `energy_class`, `energy_consumption_kwh_m2`, `energy_emissions_co2_m2`
4. Creates lookup API: GET `/buildings/{id}/energy-certificate`
5. Handles fallback (estimate if no CECB found)
6. Wires into Energy tab

## Files to create

**Create:**
- `backend/app/services/cecb_lookup_service.py` (100+ lines)
- `backend/tests/test_cecb_lookup.py` (60+ lines)

**Modify:**
- `backend/app/models/building.py` — add 3 energy fields if missing
- `backend/alembic/versions/` — add migration for fields
- `backend/app/api/buildings.py` — add GET `/buildings/{id}/energy-certificate`

## Service

```python
from typing import Optional

class CECBLookupService:
    """Fetch energy certificate from cantonal CECB registers."""
    
    CECB_ENDPOINTS = {
        'VD': 'https://cecb-vd.ch/api/lookup',
        'GE': 'https://cecb-ge.ch/api/lookup',
        'BE': 'https://cecb-be.ch/api/lookup',
        'ZH': 'https://cecb-zh.ch/api/lookup',
    }
    
    @staticmethod
    def fetch_cecb_by_egid(egid: int, canton: str) -> Optional[dict]:
        """Fetch CECB from cantonal register."""
        if canton not in CECBLookupService.CECB_ENDPOINTS:
            return None
        
        endpoint = CECBLookupService.CECB_ENDPOINTS[canton]
        
        try:
            resp = requests.get(f"{endpoint}?egid={egid}", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    'energy_class': data.get('classe_energie'),  # A-G
                    'energy_consumption_kwh_m2': data.get('consommation_kwh_m2'),
                    'energy_emissions_co2_m2': data.get('emissions_co2_m2'),
                    'certificate_date': data.get('date_certificat'),
                    'source': 'cecb_official',
                }
        except Exception as e:
            print(f"CECB lookup failed: {e}")
        
        return None
    
    @staticmethod
    def fetch_cecb_by_address(address: str, postal_code: str, canton: str) -> Optional[dict]:
        """Fallback: lookup by address."""
        # Similar pattern, use address instead of EGID
        # Return dict with energy_class, consumption, emissions
        pass
    
    @staticmethod
    def update_building_energy_cert(db: Session, building_id: UUID) -> dict:
        """Fetch and update building energy certificate."""
        building = db.query(Building).filter(Building.id == building_id).first()
        if not building:
            raise ValueError(f"Building {building_id} not found")
        
        # Try EGID first
        if building.egid:
            cert = CECBLookupService.fetch_cecb_by_egid(building.egid, building.canton)
        
        # Fallback to address
        if not cert:
            cert = CECBLookupService.fetch_cecb_by_address(
                building.address, building.postal_code, building.canton
            )
        
        # If still no cert, estimate from construction year
        if not cert:
            cert = CECBLookupService.estimate_energy_class(
                building.construction_year,
                building.renovation_year,
                building.building_type,
            )
        
        # Update building
        building.energy_class = cert.get('energy_class')
        building.energy_consumption_kwh_m2 = cert.get('energy_consumption_kwh_m2')
        building.energy_emissions_co2_m2 = cert.get('energy_emissions_co2_m2')
        building.energy_cert_source = cert.get('source')
        
        db.add(building)
        db.commit()
        
        return cert
    
    @staticmethod
    def estimate_energy_class(construction_year: int, renovation_year: Optional[int], building_type: str) -> dict:
        """Estimate energy class if no certificate found."""
        # Pre-1970: typically F-G
        # 1970-1990: D-E
        # 1990-2010: C-D
        # Post-2010: A-B
        
        ref_year = renovation_year or construction_year
        
        if ref_year < 1970:
            energy_class = 'G'
            consumption = 400
            emissions = 120
        elif ref_year < 1990:
            energy_class = 'E'
            consumption = 280
            emissions = 85
        elif ref_year < 2010:
            energy_class = 'D'
            consumption = 180
            emissions = 55
        else:
            energy_class = 'B'
            consumption = 100
            emissions = 30
        
        return {
            'energy_class': energy_class,
            'energy_consumption_kwh_m2': consumption,
            'energy_emissions_co2_m2': emissions,
            'source': 'estimated',
        }
```

## Migration

```python
# backend/alembic/versions/202604_add_energy_fields.py
def upgrade():
    op.add_column('buildings', sa.Column('energy_class', sa.String(1), nullable=True))
    op.add_column('buildings', sa.Column('energy_consumption_kwh_m2', sa.Float(), nullable=True))
    op.add_column('buildings', sa.Column('energy_emissions_co2_m2', sa.Float(), nullable=True))
    op.add_column('buildings', sa.Column('energy_cert_source', sa.String(50), nullable=True))

def downgrade():
    op.drop_column('buildings', 'energy_cert_source')
    op.drop_column('buildings', 'energy_emissions_co2_m2')
    op.drop_column('buildings', 'energy_consumption_kwh_m2')
    op.drop_column('buildings', 'energy_class')
```

## API

```python
@router.get("/{building_id}/energy-certificate")
def get_energy_certificate(building_id: UUID, db: Session = Depends(get_db)):
    """Get building energy certificate (CECB)."""
    return CECBLookupService.update_building_energy_cert(db, building_id)
```

## Test

```bash
cd backend
pytest tests/test_cecb_lookup.py -v
```

## Commit

```
feat(programme-e): CECB integration for real energy performance

- Add cecb_lookup_service with cantonal API calls (VD/GE/BE/ZH)
- Fallback to address-based lookup
- Estimation from construction year if no certificate
- Add energy_class, energy_consumption_kwh_m2, energy_emissions_co2_m2 to Building
- Add GET /buildings/{id}/energy-certificate endpoint
- Wire into Energy tab of Building Home
- 7+ tests covering real + estimated cases
```

## Success criteria

- CECB lookup works for VD/GE buildings (real API calls)
- Falls back to estimation if no certificate
- Energy class A-G displayed in Building Home
- Consumption kWh/m2 shown
