"""Synthetic UAE-style clinical reference tables.

Shared by the dataset generator (backend/scripts/generate_dataset.py) and the
Coding Agent's `code_pair_lookup_tool`. Categories are used as a coarse proxy
for "clinical coherence" between a diagnosis (ICD-10) and a procedure (CPT):
a code pair is considered valid if their categories match, or if the CPT code
is a general/emergency code that legitimately applies across categories.

All codes, descriptions and cost bands below are illustrative/synthetic and
loosely styled on real coding systems — they are not sourced from any real
payer fee schedule.
"""
from __future__ import annotations

CATEGORIES = [
    "cardiology", "endocrine", "respiratory", "orthopedic", "maternity",
    "pediatric", "dermatology", "gastro", "mental_health", "oncology",
    "general", "emergency", "dental", "optical",
]

# category -> CPT categories considered clinically coherent with it
CROSS_COMPATIBLE_CPT_CATEGORIES = {"general", "emergency"}

# code -> {desc, category}
ICD10_CODES: dict[str, dict] = {
    "I10": {"desc": "Essential (primary) hypertension", "category": "cardiology"},
    "I21.9": {"desc": "Acute myocardial infarction, unspecified", "category": "cardiology"},
    "I25.10": {"desc": "Atherosclerotic heart disease of native coronary artery", "category": "cardiology"},
    "I48.91": {"desc": "Unspecified atrial fibrillation", "category": "cardiology"},
    "I50.9": {"desc": "Heart failure, unspecified", "category": "cardiology"},
    "E11.9": {"desc": "Type 2 diabetes mellitus without complications", "category": "endocrine"},
    "E11.65": {"desc": "Type 2 diabetes mellitus with hyperglycemia", "category": "endocrine"},
    "E03.9": {"desc": "Hypothyroidism, unspecified", "category": "endocrine"},
    "E66.9": {"desc": "Obesity, unspecified", "category": "endocrine"},
    "J45.909": {"desc": "Unspecified asthma, uncomplicated", "category": "respiratory"},
    "J18.9": {"desc": "Pneumonia, unspecified organism", "category": "respiratory"},
    "J06.9": {"desc": "Acute upper respiratory infection, unspecified", "category": "respiratory"},
    "J44.9": {"desc": "Chronic obstructive pulmonary disease, unspecified", "category": "respiratory"},
    "M54.5": {"desc": "Low back pain", "category": "orthopedic"},
    "M17.9": {"desc": "Osteoarthritis of knee, unspecified", "category": "orthopedic"},
    "S52.501A": {"desc": "Fracture of distal radius, closed, initial encounter", "category": "orthopedic"},
    "M75.100": {"desc": "Rotator cuff syndrome, unspecified shoulder", "category": "orthopedic"},
    "M25.561": {"desc": "Pain in right knee", "category": "orthopedic"},
    "Z34.90": {"desc": "Supervision of normal pregnancy, unspecified trimester", "category": "maternity"},
    "O80": {"desc": "Encounter for full-term uncomplicated delivery", "category": "maternity"},
    "O26.90": {"desc": "Pregnancy related condition, unspecified", "category": "maternity"},
    "Z00.129": {"desc": "Routine child health examination, normal", "category": "pediatric"},
    "J02.9": {"desc": "Acute pharyngitis, unspecified", "category": "pediatric"},
    "R50.9": {"desc": "Fever, unspecified", "category": "pediatric"},
    "L20.9": {"desc": "Atopic dermatitis, unspecified", "category": "dermatology"},
    "L30.9": {"desc": "Dermatitis, unspecified", "category": "dermatology"},
    "L70.0": {"desc": "Acne vulgaris", "category": "dermatology"},
    "K21.9": {"desc": "Gastro-esophageal reflux disease without esophagitis", "category": "gastro"},
    "K29.70": {"desc": "Gastritis, unspecified, without bleeding", "category": "gastro"},
    "K59.00": {"desc": "Constipation, unspecified", "category": "gastro"},
    "F32.9": {"desc": "Major depressive disorder, single episode, unspecified", "category": "mental_health"},
    "F41.9": {"desc": "Anxiety disorder, unspecified", "category": "mental_health"},
    "C50.919": {"desc": "Malignant neoplasm of breast, unspecified site", "category": "oncology"},
    "C34.90": {"desc": "Malignant neoplasm of lung, unspecified part", "category": "oncology"},
    "Z00.00": {"desc": "General adult medical examination without abnormal findings", "category": "general"},
    "R51": {"desc": "Headache", "category": "general"},
    "R05": {"desc": "Cough", "category": "general"},
    "R10.9": {"desc": "Unspecified abdominal pain", "category": "general"},
    "S06.0X0A": {"desc": "Concussion without loss of consciousness, initial encounter", "category": "emergency"},
    "T14.90": {"desc": "Injury, unspecified", "category": "emergency"},
    "K08.9": {"desc": "Disorder of teeth and supporting structures, unspecified", "category": "dental"},
    "K02.9": {"desc": "Dental caries, unspecified", "category": "dental"},
    "H52.4": {"desc": "Presbyopia", "category": "optical"},
    "H52.10": {"desc": "Myopia, unspecified eye", "category": "optical"},
    "H10.9": {"desc": "Unspecified conjunctivitis", "category": "optical"},
    "I63.9": {"desc": "Cerebral infarction, unspecified", "category": "cardiology"},
    "N39.0": {"desc": "Urinary tract infection, site not specified", "category": "general"},
    "M79.7": {"desc": "Fibromyalgia", "category": "orthopedic"},
    "E78.5": {"desc": "Hyperlipidemia, unspecified", "category": "cardiology"},
    "J30.9": {"desc": "Allergic rhinitis, unspecified", "category": "respiratory"},
    "B34.9": {"desc": "Viral infection, unspecified", "category": "general"},
}

# code -> {desc, category, cost_band_aed: (min, max), prior_auth}
CPT_CODES: dict[str, dict] = {
    "99213": {"desc": "Office visit, established patient, low complexity", "category": "general", "cost_band_aed": (120, 220), "prior_auth": False},
    "99214": {"desc": "Office visit, established patient, moderate complexity", "category": "general", "cost_band_aed": (200, 350), "prior_auth": False},
    "99203": {"desc": "Office visit, new patient, low complexity", "category": "general", "cost_band_aed": (180, 320), "prior_auth": False},
    "99284": {"desc": "Emergency department visit, high severity", "category": "emergency", "cost_band_aed": (600, 1400), "prior_auth": False},
    "99285": {"desc": "Emergency department visit, critical", "category": "emergency", "cost_band_aed": (1200, 3000), "prior_auth": False},
    "93000": {"desc": "Electrocardiogram, routine, with interpretation", "category": "cardiology", "cost_band_aed": (150, 300), "prior_auth": False},
    "93306": {"desc": "Echocardiography, transthoracic, complete", "category": "cardiology", "cost_band_aed": (800, 1600), "prior_auth": True},
    "93458": {"desc": "Cardiac catheterization, left heart", "category": "cardiology", "cost_band_aed": (8000, 18000), "prior_auth": True},
    "92928": {"desc": "Percutaneous coronary intervention, stent placement", "category": "cardiology", "cost_band_aed": (25000, 55000), "prior_auth": True},
    "83036": {"desc": "Hemoglobin A1c test", "category": "endocrine", "cost_band_aed": (60, 150), "prior_auth": False},
    "80053": {"desc": "Comprehensive metabolic panel", "category": "endocrine", "cost_band_aed": (100, 220), "prior_auth": False},
    "84443": {"desc": "Thyroid stimulating hormone (TSH) test", "category": "endocrine", "cost_band_aed": (80, 180), "prior_auth": False},
    "94010": {"desc": "Spirometry, pulmonary function test", "category": "respiratory", "cost_band_aed": (200, 450), "prior_auth": False},
    "71046": {"desc": "Chest X-ray, 2 views", "category": "respiratory", "cost_band_aed": (150, 350), "prior_auth": False},
    "94640": {"desc": "Nebulizer treatment", "category": "respiratory", "cost_band_aed": (80, 200), "prior_auth": False},
    "71260": {"desc": "CT chest, with contrast", "category": "respiratory", "cost_band_aed": (1500, 3200), "prior_auth": True},
    "72148": {"desc": "MRI lumbar spine, without contrast", "category": "orthopedic", "cost_band_aed": (2000, 4200), "prior_auth": True},
    "73030": {"desc": "X-ray shoulder, 2+ views", "category": "orthopedic", "cost_band_aed": (150, 350), "prior_auth": False},
    "29881": {"desc": "Knee arthroscopy with meniscectomy", "category": "orthopedic", "cost_band_aed": (12000, 26000), "prior_auth": True},
    "20610": {"desc": "Joint injection, major joint", "category": "orthopedic", "cost_band_aed": (300, 700), "prior_auth": False},
    "97110": {"desc": "Therapeutic exercise, physical therapy, 15 min", "category": "orthopedic", "cost_band_aed": (100, 250), "prior_auth": False},
    "25605": {"desc": "Closed treatment of distal radial fracture", "category": "orthopedic", "cost_band_aed": (2500, 6000), "prior_auth": True},
    "59400": {"desc": "Routine obstetric care, vaginal delivery", "category": "maternity", "cost_band_aed": (8000, 16000), "prior_auth": True},
    "59510": {"desc": "Routine obstetric care, cesarean delivery", "category": "maternity", "cost_band_aed": (14000, 28000), "prior_auth": True},
    "76805": {"desc": "Obstetric ultrasound, fetal anatomy", "category": "maternity", "cost_band_aed": (400, 900), "prior_auth": False},
    "59025": {"desc": "Fetal non-stress test", "category": "maternity", "cost_band_aed": (150, 350), "prior_auth": False},
    "90460": {"desc": "Immunization administration, child", "category": "pediatric", "cost_band_aed": (60, 150), "prior_auth": False},
    "99392": {"desc": "Well-child visit, periodic", "category": "pediatric", "cost_band_aed": (150, 300), "prior_auth": False},
    "87880": {"desc": "Rapid strep test", "category": "pediatric", "cost_band_aed": (50, 120), "prior_auth": False},
    "11102": {"desc": "Skin biopsy, single lesion", "category": "dermatology", "cost_band_aed": (250, 600), "prior_auth": False},
    "17000": {"desc": "Destruction of premalignant skin lesion", "category": "dermatology", "cost_band_aed": (200, 500), "prior_auth": False},
    "96910": {"desc": "Phototherapy for skin condition", "category": "dermatology", "cost_band_aed": (150, 400), "prior_auth": False},
    "43235": {"desc": "Upper GI endoscopy, diagnostic", "category": "gastro", "cost_band_aed": (2500, 5500), "prior_auth": True},
    "45378": {"desc": "Colonoscopy, diagnostic", "category": "gastro", "cost_band_aed": (3000, 6500), "prior_auth": True},
    "74176": {"desc": "CT abdomen and pelvis, without contrast", "category": "gastro", "cost_band_aed": (1400, 3000), "prior_auth": True},
    "90834": {"desc": "Psychotherapy, 45 minutes", "category": "mental_health", "cost_band_aed": (300, 600), "prior_auth": False},
    "90792": {"desc": "Psychiatric diagnostic evaluation", "category": "mental_health", "cost_band_aed": (500, 1000), "prior_auth": False},
    "96127": {"desc": "Brief emotional/behavioral assessment", "category": "mental_health", "cost_band_aed": (100, 250), "prior_auth": False},
    "77067": {"desc": "Screening mammography, bilateral", "category": "oncology", "cost_band_aed": (400, 900), "prior_auth": False},
    "96413": {"desc": "Chemotherapy administration, IV, first hour", "category": "oncology", "cost_band_aed": (2000, 5000), "prior_auth": True},
    "77301": {"desc": "Intensity-modulated radiotherapy planning", "category": "oncology", "cost_band_aed": (8000, 20000), "prior_auth": True},
    "81001": {"desc": "Urinalysis, automated with microscopy", "category": "general", "cost_band_aed": (40, 100), "prior_auth": False},
    "85025": {"desc": "Complete blood count with differential", "category": "general", "cost_band_aed": (50, 130), "prior_auth": False},
    "36415": {"desc": "Routine venipuncture", "category": "general", "cost_band_aed": (20, 60), "prior_auth": False},
    "70450": {"desc": "CT head, without contrast", "category": "emergency", "cost_band_aed": (900, 2000), "prior_auth": False},
    "12002": {"desc": "Simple wound repair, 2.5-7.5cm", "category": "emergency", "cost_band_aed": (300, 700), "prior_auth": False},
    "D0120": {"desc": "Periodic oral evaluation", "category": "dental", "cost_band_aed": (80, 180), "prior_auth": False},
    "D2140": {"desc": "Dental amalgam filling, one surface", "category": "dental", "cost_band_aed": (200, 450), "prior_auth": False},
    "D7140": {"desc": "Tooth extraction, erupted tooth", "category": "dental", "cost_band_aed": (250, 600), "prior_auth": False},
    "D2740": {"desc": "Dental crown, porcelain/ceramic", "category": "dental", "cost_band_aed": (1500, 3200), "prior_auth": True},
    "92014": {"desc": "Ophthalmological exam, established patient", "category": "optical", "cost_band_aed": (150, 350), "prior_auth": False},
    "92310": {"desc": "Contact lens fitting", "category": "optical", "cost_band_aed": (200, 450), "prior_auth": False},
    "66984": {"desc": "Cataract surgery with lens insertion", "category": "optical", "cost_band_aed": (7000, 15000), "prior_auth": True},
    "99406": {"desc": "Smoking cessation counseling", "category": "general", "cost_band_aed": (80, 180), "prior_auth": False},
    "36430": {"desc": "Blood transfusion", "category": "general", "cost_band_aed": (600, 1400), "prior_auth": True},
    "93017": {"desc": "Cardiovascular stress test", "category": "cardiology", "cost_band_aed": (700, 1500), "prior_auth": True},
    "95810": {"desc": "Polysomnography, sleep study", "category": "respiratory", "cost_band_aed": (2500, 5000), "prior_auth": True},
    "62323": {"desc": "Epidural steroid injection, lumbar", "category": "orthopedic", "cost_band_aed": (1200, 2800), "prior_auth": True},
    "58150": {"desc": "Total abdominal hysterectomy", "category": "maternity", "cost_band_aed": (15000, 30000), "prior_auth": True},
}


def is_clinically_coherent(icd10_code: str, cpt_code: str) -> bool:
    icd = ICD10_CODES.get(icd10_code)
    cpt = CPT_CODES.get(cpt_code)
    if icd is None or cpt is None:
        return False
    if cpt["category"] in CROSS_COMPATIBLE_CPT_CATEGORIES:
        return True
    return icd["category"] == cpt["category"]


def cpt_cost_band(cpt_code: str) -> tuple[float, float] | None:
    cpt = CPT_CODES.get(cpt_code)
    return cpt["cost_band_aed"] if cpt else None


def cpt_requires_prior_auth(cpt_code: str) -> bool:
    cpt = CPT_CODES.get(cpt_code)
    return bool(cpt and cpt["prior_auth"])
